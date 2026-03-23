from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .classifier import ClassificationResult, classify_response_v2

LABELS = ["refusal", "success", "partial", "harmful_with_disclaimer"]


def load_golden_set(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def map_result_to_label(result: ClassificationResult) -> str:
    if result.is_refusal and not result.attack_successful:
        return "refusal"
    if result.attack_successful and result.has_disclaimer:
        return "harmful_with_disclaimer"
    if result.attack_successful and not result.has_disclaimer:
        return "success"
    return "partial"


def compute_prf(confusion: dict[str, dict[str, int]]) -> dict[str, dict[str, float | int]]:
    metrics: dict[str, dict[str, float | int]] = {}

    for label in LABELS:
        tp = confusion[label][label]
        fp = sum(confusion[other][label] for other in LABELS if other != label)
        fn = sum(confusion[label][other] for other in LABELS if other != label)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        support = sum(confusion[label].values())
        metrics[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }

    return metrics


def evaluate_golden(golden_path: str | Path) -> dict[str, Any]:
    golden = load_golden_set(golden_path)
    examples = golden.get("examples", [])

    confusion = {expected: {predicted: 0 for predicted in LABELS} for expected in LABELS}
    flagged_correct = 0
    correct = 0
    evaluations: list[dict[str, Any]] = []

    for example in examples:
        response = example["response"]
        expected_label = example["expected_label"]
        expected_flagged = bool(example["expected_flagged"])

        result = classify_response_v2(response)
        predicted_label = map_result_to_label(result)
        predicted_flagged = result.attack_successful

        confusion[expected_label][predicted_label] += 1
        if predicted_label == expected_label:
            correct += 1
        if predicted_flagged == expected_flagged:
            flagged_correct += 1

        evaluations.append(
            {
                "id": example["id"],
                "expected_label": expected_label,
                "predicted_label": predicted_label,
                "expected_flagged": expected_flagged,
                "predicted_flagged": predicted_flagged,
                "is_correct": predicted_label == expected_label,
                "classification": asdict(result),
            }
        )

    total = len(examples)
    accuracy = correct / total if total else 0.0
    flagged_accuracy = flagged_correct / total if total else 0.0

    per_class = compute_prf(confusion)
    macro_f1 = sum(m["f1"] for m in per_class.values()) / len(LABELS) if LABELS else 0.0

    critical_regressions = [
        item
        for item in evaluations
        if item["expected_label"] == "refusal" and item["predicted_label"] == "success"
    ]

    return {
        "golden_version": golden.get("version", "unknown"),
        "golden_path": str(golden_path),
        "total_examples": total,
        "overall_accuracy": accuracy,
        "flagged_accuracy": flagged_accuracy,
        "macro_f1": macro_f1,
        "per_class": per_class,
        "confusion_matrix": confusion,
        "critical_regressions": critical_regressions,
        "evaluations": evaluations,
    }


def build_baseline_snapshot(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "golden_version": report["golden_version"],
        "golden_path": report["golden_path"],
        "total_examples": report["total_examples"],
        "overall_accuracy": report["overall_accuracy"],
        "flagged_accuracy": report["flagged_accuracy"],
        "macro_f1": report["macro_f1"],
        "per_class": report["per_class"],
        "critical_regression_count": len(report["critical_regressions"]),
    }


def format_summary(report: dict[str, Any]) -> str:
    lines = [
        "Classifier Evaluation Summary",
        f"- Golden set: {report['golden_path']} (v{report['golden_version']})",
        f"- Total examples: {report['total_examples']}",
        f"- Overall accuracy: {report['overall_accuracy']:.3f}",
        f"- Flagged accuracy: {report['flagged_accuracy']:.3f}",
        f"- Macro F1: {report['macro_f1']:.3f}",
        "- Per-class metrics:",
    ]

    for label in LABELS:
        m = report["per_class"][label]
        lines.append(
            f"  {label}: precision={m['precision']:.3f} recall={m['recall']:.3f} f1={m['f1']:.3f} support={m['support']}"
        )

    lines.append(f"- Critical regressions (refusal->success): {len(report['critical_regressions'])}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate PSG classifier against a golden dataset")
    parser.add_argument(
        "--golden",
        default="datasets/classifier_golden.json",
        help="Path to golden dataset JSON",
    )
    parser.add_argument(
        "--out",
        help="Optional path to write JSON report",
    )
    parser.add_argument(
        "--baseline-out",
        help="Optional path to write compact baseline metrics JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    report = evaluate_golden(args.golden)

    print(format_summary(report))
    print()
    print(json.dumps(report, indent=2, ensure_ascii=True))

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    if args.baseline_out:
        baseline_path = Path(args.baseline_out)
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline = build_baseline_snapshot(report)
        baseline_path.write_text(json.dumps(baseline, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
