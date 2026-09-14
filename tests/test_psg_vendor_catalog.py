"""Tests for the L1B3RT4S vendor catalog (curated from elder-plinius/L1B3RT4S)."""

from __future__ import annotations

import json
from pathlib import Path

from psg.catalog import load_catalog

VENDOR = Path(__file__).resolve().parents[1] / "datasets" / "l1b3rt4s_vendor.json"


def test_vendor_catalog_loads() -> None:
    catalog = load_catalog(str(VENDOR))
    assert len(catalog) >= 70, "vendor catalog has shrunk unexpectedly"


def test_vendor_catalog_ids_unique() -> None:
    data = json.loads(VENDOR.read_text(encoding="utf-8"))
    ids = [p["id"] for p in data["prompts"]]
    assert len(ids) == len(set(ids)), "duplicate ids in vendor catalog"


def test_vendor_catalog_fields_valid() -> None:
    data = json.loads(VENDOR.read_text(encoding="utf-8"))
    for p in data["prompts"]:
        assert p["attack_type"] in ("obedience", "policy-bypass")
        assert p["tier"] in ("P0", "P1", "P2", "P3")
        assert len(p["prompt"]) >= 20
        assert "elder-plinius/L1B3RT4S" in p["source"]


def test_vendor_catalog_targets_frontier_models() -> None:
    data = json.loads(VENDOR.read_text(encoding="utf-8"))
    text = json.dumps(data).lower()
    # At least these frontier targets must appear
    for marker in ("gpt", "opus", "gemini", "grok", "deepseek"):
        assert marker in text, f"frontier target missing: {marker}"


def test_vendor_schema_meta() -> None:
    data = json.loads(VENDOR.read_text(encoding="utf-8"))
    assert data["count"] == len(data["prompts"])
    assert "AGPL-3.0" in data["license"]  # attribution per upstream license
    assert data["source"].startswith("https://github.com/elder-plinius/")
