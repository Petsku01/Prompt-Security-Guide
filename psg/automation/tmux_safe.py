"""Fix 1 (Audit P0-1, HIGH): tmux shell-injection via YAML config values.

Old run_in_tmux built a bash script by interpolating config values inside
ALREADY-QUOTED double quotes; shlex.quote() output inside double quotes is
treated literally, so $() / backticks were re-expanded by the shell
(live-verified: $(printf INJECTED) executed).

Fix: run each test DIRECTLY as an argv list under tmux (tmux new-session
runs the command via its own exec — no intermediate shell), and validate
config values in PipelineConfig.__post_init__ so hostile YAML values are
rejected before they ever reach a process boundary.
"""

from __future__ import annotations

import re


def validate_config_value(name: str, value: str, *, pattern: str | None = None) -> str:
    """Validate a config-supplied string before it reaches a process.

    Raises ValueError on shell metacharacters / path escape. Returns the
    validated value.
    """
    if not isinstance(value, str):
        raise ValueError(f"{name} must be str, got {type(value).__name__}")
    if not value:
        raise ValueError(f"{name} must not be empty")
    if "\x00" in value or "\n" in value or "\r" in value:
        raise ValueError(f"{name} contains a line-break or NUL: rejected")
    # Reject shell metacharacters outright — tmux argv path must never need them.
    if re.search(r"[;&|`$<>\(\)\{\}\[\]!]", value):
        raise ValueError(f"{name} contains a shell metacharacter (rejected): {value!r}")
    if pattern and not re.fullmatch(pattern, value):
        # fullmatch: a partial prefix match must not pass (e.g. pattern
        # r"[\w-]+" must reject "bad value", not accept its "bad" prefix)
        raise ValueError(
            f"{name} does not match required pattern {pattern!r}: {value!r}"
        )
    return value


def tmux_new_session_argv(
    session_name: str, argv: list[str], *, window_name: str = "psg"
) -> list[str]:
    """Build a tmux argv that runs *argv* directly (no shell string).

    tmux new-session <command...> spawns the command WITHOUT a shell when
    given as separate argv entries — no interpolation, no quoting layer.
    """
    if not session_name or re.search(r"[^\w.-]", session_name):
        raise ValueError(f"unsafe tmux session name: {session_name!r}")
    if any(not isinstance(a, str) or "\x00" in a for a in argv):
        raise ValueError("argv entries must be non-None strings")
    return ["tmux", "new-session", "-d", "-s", session_name, "-n", window_name, *argv]
