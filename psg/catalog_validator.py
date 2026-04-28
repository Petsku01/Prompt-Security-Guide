from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# ID field aliases (catalog.py _parse_attack_item accepts all of these)
ID_ALIASES = ("id", "attack_id", "name")
# Prompt field aliases (catalog.py _extract_prompt accepts all of these)
PROMPT_ALIASES = ("prompt", "text", "input", "query", "content")
REQUIRED_FIELDS = ID_ALIASES + PROMPT_ALIASES
OPTIONAL_FIELDS = ("technique", "source", "tier")
CATALOG_KEYS = ("attacks", "prompts", "tests", "items")


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _extract_items(data: Any) -> tuple[list[Any] | None, str | None]:
    if isinstance(data, list):
        return data, None

    if isinstance(data, dict):
        for key in CATALOG_KEYS:
            value = data.get(key)
            if isinstance(value, list):
                return value, None
        return (
            None,
            "No supported attack list key found (expected one of: attacks, prompts, tests, items)",
        )

    return None, "Top-level JSON must be an object or array"


def validate_catalog_file(path: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "file": str(path),
            "checked": 0,
            "errors": [
                f"Invalid JSON: {exc.msg} at line {exc.lineno}, column {exc.colno}"
            ],
            "warnings": [],
            "skipped": False,
        }

    items, schema_error = _extract_items(data)
    if items is None:
        return {
            "file": str(path),
            "checked": 0,
            "errors": [],
            "warnings": [f"Skipped (not an attack catalog schema): {schema_error}"],
            "skipped": True,
        }

    seen_ids: set[str] = set()
    checked = 0

    for idx, item in enumerate(items):
        checked += 1

        if not isinstance(item, dict):
            errors.append(
                f"[{idx}] Entry must be an object with required fields: id, prompt"
            )
            continue

        # Check that at least one ID alias is present
        has_id = any(_is_non_empty_string(item.get(key)) for key in ID_ALIASES)
        # Check that at least one prompt alias is present
        has_prompt = any(_is_non_empty_string(item.get(key)) for key in PROMPT_ALIASES)
        missing_required: list[str] = []

        if not has_id:
            missing_required.append(f"one of: {', '.join(ID_ALIASES)}")
        if not has_prompt:
            missing_required.append(f"one of: {', '.join(PROMPT_ALIASES)}")

        if missing_required:
            errors.append(
                f"[{idx}] Missing required field(s): {', '.join(missing_required)}"
            )

        item_id = item.get("id") or item.get("attack_id") or item.get("name")
        if _is_non_empty_string(item_id):
            item_id_str = str(item_id)
            if item_id_str in seen_ids:
                errors.append(f"[{idx}] Duplicate id: {item_id_str}")
            seen_ids.add(item_id_str)

        missing_optional = [
            name for name in OPTIONAL_FIELDS if not _is_non_empty_string(item.get(name))
        ]
        if missing_optional:
            warnings.append(
                f"[{idx}] Missing optional field(s): {', '.join(missing_optional)}"
            )

    return {
        "file": str(path),
        "checked": checked,
        "errors": errors,
        "warnings": warnings,
        "skipped": False,
    }


def _iter_json_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(p for p in path.rglob("*.json") if p.is_file())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate attack catalog JSON files")
    parser.add_argument(
        "--path",
        default="datasets/",
        help="Path to a JSON file or directory of catalog files",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    base_path = Path(args.path)

    if not base_path.exists():
        print(f"Path does not exist: {base_path}", file=sys.stderr)
        return 2

    files = _iter_json_files(base_path)
    if not files:
        print(f"No JSON files found at: {base_path}")
        return 0

    had_errors = False
    total_checked = 0
    total_warnings = 0
    skipped = 0

    for file_path in files:
        report = validate_catalog_file(file_path)
        total_checked += report["checked"]
        total_warnings += len(report["warnings"])
        if report["skipped"]:
            skipped += 1

        print(f"\n== {report['file']} ==")
        print(f"checked: {report['checked']}")

        if report["errors"]:
            had_errors = True
            for line in report["errors"]:
                print(f"ERROR: {line}")

        for line in report["warnings"]:
            print(f"WARN: {line}")

        if not report["errors"] and not report["warnings"]:
            print("OK")

    print("\nSummary")
    print(f"- files: {len(files)}")
    print(f"- records_checked: {total_checked}")
    print(f"- warnings: {total_warnings}")
    print(f"- skipped_non_catalog: {skipped}")
    print(f"- status: {'FAILED' if had_errors else 'PASSED'}")

    return 1 if had_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
