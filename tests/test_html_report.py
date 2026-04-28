"""Tests for psg.reporting.html_report module."""

from __future__ import annotations

import tempfile
from pathlib import Path

from psg.models import AttemptResult, RunSummary
from psg.reporting.html_report import (
    generate_html_string,
    write_html_report,
)


def _make_summary(total=10, flagged=2, failed=1, duration_seconds=5.0) -> RunSummary:
    """Create a test summary."""
    return RunSummary(
        total=total,
        succeeded=total - failed,
        failed=failed,
        flagged=flagged,
        duration_seconds=duration_seconds,
    )


def _make_results() -> list[AttemptResult]:
    """Create test results."""
    return [
        AttemptResult(
            attack_id="ATK-001",
            prompt="Test prompt 1",
            response_text="I cannot help with that.",
            flagged=False,
            labels=[],
        ),
        AttemptResult(
            attack_id="ATK-002",
            prompt="Test prompt 2",
            response_text="Here is harmful content...",
            flagged=True,
            labels=["harmful"],
        ),
        AttemptResult(
            attack_id="ATK-003",
            prompt="Test prompt 3",
            response_text="",
            flagged=False,
            labels=[],
            error="Connection timeout",
        ),
    ]


def test_generate_html_string_basic():
    """Test generating HTML string."""
    summary = _make_summary()
    results = _make_results()

    html = generate_html_string(
        summary, results, model="test-model", catalog="test.json"
    )

    assert "<!DOCTYPE html>" in html
    assert "PSG Security Report" in html
    assert "test-model" in html
    assert "test.json" in html


def test_generate_html_contains_stats():
    """Test that HTML contains statistics."""
    summary = _make_summary(total=10, flagged=2, failed=1)
    results = _make_results()

    html = generate_html_string(summary, results)

    assert ">10<" in html  # Total
    assert ">2<" in html  # Flagged
    assert ">1<" in html  # Failed
    assert ">7<" in html  # Defended (10 - 2 - 1)


def test_generate_html_contains_results():
    """Test that HTML contains result rows."""
    summary = _make_summary()
    results = _make_results()

    html = generate_html_string(summary, results)

    assert "ATK-001" in html
    assert "ATK-002" in html
    assert "ATK-003" in html


def test_generate_html_badges():
    """Test that HTML contains status badges."""
    summary = _make_summary()
    results = _make_results()

    html = generate_html_string(summary, results)

    assert "badge-success" in html  # Defended
    assert "badge-danger" in html  # Flagged
    assert "badge-warning" in html  # Failed


def test_generate_html_defense_rate():
    """Test defense rate calculation."""
    summary = _make_summary(total=100, flagged=20)
    results = []

    html = generate_html_string(summary, results)

    # 80% defended (100 - 20 - 0 = 80)
    assert "80.0%" in html or "80%" in html


def test_generate_html_escapes_special_chars():
    """Test that special characters in user data are escaped."""
    summary = _make_summary()
    results = [
        AttemptResult(
            attack_id="<script>alert('xss')</script>",
            prompt="<img onerror='hack'>",
            response_text="test",
            flagged=False,
            labels=[],
        ),
    ]

    html = generate_html_string(summary, results)

    # User data should be escaped (template has legitimate <script> for JS)
    assert "&lt;script&gt;" in html  # attack_id escaped
    assert "&lt;img onerror=" in html  # prompt escaped


def test_write_html_report_creates_file():
    """Test writing HTML report to file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "report.html"
        summary = _make_summary()
        results = _make_results()

        write_html_report(str(path), summary, results)

        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content


def test_write_html_report_creates_parent_dirs():
    """Test that parent directories are created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "subdir" / "nested" / "report.html"
        summary = _make_summary()
        results = []

        write_html_report(str(path), summary, results)

        assert path.exists()


def test_generate_html_empty_results():
    """Test generating HTML with no results."""
    summary = _make_summary(total=0, flagged=0, failed=0)
    results = []

    html = generate_html_string(summary, results)

    assert "<!DOCTYPE html>" in html
    assert "0%" in html or "0.0%" in html  # Defense rate


def test_generate_html_low_defense_rate_danger():
    """Test that low defense rate shows danger class."""
    summary = _make_summary(total=100, flagged=50, failed=10)  # 40% defended
    results = []

    html = generate_html_string(summary, results)

    # Should have danger class on progress bar
    assert 'class="progress-fill danger"' in html
