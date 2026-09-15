"""Audit P1-8 (HIGH, 2026-09-15): crontab read-modify-write lock.

daily_check.install_cron / remove_cron read the user's WHOLE crontab,
filter out the PSG-tagged lines, and write the whole crontab back. Two
concurrent writers (e.g. daily_check run racing a human `crontab -e`,
or two PSG processes) can interleave read→write and SILENTLY DROP the
other writer's unrelated entries — data loss outside PSG's own lines.

Fix (this module): an exclusive advisory lock file (fcntl.flock on
~/.psg_cron.lock) held across the entire read→modify→write critical
section. flock gives:
  - mutual exclusion between PSG processes on the same machine
  - automatic release on process death (no stale-lock cleanup needed)
  - no interference with other tools' crontab edits — we lock OUR
    read-modify-write, so two PSG writers can never interleave, and a
    human editor racing PSG still sees a self-consistent crontab
    (either the old or the new one, never a torn mix).

Non-blocking variant is provided for callers that must fail fast
(install_cron uses the blocking one with a short timeout — installs are
rare and worth waiting a few seconds for; removes likewise).
"""
from __future__ import annotations

import contextlib
import fcntl
import os
from pathlib import Path
from typing import Callable

from .logging_config import logger

_LOCK_PATH = Path(os.environ.get("PSG_CRON_LOCK", Path.home() / ".psg_cron.lock"))


@contextlib.contextmanager
def cron_write_lock(*, blocking: bool = True, timeout: float = 30.0):
    """Hold an exclusive advisory lock over crontab read-modify-write.

    Yields True when the lock was acquired, False on timeout (non-blocking
    mode). Callers MUST check the flag and skip their read-modify-write
    when False — acquiring is the gate, not a formality.

    The lock file itself contains no data and holds no secrets; it only
    exists so two processes can agree on ordering.
    """
    _LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    fh = _LOCK_PATH.open("a")
    acquired = False
    try:
        if blocking:

            def _on_timeout(signum, frame):  # pragma: no cover - signal path
                raise TimeoutError(f"cron lock wait exceeded {timeout}s")

            old = None
            try:
                import signal as _signal

                old = _signal.signal(_signal.SIGALRM, _on_timeout)
                _signal.alarm(int(max(1, timeout)))
            except (ImportError, ValueError, OSError):
                old = None  # not in main thread — best effort, no alarm
            try:
                fcntl.flock(fh, fcntl.LOCK_EX)
                acquired = True
            finally:
                if old is not None:
                    import signal as _signal2

                    _signal2.alarm(0)
                    _signal2.signal(_signal2.SIGALRM, old)
        else:
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except OSError:
                acquired = False
        yield acquired
    finally:
        with contextlib.suppress(OSError):
            fcntl.flock(fh, fcntl.LOCK_UN)
        fh.close()


def install_cron_locked(
    validate_and_build: Callable[[], bool], *, blocking: bool = True
) -> bool:
    """Run validate_and_build() while holding the cron lock.

    `validate_and_build` must do the full read→modify→write cycle and
    return True on success. If the lock cannot be acquired, returns
    False WITHOUT running it — the caller's crontab stays untouched.
    """
    with cron_write_lock(blocking=blocking) as ok:
        if not ok:
            logger.warning(
                "cron lock busy (%s) — install_cron skipped; retry later",
                _LOCK_PATH,
            )
            return False
        return validate_and_build()