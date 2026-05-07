from __future__ import annotations

import json
import logging

import pytest

from psg.catalog import load_catalog
from psg.catalog_validator import validate_catalog_file


def test_validate_catalog_file_detects_duplicate_id_and_missing_required(
    tmp_path,
) -> None:
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(
        json.dumps(
            {
                "attacks": [
                    {"id": "a-1", "prompt": "first"},
                    {"id": "a-1", "prompt": "second"},
                    {"id": "a-3"},
                ]
            }
        ),
        encoding="utf-8",
    )

    report = validate_catalog_file(catalog_path)

    assert report["skipped"] is False
    assert any("Duplicate id" in e for e in report["errors"])
    assert any(
        "Missing required field(s)" in e and "prompt" in e for e in report["errors"]
    )


def test_validate_catalog_file_warnings_for_optional_fields(tmp_path) -> None:
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(
        json.dumps({"attacks": [{"id": "a-1", "prompt": "hello"}]}), encoding="utf-8"
    )

    report = validate_catalog_file(catalog_path)

    assert report["errors"] == []
    assert any(
        "Missing optional field(s): technique, source, tier" in w
        for w in report["warnings"]
    )


def test_validate_catalog_file_skips_non_catalog_schema(tmp_path) -> None:
    payload = tmp_path / "golden_like.json"
    payload.write_text(json.dumps({"examples": [{"id": "x"}]}), encoding="utf-8")

    report = validate_catalog_file(payload)

    assert report["skipped"] is True
    assert report["errors"] == []
    assert report["checked"] == 0


def test_load_catalog_warns_on_non_dict_non_str_item(tmp_path, caplog) -> None:
    """Invalid catalog items (e.g. integers) should trigger a warning and be skipped."""
    catalog = tmp_path / "catalog.json"
    catalog.write_text(
        json.dumps({"attacks": [{"id": "a1", "prompt": "valid"}, 42, None]}),
        encoding="utf-8",
    )

    with caplog.at_level(logging.WARNING, logger="psg.catalog"):
        attacks = load_catalog(str(catalog))

    # Only the valid dict item should survive
    assert len(attacks) == 1
    assert attacks[0].id == "a1"

    # Warnings should have been logged for both invalid items
    assert any(
        "index 1" in r.message and "expected str or dict" in r.message
        for r in caplog.records
    )
    assert any(
        "index 2" in r.message and "expected str or dict" in r.message
        for r in caplog.records
    )


def test_load_catalog_warns_on_dict_with_no_prompt(tmp_path, caplog) -> None:
    """Dict items missing all prompt fields should trigger a warning and be skipped."""
    catalog = tmp_path / "catalog.json"
    catalog.write_text(
        json.dumps({"attacks": [{"id": "a1", "prompt": "valid"}, {"id": "a2"}]}),
        encoding="utf-8",
    )

    with caplog.at_level(logging.WARNING, logger="psg.catalog"):
        attacks = load_catalog(str(catalog))

    # Only the item with a prompt should survive
    assert len(attacks) == 1
    assert attacks[0].id == "a1"

    # A warning should have been logged for the item missing prompt
    assert any(
        "index 1" in r.message and "no prompt text found" in r.message
        for r in caplog.records
    )