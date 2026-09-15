"""Tests for the parseltongue + P4RS3LT0NGV3 catalog."""
import json
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[1] / "datasets" / "parseltongue_attacks.json"


@pytest.fixture(scope="module")
def catalog() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"), strict=False)


def test_catalog_loads(catalog: dict) -> None:
    assert catalog["count"] == len(catalog["prompts"])
    assert catalog["count"] == 792


def test_parseltongue_grid_complete(catalog: dict) -> None:
    """33 triggers x 6 techniques x 3 intensities = 594, one each."""
    pt = [p for p in catalog["prompts"] if p["id"].startswith("parseltongue_")]
    assert len(pt) == 594
    combos = {(p["trigger"], p["technique"], p["intensity"]) for p in pt}
    assert len(combos) == 594  # no duplicates


def test_obfuscation_actually_transforms(catalog: dict) -> None:
    """Each parseltongue leetspeak entry must differ from the plain sentence."""
    pt = [
        p
        for p in catalog["prompts"]
        if p.get("technique") == "leetspeak" and "trigger" in p
    ]
    assert len(pt) == 99, "expected 99 parseltongue leetspeak entries"
    plain = [p for p in pt if p["trigger"] in p["prompt"]]
    assert not plain, "trigger survived obfuscation un-transformed"


def test_p4rs3lt0ngv3_transforms_unique(catalog: dict) -> None:
    p4 = [p for p in catalog["prompts"] if p["id"].startswith("p4rs3lt0ngv3_")]
    assert len(p4) == 198
    ids = [p["id"] for p in p4]
    assert len(ids) == len(set(ids))


def test_schema_fields(catalog: dict) -> None:
    required = {"id", "prompt", "technique", "attack_type", "tier", "source"}
    for p in catalog["prompts"][:50]:
        missing = required - set(p)
        assert not missing, f"{p['id']} missing {missing}"


def test_no_prompt_whitespace_only(catalog: dict) -> None:
    for p in catalog["prompts"]:
        assert p["prompt"].strip(), f"empty prompt: {p['id']}"