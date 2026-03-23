from __future__ import annotations

import json

from psg.catalog_validator import validate_catalog_file


def test_validate_catalog_file_detects_duplicate_id_and_missing_required(tmp_path) -> None:
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
    assert any("Missing required field(s): prompt" in e for e in report["errors"])


def test_validate_catalog_file_warnings_for_optional_fields(tmp_path) -> None:
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps({"attacks": [{"id": "a-1", "prompt": "hello"}]}), encoding="utf-8")

    report = validate_catalog_file(catalog_path)

    assert report["errors"] == []
    assert any("Missing optional field(s): technique, source, tier" in w for w in report["warnings"])


def test_validate_catalog_file_skips_non_catalog_schema(tmp_path) -> None:
    payload = tmp_path / "golden_like.json"
    payload.write_text(json.dumps({"examples": [{"id": "x"}]}), encoding="utf-8")

    report = validate_catalog_file(payload)

    assert report["skipped"] is True
    assert report["errors"] == []
    assert report["checked"] == 0
