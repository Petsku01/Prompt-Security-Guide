from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _load_report(path: str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"report must be an object: {path}")
    return data


def compare_reports(left: dict[str, Any], right: dict[str, Any]) -> dict[str, str | bool]:
    left_meta = left.get("run_metadata", {}) if isinstance(left, dict) else {}
    right_meta = right.get("run_metadata", {}) if isinstance(right, dict) else {}
    left_set = left_meta.get("attack_set")
    right_set = right_meta.get("attack_set")
    left_ids = left_meta.get("attack_ids")
    right_ids = right_meta.get("attack_ids")

    if left_set != right_set:
        return {
            "aligned": False,
            "reason": "attack_set_mismatch",
            "details": f"{left_set!r} vs {right_set!r}",
        }
    if not isinstance(left_ids, list) or not isinstance(right_ids, list):
        return {
            "aligned": False,
            "reason": "missing_attack_ids",
            "details": "run_metadata.attack_ids missing from one or both reports",
        }
    if left_ids != right_ids:
        return {
            "aligned": False,
            "reason": "attack_id_mismatch",
            "details": f"{len(left_ids)} ids vs {len(right_ids)} ids (order/content differ)",
        }
    return {
        "aligned": True,
        "reason": "aligned",
        "details": f"{len(left_ids)} aligned attacks",
    }


def compare_report_files(left_path: str, right_path: str) -> dict[str, str | bool]:
    return compare_reports(_load_report(left_path), _load_report(right_path))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare two PSG JSON reports")
    parser.add_argument("--left", required=True, help="Baseline report JSON")
    parser.add_argument("--right", required=True, help="Candidate report JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        comparison = compare_report_files(args.left, args.right)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Comparison failed: {exc}", file=sys.stderr)
        return 2

    status = "ALIGNED" if comparison["aligned"] else "MISALIGNED"
    print(f"{status}: {comparison['reason']} - {comparison['details']}")
    if comparison["aligned"]:
        return 0

    print(
        "Warning: comparing runs with different attack sets is apples-to-oranges.",
        file=sys.stderr,
    )
    return 1
