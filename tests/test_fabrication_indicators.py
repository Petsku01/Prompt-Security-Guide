"""Tests for externalized fabrication-indicator config (Phase 2.6).

The classifier's fake-URL/fake-package denylist lives in
``datasets/fabrication_indicators.json`` so it can be updated without code
changes. These tests cover the JSON loader's edge cases and verify the
compiled regex still fires on representative inputs.
"""
from __future__ import annotations

import json

import pytest

from psg.security import classifier as clf


def test_builtin_indicators_still_catch_representative_samples() -> None:
    """Sanity check that the shipped JSON catches obviously-fake signals.

    These match the ``fabricated_reference`` regex in ``HARMFUL_PATTERNS``,
    which is built from the JSON indicator lists.
    """
    samples = [
        "GET /v1/admin/steal-secrets?user=all",
        "POST /v2/auth/recover-deleted",
        "pip install fake-anthropic-sdk",
        "import hallucinated_anthropic_client",
    ]
    for sample in samples:
        labels = clf.detect_harmful_content(sample)
        assert "fabricated_reference" in labels, (
            f"missed fabricated signal in {sample!r}; got labels={labels}"
        )


def test_benign_urls_are_not_flagged_as_fabricated() -> None:
    benign = [
        "See https://github.com/anthropics/anthropic-sdk-python for the SDK.",
        "pip install anthropic",
        "GET /v1/messages",
    ]
    for sample in benign:
        labels = clf.detect_harmful_content(sample)
        assert "fabricated_reference" not in labels, (
            f"FP on benign {sample!r}; got labels={labels}"
        )


def test_loader_falls_back_to_defaults_on_missing_file(monkeypatch, tmp_path) -> None:
    missing = tmp_path / "does_not_exist.json"
    monkeypatch.setattr(clf, "_FABRICATION_INDICATOR_PATH", missing)
    result = clf._load_fabrication_indicators()

    # All expected keys exist with safe defaults.
    assert result["suspicious_api_paths"] == []
    assert result["implausible_journal_markers"] == []
    assert result["authority_domains"] == {}


def test_loader_falls_back_on_malformed_json(monkeypatch, tmp_path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("this is not JSON", encoding="utf-8")
    monkeypatch.setattr(clf, "_FABRICATION_INDICATOR_PATH", bad)
    result = clf._load_fabrication_indicators()

    assert result["suspicious_api_paths"] == []


def test_loader_fills_missing_keys_with_defaults(monkeypatch, tmp_path) -> None:
    partial = tmp_path / "partial.json"
    partial.write_text(json.dumps({"suspicious_api_paths": ["foo"]}), encoding="utf-8")
    monkeypatch.setattr(clf, "_FABRICATION_INDICATOR_PATH", partial)
    result = clf._load_fabrication_indicators()

    assert result["suspicious_api_paths"] == ["foo"]
    assert result["implausible_journal_markers"] == []  # filled default
    assert result["authority_domains"] == {}


def test_compile_fabricated_reference_pattern_handles_empty_lists() -> None:
    """A minimal indicator set produces a never-matching pattern, not a crash."""
    pattern = clf._compile_fabricated_reference_pattern(
        {
            "suspicious_api_paths": [],
            "suspicious_package_fragments": [],
            "suspicious_import_prefixes": [],
            "implausible_journal_markers": [],
            "authority_domains": {},
            "cdc_non_health_keywords": [],
        }
    )
    assert pattern.search("anything at all") is None


def test_compile_fabricated_reference_pattern_uses_provided_paths() -> None:
    """Custom indicator lists produce regexes that match them."""
    pattern = clf._compile_fabricated_reference_pattern(
        {
            "suspicious_api_paths": ["custom-bad-route"],
            "suspicious_package_fragments": ["evil-"],
            "suspicious_import_prefixes": ["evil_"],
            "implausible_journal_markers": [],
            "authority_domains": {},
            "cdc_non_health_keywords": [],
        }
    )
    assert pattern.search("GET /v1/custom-bad-route")
    assert pattern.search("pip install evil-package")
    assert pattern.search("import evil_thing")
    assert not pattern.search("import anthropic")


@pytest.mark.parametrize(
    "bad_journal_marker",
    [
        "doi:10.1234/fake-journal/article-123",
        "https://doi.org/10.9999/ultimate-journal/x",
    ],
)
def test_implausible_journal_markers_still_detected(bad_journal_marker: str) -> None:
    # Sanity that IMPLAUSIBLE_JOURNAL_MARKERS loaded from JSON work.
    labels = clf.detect_fabricated_references(bad_journal_marker)
    assert "fabricated_doi_unverified" in labels
