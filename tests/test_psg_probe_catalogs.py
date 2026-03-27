from __future__ import annotations

from collections import Counter

from psg.catalog import load_catalog


def _subcategory_counts(path: str) -> Counter[str]:
    attacks = load_catalog(path)
    return Counter(str(a.metadata.get("subcategory", "")) for a in attacks)


def test_hallucination_probe_catalog_has_expected_subcategories() -> None:
    counts = _subcategory_counts("datasets/hallucination_detection_probes.json")
    assert sum(counts.values()) >= 50
    assert counts["fake_citations"] > 0
    assert counts["invented_facts"] > 0
    assert counts["false_urls"] > 0
    assert counts["non_existent_apis"] > 0
    assert counts["package_hallucination"] > 0
    assert counts["code_hallucination"] > 0
    assert counts["confidently_wrong_facts"] > 0


def test_data_leakage_probe_catalog_has_expected_subcategories() -> None:
    counts = _subcategory_counts("datasets/data_leakage_probes.json")
    assert sum(counts.values()) >= 50
    assert counts["memorization_attacks"] > 0
    assert counts["pii_extraction"] > 0
    assert counts["system_prompt_leaks"] > 0
    assert counts["training_membership_inference"] > 0
    assert counts["indirect_leakage"] > 0
    assert counts["model_inversion"] > 0
