"""Audit follow-up 2026-09-16: tmux_safe rejection paths + argv guard.

The P0-1 fix module had its validation error branches untested and carried
a dead duplicate implementation (run_in_tmux_argv, removed in the same
commit that adds these tests).
"""

import pytest

from psg.automation.tmux_safe import tmux_new_session_argv, validate_config_value


class TestValidateConfigValue:
    def test_rejects_non_str(self):
        with pytest.raises(ValueError, match="must be str"):
            validate_config_value("x", 123)  # type: ignore[arg-type]

    def test_rejects_empty(self):
        with pytest.raises(ValueError, match="must not be empty"):
            validate_config_value("x", "")

    def test_rejects_nul(self):
        with pytest.raises(ValueError, match="line-break or NUL"):
            validate_config_value("x", "a\x00b")

    def test_rejects_linebreak(self):
        with pytest.raises(ValueError, match="line-break or NUL"):
            validate_config_value("x", "a\nb")
        with pytest.raises(ValueError, match="line-break or NUL"):
            validate_config_value("x", "a\rb")

    @pytest.mark.parametrize(
        "meta", [";", "&", "|", "`", "$", "<", ">", "(", ")", "{", "}", "[", "]", "!"]
    )
    def test_rejects_shell_metacharacters(self, meta: str):
        with pytest.raises(ValueError, match="shell metacharacter"):
            validate_config_value("x", f"val{meta}ue")

    def test_rejects_pattern_mismatch(self):
        # value free of metachars but violating the pattern
        with pytest.raises(ValueError, match="does not match"):
            validate_config_value("x", "bad value", pattern=r"[\w-]+")

    def test_accepts_clean_value(self):
        assert validate_config_value("x", "llama3:8b", pattern=r"[\w./:+-]+") == "llama3:8b"


class TestTmuxNewSessionArgv:
    def test_rejects_unsafe_session_name(self):
        for bad in ("", "a;b", "a b", "a\nb", "a$b", "a..../x"):
            with pytest.raises(ValueError, match="unsafe tmux session name"):
                tmux_new_session_argv(bad, ["true"])

    def test_rejects_non_string_argv(self):
        with pytest.raises(ValueError, match="non-None strings"):
            tmux_new_session_argv("s", ["ok", None])  # type: ignore[list-item]
        with pytest.raises(ValueError, match="non-None strings"):
            tmux_new_session_argv("s", ["ok", "a\x00b"])

    def test_builds_pure_argv(self):
        argv = tmux_new_session_argv("sess1", ["python", "-m", "psg", "--model", "x"])
        assert argv[:8] == ["tmux", "new-session", "-d", "-s", "sess1", "-n", "psg", "python"]
        assert all(isinstance(a, str) for a in argv)
        # no shell-intermediary anywhere
        assert not any(a in ("bash", "sh", "/bin/bash", "/bin/sh") for a in argv)

    def test_custom_window_name(self):
        argv = tmux_new_session_argv("s", ["true"], window_name="win2")
        assert argv[6] == "win2"