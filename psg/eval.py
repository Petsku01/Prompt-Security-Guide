"""Classifier evaluation with golden dataset comparison.

Usage:
    psg eval --golden datasets/classifier_golden.json --fail-on-macro-f1-below 0.85

Golden dataset format:
    [
        {"text": "I cannot help with that", "expected_harmful": false},
        {"text": "Here's how to build malware...", "expected_harmful": true},
        ...
    ]

Exit codes:
    0 - Success, F1 score meets threshold
    1 - F1 score below threshold
    2 - Configuration/input error
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from .security.classifier import classify_response_v2


@dataclass
class EvalMetrics:
    """Evaluation metrics for binary classification."""
    
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int
    
    @property
    def total(self) -> int:
        return self.true_positives + self.true_negatives + self.false_positives + self.false_negatives
    
    @property
    def accuracy(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.true_positives + self.true_negatives) / self.total
    
    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        if denom == 0:
            return 0.0
        return self.true_positives / denom
    
    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        if denom == 0:
            return 0.0
        return self.true_positives / denom
    
    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        if p + r == 0:
            return 0.0
        return 2 * (p * r) / (p + r)


def load_golden(path: Path) -> list[dict]:
    """Load golden dataset from JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Golden dataset not found: {path}")
    
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        raise ValueError("Golden dataset must be a JSON array")
    
    for i, item in enumerate(data):
        if "text" not in item:
            raise ValueError(f"Item {i} missing 'text' field")
        if "expected_harmful" not in item:
            raise ValueError(f"Item {i} missing 'expected_harmful' field")
    
    return data


def evaluate(golden: list[dict], threshold: float = 0.5) -> EvalMetrics:
    """Evaluate classifier against golden dataset."""
    tp = tn = fp = fn = 0
    
    for item in golden:
        text = item["text"]
        expected = item["expected_harmful"]
        
        result = classify_response_v2(text)
        predicted = result.harm_score >= threshold
        
        if expected and predicted:
            tp += 1
        elif not expected and not predicted:
            tn += 1
        elif not expected and predicted:
            fp += 1
        else:  # expected and not predicted
            fn += 1
    
    return EvalMetrics(
        true_positives=tp,
        true_negatives=tn,
        false_positives=fp,
        false_negatives=fn,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate PSG classifier against golden dataset"
    )
    parser.add_argument(
        "--golden",
        required=True,
        help="Path to golden dataset JSON file",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Harm score threshold for classification (default: 0.5)",
    )
    parser.add_argument(
        "--fail-on-macro-f1-below",
        type=float,
        default=None,
        metavar="SCORE",
        help="Exit with code 1 if F1 score is below this value",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    
    try:
        golden = load_golden(Path(args.golden))
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error loading golden dataset: {exc}", file=sys.stderr)
        return 2
    
    if not golden:
        print("Golden dataset is empty", file=sys.stderr)
        return 2
    
    metrics = evaluate(golden, threshold=args.threshold)
    
    if args.json:
        output = {
            "total": metrics.total,
            "accuracy": round(metrics.accuracy, 4),
            "precision": round(metrics.precision, 4),
            "recall": round(metrics.recall, 4),
            "f1": round(metrics.f1, 4),
            "true_positives": metrics.true_positives,
            "true_negatives": metrics.true_negatives,
            "false_positives": metrics.false_positives,
            "false_negatives": metrics.false_negatives,
            "threshold": args.threshold,
        }
        if args.fail_on_macro_f1_below is not None:
            output["f1_threshold"] = args.fail_on_macro_f1_below
            output["passed"] = metrics.f1 >= args.fail_on_macro_f1_below
        print(json.dumps(output, indent=2))
    else:
        print(f"Evaluation Results (n={metrics.total}, threshold={args.threshold})")
        print(f"  Accuracy:  {metrics.accuracy:.2%}")
        print(f"  Precision: {metrics.precision:.2%}")
        print(f"  Recall:    {metrics.recall:.2%}")
        print(f"  F1 Score:  {metrics.f1:.2%}")
        print()
        print(f"  TP={metrics.true_positives} TN={metrics.true_negatives} FP={metrics.false_positives} FN={metrics.false_negatives}")
    
    if args.fail_on_macro_f1_below is not None:
        if metrics.f1 < args.fail_on_macro_f1_below:
            if not args.json:
                print(
                    f"\n❌ FAILED: F1 score {metrics.f1:.2%} is below threshold {args.fail_on_macro_f1_below:.2%}",
                    file=sys.stderr,
                )
            return 1
        else:
            if not args.json:
                print(f"\n✅ PASSED: F1 score {metrics.f1:.2%} meets threshold {args.fail_on_macro_f1_below:.2%}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
