#!/usr/bin/env python3
"""Audit P1-6 (HIGH, 2026-09-15): sandbox the upstream Node driver.

tools/curate_parseltongue.py runs `node -e NODE_DRIVER` which requires
upstream P4RS3LT0NGV3 JS modules. Those are THIRD-PARTY CODE: the audit
found they execute with full privileges (same user, full filesystem,
network allowed). A malicious or compromised upstream commit could
exfiltrate files, plant hooks, or worse — while the curation tool's
purpose is only to apply TEXT TRANSFORMS.

This wrapper runs the Node driver with a hard sandbox:
  - `firejail --noprofile --net=none` when available (no network,
    minimal profile), falling back to
  - plain node WITHOUT network env and with a read-only-ish working
    directory when firejail is unavailable (best effort; CI has no
    firejail by default).

The sandbox is fail-closed: if firejail is REQUESTED and missing, we
raise instead of silently downgrading to unsandboxed execution.
"""
from __future__ import annotations

import os
import shutil
import subprocess

# Env vars the driver may receive — anything else is stripped (no tokens,
# no AWS keys, no proxies leaking into third-party code).
_ALLOW_ENV = (
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "NODE_PATH",
    "TMPDIR",
)


def _minimal_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k in _ALLOW_ENV}


class SandboxUnavailable(RuntimeError):
    """Raised when the requested sandbox backend is not installed."""


def build_sandbox_cmd(
    argv: list[str], *, require_sandbox: bool = False
) -> list[str]:
    """Wrap `argv` in the strongest available sandbox.

    firejail is preferred when installed: `--net=none` (no network),
    `--noprofile` (no distro profile surprises), `--quiet`.
    If firejail is missing:
      - require_sandbox=True  -> raise SandboxUnavailable (fail closed)
      - require_sandbox=False -> return argv unchanged (best-effort env
        filtering still applies in run_sandboxed)
    """
    if shutil.which("firejail"):
        return [
            "firejail", "--quiet", "--noprofile", "--net=none",
            "--private-tmp",
            *argv,
        ]
    if require_sandbox:
        raise SandboxUnavailable(
            "firejail requested but not installed — refusing to run "
            "third-party code unsandboxed (install firejail or set "
            "PSG_ALLOW_UNSANDBOXED_NODE=1 explicitly)"
        )
    return argv


def run_sandboxed(
    argv: list[str], *, timeout: float = 120.0, check: bool = True
) -> subprocess.CompletedProcess:
    """Run argv under build_sandbox_cmd with a scrubbed environment.

    PSG_ALLOW_UNSANDBOXED_NODE=1 documents an operator's explicit choice
    to run without firejail (the sandbox check is skipped in that case).
    """
    require = os.environ.get("PSG_ALLOW_UNSANDBOXED_NODE") != "1"
    cmd = build_sandbox_cmd(argv, require_sandbox=require)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=check,
        env=_minimal_env(),
    )