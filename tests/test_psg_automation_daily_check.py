"""Tests for psg.automation.daily_check — 6 tests.

Uses tmp_path for marker file via monkeypatch; no external deps.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

import psg.automation.daily_check as dc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _marker_path(tmp_path: Path) -> Path:
    """Return a marker file path inside tmp_path."""
    return tmp_path / ".last_discovery"


def _patch_marker(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    """Monkeypatch the module-level MARKER_FILE to *path*."""
    monkeypatch.setattr(dc, "MARKER_FILE", path)


# ---------------------------------------------------------------------------
# 1. check() — no marker file
# ---------------------------------------------------------------------------

def test_check_returns_run_needed_when_no_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    marker = _marker_path(tmp_path)
    _patch_marker(monkeypatch, marker)

    assert dc.check() == "RUN_NEEDED"


# ---------------------------------------------------------------------------
# 2. check() — marker has today's date
# ---------------------------------------------------------------------------

def test_check_returns_already_run_when_today(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    marker = _marker_path(tmp_path)
    _patch_marker(monkeypatch, marker)

    today = datetime.now().strftime("%Y-%m-%d")
    marker.write_text(today)

    assert dc.check() == "ALREADY_RUN"


# ---------------------------------------------------------------------------
# 3. check() — marker has a stale (yesterday) date
# ---------------------------------------------------------------------------

def test_check_returns_run_needed_when_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    marker = _marker_path(tmp_path)
    _patch_marker(monkeypatch, marker)

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    marker.write_text(yesterday)

    assert dc.check() == "RUN_NEEDED"


# ---------------------------------------------------------------------------
# 4. mark() — writes today's date
# ---------------------------------------------------------------------------

def test_mark_writes_today(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    marker = _marker_path(tmp_path)
    _patch_marker(monkeypatch, marker)

    dc.mark()

    today = datetime.now().strftime("%Y-%m-%d")
    assert marker.read_text().strip() == today


# ---------------------------------------------------------------------------
# 5. main() — check action, already run → return 0
# ---------------------------------------------------------------------------

def test_main_check_returns_0_if_already_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    marker = _marker_path(tmp_path)
    _patch_marker(monkeypatch, marker)

    today = datetime.now().strftime("%Y-%m-%d")
    marker.write_text(today)

    monkeypatch.setattr(sys, "argv", ["daily_check.py", "check"])

    assert dc.main() == 0


# ---------------------------------------------------------------------------
# 6. main() — check action, run needed → return 1
# ---------------------------------------------------------------------------

def test_main_check_returns_1_if_needed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    marker = _marker_path(tmp_path)
    _patch_marker(monkeypatch, marker)

    # No marker file → RUN_NEEDED
    monkeypatch.setattr(sys, "argv", ["daily_check.py", "check"])

    assert dc.main() == 1