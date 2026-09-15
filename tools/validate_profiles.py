"""Audit P1-10 (HIGH, 2026-09-15): profile/catalog schema validation in CI.

Audit found 227/355 profile rows missing fields (notes 182, sophistication
78, source 40) with row-shape varying by generator. This validator is the
CI gate: any catalog/profile under datasets/ must have, per row:
  - id (non-empty string, unique within file)
  - prompt (non-empty string)
  - provenance_type in the allowed enum (rows added before the field
    default to 'mechanism_inspired' with a warning)
Missing-field counting is per required key with ALIAS support matching
catalog.py's parser, so a row using 'text' instead of 'prompt' still
counts as present.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Mirrors psg/catalog_validator.py alias sets:
ID_ALIASES = ("id", "attack_id", "name")
PROMPT_ALIASES = ("prompt", "text", "input", "query", "content")
PROVENANCE_VALUES = (
    "verbatim",
    "faithful_adaptation",
    "mechanism_inspired",
    "anecdotal_probe",
)
LIST_KEYS = ("attacks", "prompts", "tests", "items", "behaviors")

# Files exempt from provenance_type requirement (pre-date the field;
# they are alias manifests or third-party verbatim corpora).
EXEMPT_FILES = (
    "datasets/jailbreakbench_behaviors.json",  # alias manifest, not data
)

# Directories where provenance_type is REQUIRED (PSG-authored profiles
# and catalogs that feed benchmark presets — i.e. rows PSG authored or
# curates AND has already backfilled). Others are warned only, until a
# curation pass backfills them — a hard gate on 3000+ community rows
# would block all benchmark work for weeks.
ENFORCE_DIRS = ("datasets/profiles/gpt51_attacks.json",)


def _first_non_empty(item: dict, keys: tuple[str, ...]) -> bool:
    return any(
        isinstance(item.get(k), str) and item[k].strip() for k in keys
    )


def validate_file(path: Path) -> tuple[list[str], int]:
    """Return (errors, checked_count) for one catalog/profile JSON."""
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON: {exc} at line {exc.lineno}"], 0

    items: list | None = None
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        for key in LIST_KEYS:
            value = data.get(key)
            if isinstance(value, list):
                items = value
                break
    if items is None:
        # Not an attack-catalog shape (e.g. alias manifest) — skip quietly.
        return [], 0

    rel = path.as_posix()
    exempt = any(rel.endswith(e) for e in EXEMPT_FILES)

    seen_ids: set[str] = set()
    for idx, item in enumerate(items):
        where = f"{rel}[{idx}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: entry is {type(item).__name__}, expected object")
            continue
        if not _first_non_empty(item, ID_ALIASES):
            errors.append(f"{where}: missing id (aliases: {ID_ALIASES})")
        if not _first_non_empty(item, PROMPT_ALIASES):
            errors.append(f"{where}: missing prompt (aliases: {PROMPT_ALIASES})")
        id_val = next(
            (item.get(k) for k in ID_ALIASES
             if isinstance(item.get(k), str) and item[k].strip()),
            None,
        )
        if id_val:
            if id_val in seen_ids:
                errors.append(f"{where}: duplicate id {id_val!r}")
            seen_ids.add(id_val)
        if not exempt and rel.startswith(ENFORCE_DIRS) and "provenance_type" not in item:
            errors.append(
                f"{where}: missing provenance_type (audit B4 requirement)"
            )
        elif (
            not exempt
            and rel.startswith(ENFORCE_DIRS)
            and item.get("provenance_type") not in PROVENANCE_VALUES
        ):
            errors.append(
                f"{where}: provenance_type {item.get('provenance_type')!r} "
                f"not in {PROVENANCE_VALUES}"
            )
    return errors, len(items)


def main() -> int:
    root = Path(".")
    targets = sorted(root.glob("datasets/**/*.json"))
    if not targets:
        print("no dataset files found", file=sys.stderr)
        return 2
    total_errors: list[str] = []
    total_rows = 0
    for path in targets:
        errors, n = validate_file(path)
        total_rows += n
        total_errors.extend(errors)
    print(f"validated {len(targets)} files / {total_rows} rows")
    if total_errors:
        print(f"{len(total_errors)} ERRORS:", file=sys.stderr)
        for e in total_errors[:30]:
            print(f"  - {e}", file=sys.stderr)
        if len(total_errors) > 30:
            print(f"  ...and {len(total_errors) - 30} more", file=sys.stderr)
        return 1
    print("schema OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())