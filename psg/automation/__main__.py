"""CLI entry point for psg.automation."""

import logging

from .main import main

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    raise SystemExit(main())
