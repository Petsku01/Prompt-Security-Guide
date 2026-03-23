"""Deprecated entrypoint.

Use: python -m psg --model <model> --catalog <path>
"""
from __future__ import annotations

import warnings

warnings.warn(
    "tester.py is deprecated and will be removed in a future release. "
    "Use `python -m psg` instead.",
    DeprecationWarning,
    stacklevel=2,
)

from psg.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
