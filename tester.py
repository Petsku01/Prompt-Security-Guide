"""Deprecated entrypoint.

Use: python -m jailbreak_tester --model <model> --catalog <path>
Legacy implementation moved to legacy/tester_v2.py.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "tester.py is deprecated and will be removed in a future release. "
    "Use `python -m jailbreak_tester` instead.",
    DeprecationWarning,
    stacklevel=2,
)

from legacy.tester_v2 import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
