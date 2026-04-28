from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

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


def test_encoding_attacks_catalog_has_minimum_size_and_techniques() -> None:
    data = json.loads(
        Path("datasets/encoding_attacks.json").read_text(encoding="utf-8")
    )
    attacks = data.get("attacks", [])
    assert len(attacks) >= 30

    techniques = {str(attack.get("technique", "")) for attack in attacks}
    assert "base64" in techniques
    assert "rot13" in techniques
    assert "unicode_homoglyph" in techniques
    assert "leetspeak" in techniques
    assert "mixed_encoding" in techniques


def test_target_catalogs_do_not_contain_unknown_categories() -> None:
    paths = list(Path("datasets").glob("auto_*.json")) + [
        Path("datasets/jailbreak_community.json"),
        Path("datasets/obliteratus_attacks.json"),
        Path("datasets/new_vectors_2026-03-06.json"),
    ]

    def _collect_unknowns(obj: object) -> list[str]:
        unknowns: list[str] = []

        def _walk(current: object, trail: str = "") -> None:
            if isinstance(current, dict):
                for key, value in current.items():
                    path = f"{trail}.{key}" if trail else key
                    if (
                        key == "category"
                        and isinstance(value, str)
                        and value.lower() == "unknown"
                    ):
                        unknowns.append(path)
                    _walk(value, path)
            elif isinstance(current, list):
                for idx, item in enumerate(current):
                    _walk(item, f"{trail}[{idx}]")

        _walk(obj)
        return unknowns

    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert not _collect_unknowns(data), f"unknown category found in {path}"
