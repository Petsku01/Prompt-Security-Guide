#!/usr/bin/env python3
"""
DEPRECATED: Use cli.py instead.

This file is kept for backward compatibility and will be removed in v2.0.
"""
import warnings
import sys
from pathlib import Path

warnings.warn(
    "tester.py is deprecated. Use 'python -m tools.cli' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Support both `python -m tools.tester` and `python tools/tester.py` execution styles.
try:
    from .cli import main
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools.cli import main  # type: ignore


if __name__ == "__main__":
    sys.exit(main())
