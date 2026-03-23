from __future__ import annotations

import json

import pytest

from psg.catalog import load_catalog


def test_load_catalog_attacks_root(tmp_path) -> None:
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({"attacks": [{"id": "1", "prompt": "hello"}]}), encoding="utf-8")

    attacks = load_catalog(str(catalog))

    assert len(attacks) == 1
    assert attacks[0].id == "1"
    assert attacks[0].prompt == "hello"


def test_load_catalog_list_root_with_strings(tmp_path) -> None:
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps(["one", {"id": "2", "text": "two"}]), encoding="utf-8")

    attacks = load_catalog(str(catalog))

    assert [a.prompt for a in attacks] == ["one", "two"]


def test_load_catalog_unsupported_schema_raises(tmp_path) -> None:
    catalog = tmp_path / "bad.json"
    catalog.write_text(json.dumps({"unexpected": "shape"}), encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported catalog schema"):
        load_catalog(str(catalog))
