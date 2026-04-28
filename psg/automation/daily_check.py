#!/usr/bin/env python3
"""Check if daily discovery has been run."""

import sys
from datetime import datetime
from pathlib import Path

MARKER_FILE = Path(__file__).parent / ".last_discovery"


def check() -> str:
    """Check if discovery needed today."""
    today = datetime.now().strftime("%Y-%m-%d")

    if MARKER_FILE.exists():
        last_run = MARKER_FILE.read_text().strip()
        if last_run == today:
            return "ALREADY_RUN"

    return "RUN_NEEDED"


def mark() -> None:
    """Mark today as done."""
    today = datetime.now().strftime("%Y-%m-%d")
    MARKER_FILE.write_text(today)
    print(f"Marked {today} as complete")


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
