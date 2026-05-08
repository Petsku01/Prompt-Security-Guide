#!/usr/bin/env python3
"""Check if daily discovery has been run and manage cron scheduling."""

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from .logging_config import logger

_DEFAULT_MARKER_FILE = Path(__file__).parent / ".last_discovery"

# Marker string embedded in crontab entries so we can identify our jobs
CRON_MARKER = "psg_daily_pipeline"

# Shell metacharacters that must never appear in a cron schedule
_SHELL_META_RE = re.compile(r'[;&|`$(){}!<>"\\]')


def validate_cron_schedule(schedule: str) -> str:
    """Validate 5-field cron schedule. Rejects shell metacharacters. Raises ValueError if invalid."""
    if not schedule or not schedule.strip():
        raise ValueError("Cron schedule must not be empty")

    # Reject shell metacharacters outright
    if _SHELL_META_RE.search(schedule):
        raise ValueError(
            f"Cron schedule contains shell metacharacters: {schedule!r}"
        )

    fields = schedule.split()
    if len(fields) != 5:
        raise ValueError(
            f"Cron schedule must have exactly 5 fields, got {len(fields)}: {schedule!r}"
        )

    # Each field may contain: digits, *, ranges (1-5), steps (*/5, 1-5/2), and commas
    _field_re = re.compile(r"^[0-9,\-\*/]+$")
    for i, field in enumerate(fields):
        if not _field_re.match(field):
            raise ValueError(
                f"Cron field {i + 1} is invalid: {field!r} (in schedule {schedule!r})"
            )

    return schedule


def install_cron(schedule: str = "0 3 * * *") -> bool:
    """Install tagged cron entry for daily pipeline. Returns True on success.

    Raises ValueError if schedule is invalid. Entry is tagged with
    CRON_MARKER for later lookup by is_cron_installed().
    """
    validate_cron_schedule(schedule)

    # Retrieve existing crontab (may be empty)
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        existing = result.stdout if result.returncode == 0 else ""
    except (subprocess.SubprocessError, OSError):
        existing = ""

    # Remove any previous marker-tagged line to avoid duplicates
    lines = [
        ln for ln in existing.splitlines()
        if CRON_MARKER not in ln
    ]

    # Add the new schedule line
    cron_line = f"{schedule} cd \"$HOME\" && python3 -m psg.automation.main # {CRON_MARKER}"
    lines.append(cron_line)

    new_crontab = "\n".join(lines) + "\n"

    try:
        result = subprocess.run(
            ["crontab", "-"],
            input=new_crontab,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def remove_cron() -> bool:
    """Remove the psg cron entry from the current user's crontab.

    Returns True on success, False on failure.
    """
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return False
        existing = result.stdout
    except (subprocess.SubprocessError, OSError):
        return False

    lines = [
        ln for ln in existing.splitlines()
        if CRON_MARKER not in ln
    ]

    if not lines:
        # Nothing left — remove the crontab entirely
        try:
            result = subprocess.run(
                ["crontab", "-r"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, OSError):
            return False

    new_crontab = "\n".join(lines) + "\n"

    try:
        result = subprocess.run(
            ["crontab", "-"],
            input=new_crontab,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def is_cron_installed() -> bool:
    """Check whether the psg cron entry is present in the current user's crontab.

    Returns True if the marker is found, False otherwise.
    """
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return False
        return CRON_MARKER in result.stdout
    except (subprocess.SubprocessError, OSError):
        return False


def _marker_file(config_dir: Path | None = None) -> Path:
    """Return marker file path.

    Uses config_dir/.last_discovery if given, else package default
    (kept for backwards compatibility).
    """
    if config_dir is not None:
        config_dir = Path(config_dir)
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / ".last_discovery"
    return _DEFAULT_MARKER_FILE


def check(config_dir: Path | None = None) -> str:
    """Check if discovery needed today."""
    marker = _marker_file(config_dir)
    today = datetime.now().strftime("%Y-%m-%d")

    if marker.exists():
        last_run = marker.read_text().strip()
        if last_run == today:
            return "ALREADY_RUN"

    return "RUN_NEEDED"


def mark(config_dir: Path | None = None) -> None:
    """Mark today as done."""
    marker = _marker_file(config_dir)
    today = datetime.now().strftime("%Y-%m-%d")
    marker.write_text(today)
    logger.info(f"Marked {today} as complete")


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: daily_check.py [check|mark]")
        return 1

    action = sys.argv[1]

    if action == "check":
        result = check()
        print(result)
        return 0 if result == "ALREADY_RUN" else 1
    elif action == "mark":
        mark()
        return 0
    else:
        print(f"Unknown action: {action}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
