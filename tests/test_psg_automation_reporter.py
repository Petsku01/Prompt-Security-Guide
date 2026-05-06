"""Tests for psg.automation.reporter — PipelineReport & Reporter."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from psg.automation.config import PipelineConfig
from psg.automation.discovery import Source
from psg.automation.generator import AttackVector
from psg.automation.reporter import PipelineReport, Reporter
from psg.automation.tester import ModelTestResult


# ── helpers ────────────────────────────────────────────────────────────────

def _make_config(tmp_path: Path) -> PipelineConfig:
    return PipelineConfig(
        base_dir=tmp_path,
        project_root=tmp_path,
        output_dir=tmp_path,
        datasets_dir=tmp_path / "datasets",
        results_dir=tmp_path / "results",
        logs_dir=tmp_path / "logs",
        known_sources_path=tmp_path / "known_sources.json",
        known_vectors_path=tmp_path / "known_vectors.json",
        reports_dir=tmp_path / "reports",
    )


def _make_result(
    model: str = "llama3:8b",
    total: int = 10,
    flagged: int = 2,
    techniques: dict[str, int] | None = None,
) -> ModelTestResult:
    return ModelTestResult(
        model=model,
        total=total,
        succeeded=total - flagged,
        failed=0,
        flagged=flagged,
        duration_seconds=1.0,
        output_path=Path("/tmp/fake.txt"),
        techniques=techniques if techniques is not None else {},
    )


def _make_source(url: str = "https://example.com") -> Source:
    return Source(
        url=url,
        title="Test Source",
        snippet="A snippet",
        query="test query",
        discovered_at="2026-01-01",
    )


def _make_vector(id_: str = "v1") -> AttackVector:
    return AttackVector(
        id=id_,
        prompt="test prompt",
        technique="test technique",
        description="test description",
        source_url="https://example.com",
    )


# ── test 1: PipelineReport serialization via to_dict ──────────────────────

def test_pipeline_report_to_dict() -> None:
    """PipelineReport.to_dict() must include all scalar fields and
    serialize each ModelTestResult via its own to_dict()."""
    r = _make_result()
    report = PipelineReport(
        date="2026-01-01",
        sources_found=3,
        vectors_generated=5,
        models_tested=1,
        total_tests=10,
        total_flagged=2,
        results=[r],
        top_findings=[{"model": "llama3:8b", "flagged": 2, "rate": "20.0%"}],
    )

    d = report.to_dict()

    assert d["date"] == "2026-01-01"
    assert d["sources_found"] == 3
    assert d["vectors_generated"] == 5
    assert d["models_tested"] == 1
    assert d["total_tests"] == 10
    assert d["total_flagged"] == 2
    assert d["results"] == [r.to_dict()]
    assert d["top_findings"] == [{"model": "llama3:8b", "flagged": 2, "rate": "20.0%"}]


# ── test 2: create_report aggregates sources, vectors, results ───────────

def test_create_report_aggregates(tmp_path: Path) -> None:
    """create_report must count sources, vectors, and aggregate
    total_tests / total_flagged from results."""
    config = _make_config(tmp_path)
    reporter = Reporter(config)

    sources = [_make_source(), _make_source("https://b.com")]
    vectors = [_make_vector("v1"), _make_vector("v2"), _make_vector("v3")]
    results = [
        _make_result("model-a", total=10, flagged=3),
        _make_result("model-b", total=8, flagged=1),
    ]

    report = reporter.create_report(sources, vectors, results)

    assert report.sources_found == 2
    assert report.vectors_generated == 3
    assert report.models_tested == 2
    assert report.total_tests == 18  # 10 + 8
    assert report.total_flagged == 4  # 3 + 1


# ── test 3: top_findings sorted by flagged desc ──────────────────────────

def test_top_findings_sorted_by_flagged_desc(tmp_path: Path) -> None:
    """top_findings list must be sorted descending by flagged count."""
    config = _make_config(tmp_path)
    reporter = Reporter(config)

    results = [
        _make_result("low", total=10, flagged=1),
        _make_result("high", total=10, flagged=8),
        _make_result("mid", total=10, flagged=4),
    ]

    report = reporter.create_report([], [], results)

    assert report.top_findings[0]["model"] == "high"
    assert report.top_findings[0]["flagged"] == 8
    assert report.top_findings[1]["model"] == "mid"
    assert report.top_findings[1]["flagged"] == 4
    assert report.top_findings[2]["model"] == "low"
    assert report.top_findings[2]["flagged"] == 1


# ── test 4: rate calculation ─────────────────────────────────────────────

def test_rate_calculation(tmp_path: Path) -> None:
    """Rate must be flagged/total * 100 with one decimal.  Zero total → 0%."""
    config = _make_config(tmp_path)
    reporter = Reporter(config)

    results = [
        _make_result("r1", total=10, flagged=3),  # 30.0%
        _make_result("r2", total=7, flagged=1),   # ~14.3%
        _make_result("r3", total=0, flagged=0),    # 0%
    ]

    report = reporter.create_report([], [], results)

    rates = {f["model"]: f["rate"] for f in report.top_findings}
    assert rates["r1"] == "30.0%"
    assert rates["r2"] == "14.3%"
    # r3 has 0 flagged so won't appear in top_findings at all


# ── test 5: summary_message SPEC format — warning prefix when flagged > 0 ───────

def test_summary_message_spec_format_flagged_warning(tmp_path: Path) -> None:
    """When total_flagged > 0, the summary message must include the ⚠️
    warning prefix per the SPEC."""
    config = _make_config(tmp_path)
    reporter = Reporter(config)

    report = PipelineReport(
        date="2026-01-01",
        sources_found=1,
        vectors_generated=2,
        models_tested=1,
        total_tests=10,
        total_flagged=5,
        results=[],
        top_findings=[{"model": "llama3:8b", "flagged": 5, "rate": "50.0%"}],
    )

    msg = reporter.generate_summary_message(report)

    assert "⚠️ Flagged: 5" in msg
    assert msg.startswith("🔬 Auto Vector Pipeline Complete")
    assert "📅 Date: 2026-01-01" in msg
    assert "🆕 New vectors: 2" in msg
    assert "🧪 Models tested: 1" in msg


# ── test 6: summary_message SPEC format — no warning when flagged == 0 ───────────

def test_summary_message_spec_format_no_warning_when_zero(tmp_path: Path) -> None:
    """When total_flagged == 0, the summary message uses plain 'Flagged: 0'
    (no ⚠️ emoji) per the SPEC."""
    config = _make_config(tmp_path)
    reporter = Reporter(config)

    report = PipelineReport(
        date="2026-01-01",
        sources_found=0,
        vectors_generated=0,
        models_tested=0,
        total_tests=0,
        total_flagged=0,
        results=[],
        top_findings=[],
    )

    msg = reporter.generate_summary_message(report)

    assert "Flagged: 0" in msg
    assert "⚠️" not in msg


# ── test 7: summary_message top findings limited to 3 ────────────────────────────

def test_summary_message_top_findings_limited_to_three(tmp_path: Path) -> None:
    """Even if there are 5 top_findings, summary_message shows at most 3."""
    config = _make_config(tmp_path)
    reporter = Reporter(config)

    top = [
        {"model": f"m{i}", "flagged": 5 - i, "rate": f"{50 - i * 10}%"}
        for i in range(5)
    ]
    report = PipelineReport(
        date="2026-01-01",
        sources_found=1,
        vectors_generated=1,
        models_tested=5,
        total_tests=50,
        total_flagged=15,
        results=[],
        top_findings=top,
    )

    msg = reporter.generate_summary_message(report)

    # Only m0, m1, m2 appear in the top findings sublist
    assert "- m0: 5 flagged" in msg
    assert "- m2: 3 flagged" in msg
    assert "- m3: 2 flagged" not in msg


# ── test 8: save_report writes markdown file ────────────────────────────

def test_save_report(tmp_path: Path) -> None:
    """save_report must write a .md file to reports_dir and return its Path."""
    config = _make_config(tmp_path)
    reporter = Reporter(config)

    report = PipelineReport(
        date="2026-01-01",
        sources_found=1,
        vectors_generated=2,
        models_tested=1,
        total_tests=10,
        total_flagged=3,
        results=[_make_result()],
        top_findings=[{"model": "llama3:8b", "flagged": 3, "rate": "30.0%"}],
    )

    returned_path = reporter.save_report(report)

    assert returned_path == config.reports_dir / "2026-01-01.md"
    assert returned_path.exists()
    content = returned_path.read_text()
    assert "# Auto Vector Pipeline Report" in content
    assert "2026-01-01" in content


# ── test 9: top_findings capped at 5 entries ────────────────────────────

def test_top_findings_capped_at_five(tmp_path: Path) -> None:
    """Even if 7 results have flagged > 0, top_findings must be at most 5."""
    config = _make_config(tmp_path)
    reporter = Reporter(config)

    results = [_make_result(f"m{i}", total=10, flagged=i + 1) for i in range(7)]

    report = reporter.create_report([], [], results)

    assert len(report.top_findings) == 5


# ── test 10: top_findings excludes zero-flagged results ─────────────────

def test_top_findings_excludes_zero_flagged(tmp_path: Path) -> None:
    """Results with flagged == 0 must NOT appear in top_findings."""
    config = _make_config(tmp_path)
    reporter = Reporter(config)

    results = [
        _make_result("good", total=10, flagged=5),
        _make_result("clean", total=10, flagged=0),
    ]

    report = reporter.create_report([], [], results)

    assert len(report.top_findings) == 1
    assert report.top_findings[0]["model"] == "good"



# ── test 14: ModelTestResult.techniques field ──────────────────────────────

def test_model_test_result_techniques_default_empty() -> None:
    """ModelTestResult must accept an optional techniques dict,
    defaulting to empty for backward compatibility."""
    r = ModelTestResult(
        model="test-model",
        total=5,
        succeeded=3,
        failed=1,
        flagged=1,
        duration_seconds=2.5,
        output_path=Path("/tmp/out.txt"),
    )
    assert r.techniques == {}


def test_model_test_result_techniques_in_to_dict() -> None:
    """to_dict() must include techniques field."""
    r = ModelTestResult(
        model="test-model",
        total=5,
        succeeded=3,
        failed=1,
        flagged=1,
        duration_seconds=2.5,
        output_path=Path("/tmp/out.txt"),
        techniques={"jailbreak": 3, "injection": 1},
    )
    d = r.to_dict()
    assert d["techniques"] == {"jailbreak": 3, "injection": 1}


# ── test 15: format_top_findings_by_technique ───────────────────────────────

def test_format_top_findings_by_technique_groups_techniques(tmp_path: Path) -> None:
    """format_top_findings_by_technique must group flagged vectors by
    technique and list which models flagged each one."""
    config = _make_config(tmp_path)
    reporter = Reporter(config)

    results = [
        _make_result("llama3:8b", total=10, flagged=4, techniques={"jailbreak": 3, "injection": 1}),
        _make_result("mistral:7b", total=10, flagged=2, techniques={"jailbreak": 2}),
    ]

    findings = reporter.format_top_findings_by_technique(results)

    # jailbreak flagged on both models, total count 5
    assert findings[0]["technique"] == "jailbreak"
    assert "llama3:8b" in findings[0]["models"]
    assert "mistral:7b" in findings[0]["models"]
    assert findings[0]["total"] == 5
    # injection flagged only on llama3:8b
    assert findings[1]["technique"] == "injection"
    assert findings[1]["models"] == ["llama3:8b"]
    assert findings[1]["total"] == 1


def test_format_top_findings_by_technique_sorted_by_total_desc(tmp_path: Path) -> None:
    """Technique findings must be sorted by total flagged count descending."""
    config = _make_config(tmp_path)
    reporter = Reporter(config)

    results = [
        _make_result("model-a", total=10, flagged=5, techniques={"injection": 1, "jailbreak": 4}),
    ]

    findings = reporter.format_top_findings_by_technique(results)
    assert findings[0]["technique"] == "jailbreak"
    assert findings[1]["technique"] == "injection"


def test_format_top_findings_by_technique_empty_results(tmp_path: Path) -> None:
    """With no results, format_top_findings_by_technique returns empty list."""
    config = _make_config(tmp_path)
    reporter = Reporter(config)

    findings = reporter.format_top_findings_by_technique([])
    assert findings == []


def test_format_top_findings_by_technique_no_technique_data(tmp_path: Path) -> None:
    """When results have empty techniques dicts, the output should be empty."""
    config = _make_config(tmp_path)
    reporter = Reporter(config)

    results = [_make_result("model-a", total=10, flagged=3, techniques={})]
    findings = reporter.format_top_findings_by_technique(results)
    assert findings == []


# ── test 16: summary_message uses technique-level format when available ────

def test_summary_message_technique_format_when_available(tmp_path: Path) -> None:
    """When results have technique data, summary_message must show
    technique-level findings in the SPEC format:
    ⚠️ Top techniques:
    - [jailbreak] flagged on llama3:8b, mistral:7b (3)
    """
    config = _make_config(tmp_path)
    reporter = Reporter(config)

    results = [
        _make_result("llama3:8b", total=10, flagged=4, techniques={"jailbreak": 3, "injection": 1}),
        _make_result("mistral:7b", total=10, flagged=2, techniques={"jailbreak": 2}),
    ]
    report = reporter.create_report([], [], results)

    msg = reporter.generate_summary_message(report)

    assert "Top techniques:" in msg
    assert "[jailbreak] flagged on" in msg
    assert "llama3:8b" in msg
    assert "mistral:7b" in msg
    # Count in parentheses
    assert "(5)" in msg  # jailbreak total across models


def test_summary_message_falls_back_to_model_format_no_techniques(tmp_path: Path) -> None:
    """When no technique data is available, summary_message should fall back
    to model-level formatting (the current behavior)."""
    config = _make_config(tmp_path)
    reporter = Reporter(config)

    results = [
        _make_result("llama3:8b", total=10, flagged=3, techniques={}),
        _make_result("mistral:7b", total=10, flagged=1, techniques={}),
    ]
    report = reporter.create_report([], [], results)

    msg = reporter.generate_summary_message(report)

    # Should NOT have technique format section
    assert "Top techniques:" not in msg
    # Should have model-level format (existing behavior)
    assert "Top findings:" in msg


# ── test 17: Markdown report includes technique-level section ──────────────

def test_markdown_includes_technique_section_when_available(tmp_path: Path) -> None:
    """When results have technique data, markdown report must include a
    'Top Findings by Technique' section."""
    config = _make_config(tmp_path)
    reporter = Reporter(config)

    results = [
        _make_result("llama3:8b", total=10, flagged=4, techniques={"jailbreak": 3, "injection": 1}),
        _make_result("mistral:7b", total=10, flagged=2, techniques={"jailbreak": 2}),
    ]
    report = reporter.create_report([], [], results)

    md = reporter.generate_markdown(report)

    assert "Top Findings by Technique" in md
    assert "[jailbreak]" in md
    assert "llama3:8b" in md
    assert "mistral:7b" in md


def test_markdown_no_technique_section_when_no_data(tmp_path: Path) -> None:
    """When no technique data exists, markdown should not include a technique
    section."""
    config = _make_config(tmp_path)
    reporter = Reporter(config)

    results = [
        _make_result("llama3:8b", total=10, flagged=3, techniques={}),
    ]
    report = reporter.create_report([], [], results)

    md = reporter.generate_markdown(report)

    assert "Top Findings by Technique" not in md


# ── test 18: PipelineReport.top_technique_findings ──────────────────────────

def test_pipeline_report_includes_top_technique_findings(tmp_path: Path) -> None:
    """PipelineReport must include top_technique_findings field."""
    report = PipelineReport(
        date="2026-01-01",
        sources_found=1,
        vectors_generated=2,
        models_tested=1,
        total_tests=10,
        total_flagged=3,
        results=[],
        top_findings=[],
        top_technique_findings=[{"technique": "jailbreak", "models": ["llama3:8b"], "total": 3}],
    )

    d = report.to_dict()
    assert "top_technique_findings" in d
    assert d["top_technique_findings"][0]["technique"] == "jailbreak"


def test_create_report_populates_technique_findings(tmp_path: Path) -> None:
    """create_report must populate top_technique_findings when technique data
    is available."""
    config = _make_config(tmp_path)
    reporter = Reporter(config)

    results = [
        _make_result("llama3:8b", total=10, flagged=4, techniques={"jailbreak": 3, "injection": 1}),
    ]
    report = reporter.create_report([], [], results)

    assert len(report.top_technique_findings) == 2
    assert report.top_technique_findings[0]["technique"] == "jailbreak"
    assert report.top_technique_findings[0]["total"] == 3


# ── test 19: summary_message path matches saved report filename (B7) ─────

def test_summary_message_path_matches_saved_report(tmp_path: Path) -> None:
    """The 'Full report' path in summary_message must use the same date format
    (YYYY-MM-DD.md) as the file saved by save_report(), not YYYYMMDD.md."""
    config = _make_config(tmp_path)
    reporter = Reporter(config)

    report = PipelineReport(
        date="2026-01-15",
        sources_found=1,
        vectors_generated=2,
        models_tested=1,
        total_tests=10,
        total_flagged=0,
        results=[],
        top_findings=[],
    )

    msg = reporter.generate_summary_message(report)
    assert "reports/2026-01-15.md" in msg
    assert "reports/20260115.md" not in msg