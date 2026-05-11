"""Tests for psg.automation.daily_check — cron scheduler helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from psg.automation.daily_check import install_cron, is_cron_installed, remove_cron, validate_cron_schedule


# ── test 1: install_cron runs crontab with correct schedule ───────────────

def test_install_cron_runs_crontab_command() -> None:
    """install_cron must invoke `crontab -l` then `crontab -` via subprocess."""
    with patch("psg.automation.daily_check.subprocess") as mock_subprocess:
        mock_subprocess.run.return_value = MagicMock(returncode=0)

        result = install_cron("0 3 * * *")

    assert result is True
    assert mock_subprocess.run.call_count == 2  # crontab -l then crontab -
    first_cmd = mock_subprocess.run.call_args_list[0][0][0]
    assert first_cmd == ["crontab", "-l"]
    second_cmd = mock_subprocess.run.call_args_list[1][0][0]
    assert second_cmd == ["crontab", "-"]


# ── test 2: install_cron returns False on subprocess error ───────────────

def test_install_cron_returns_false_on_error() -> None:
    """If crontab command fails (non-zero exit), install_cron returns False."""
    with patch("psg.automation.daily_check.subprocess") as mock_subprocess:
        mock_subprocess.run.return_value = MagicMock(returncode=1)

        result = install_cron("0 3 * * *")

    assert result is False


# ── test 3: remove_cron runs crontab removal command ──────────────────────

def test_remove_cron_runs_crontab_remove() -> None:
    """remove_cron must invoke `crontab -l` then `crontab -r` to remove the cron entry."""
    with patch("psg.automation.daily_check.subprocess") as mock_subprocess:
        mock_subprocess.run.return_value = MagicMock(returncode=0)

        result = remove_cron()

    assert result is True
    assert mock_subprocess.run.call_count == 2  # crontab -l then crontab -r
    first_cmd = mock_subprocess.run.call_args_list[0][0][0]
    assert first_cmd == ["crontab", "-l"]
    second_cmd = mock_subprocess.run.call_args_list[1][0][0]
    assert second_cmd == ["crontab", "-r"]


# ── test 4: remove_cron returns False on error ────────────────────────────

def test_remove_cron_returns_false_on_error() -> None:
    """If the crontab -r command fails, remove_cron returns False."""
    with patch("psg.automation.daily_check.subprocess") as mock_subprocess:
        mock_subprocess.run.return_value = MagicMock(returncode=1)

        result = remove_cron()

    assert result is False


# ── test 5: is_cron_installed returns True when crontab contains marker ────

def test_is_cron_installed_returns_true_when_present() -> None:
    """is_cron_installed must return True when `crontab -l` output
    contains the psg_daily_pipeline marker."""
    with patch("psg.automation.daily_check.subprocess") as mock_subprocess:
        mock_subprocess.run.return_value = MagicMock(
            returncode=0,
            stdout="# psg_daily_pipeline\n0 3 * * * /usr/bin/python3 -m psg.automation.main\n",
        )

        result = is_cron_installed()

    assert result is True


# ── test 6: is_cron_installed returns False when marker absent ─────────────

def test_is_cron_installed_returns_false_when_absent() -> None:
    """is_cron_installed must return False when `crontab -l` output
    does NOT contain the psg_daily_pipeline marker."""
    with patch("psg.automation.daily_check.subprocess") as mock_subprocess:
        mock_subprocess.run.return_value = MagicMock(
            returncode=0,
            stdout="",
        )

        result = is_cron_installed()

    assert result is False


# ── test 7: is_cron_installed returns False on subprocess error ───────────

def test_is_cron_installed_returns_false_on_error() -> None:
    """If crontab -l fails (e.g., no crontab for user), return False."""
    with patch("psg.automation.daily_check.subprocess") as mock_subprocess:
        mock_subprocess.run.return_value = MagicMock(
            returncode=1,
            stdout="",
        )

        result = is_cron_installed()

    assert result is False


# ── test 8: validate_cron_schedule accepts valid schedules ────────────────

def test_validate_cron_schedule_accepts_valid() -> None:
    """validate_cron_schedule must accept standard cron schedules."""
    assert validate_cron_schedule("0 3 * * *") == "0 3 * * *"
    assert validate_cron_schedule("*/5 * * * *") == "*/5 * * * *"
    assert validate_cron_schedule("0 0 1,15 * *") == "0 0 1,15 * *"
    assert validate_cron_schedule("0 0-5 * * *") == "0 0-5 * * *"
    assert validate_cron_schedule("30 4 * * 1-5") == "30 4 * * 1-5"


# ── test 9: validate_cron_schedule rejects shell metacharacters ───────────

def test_validate_cron_schedule_rejects_shell_metas() -> None:
    """validate_cron_schedule must reject schedules with shell metacharacters."""
    for bad in [
        "0 3 * * * ; rm -rf /",
        "0 3 * * * && echo pwned",
        "0 3 * * * | cat /etc/passwd",
        "0 3 * * * `rm -rf /`",
        "0 3 * * * $(whoami)",
    ]:
        with pytest.raises(ValueError, match="shell metacharacters"):
            validate_cron_schedule(bad)


# ── test 10: validate_cron_schedule rejects wrong field count ──────────────

def test_validate_cron_schedule_rejects_wrong_field_count() -> None:
    """validate_cron_schedule must reject schedules without exactly 5 fields."""
    with pytest.raises(ValueError, match="exactly 5 fields"):
        validate_cron_schedule("0 3")
    with pytest.raises(ValueError, match="exactly 5 fields"):
        validate_cron_schedule("0 3 * * * * extra")


# ── test 11: validate_cron_schedule rejects empty schedule ─────────────────

def test_validate_cron_schedule_rejects_empty() -> None:
    """validate_cron_schedule must reject empty strings."""
    with pytest.raises(ValueError, match="empty"):
        validate_cron_schedule("")
    with pytest.raises(ValueError, match="empty"):
        validate_cron_schedule("   ")


# ── test 12: validate_cron_schedule rejects fields with bad chars ──────────

def test_validate_cron_schedule_rejects_bad_field_chars() -> None:
    """validate_cron_schedule must reject fields containing non-cron characters."""
    with pytest.raises(ValueError, match="invalid"):
        validate_cron_schedule("0 abc * * *")


# ── test 13: install_cron raises ValueError on bad schedule (B1) ───────────

def test_install_cron_raises_on_bad_schedule() -> None:
    """install_cron must raise ValueError if schedule fails validation."""
    with pytest.raises(ValueError):
        install_cron("0 3 * * * ; rm -rf /")
