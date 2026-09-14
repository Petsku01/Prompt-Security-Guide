"""Human validation baseline for detector accuracy (#2).

Compares configured detectors against a human-labeled ground truth set of
(prompt, response, label) triples, reporting per-detector precision, recall,
F1 and the confusion matrix. Labels use the same 4-class space as
``evaluate.py``: refusal / success / partial / harmful_with_disclaimer.

Ground truth format (``eval/attack_outcomes_ground_truth.json``):

    {
      "meta": {"version": 1, "labeled_by": "...", "date": "YYYY-MM-DD",
               "labeling_guide": "docs/METHODOLOGY.md#ground-truth-labels"},
      "samples": [
        {"id": "GT-001", "attack_id": "RE-03", "attack_type": "reframing",
         "prompt": "...", "response": "...", "label": "success",
         "notes": "optional rationale"}
      ]
    }

The label is the *human* verdict on the response. This module never labels —
it only measures detectors against labels a human wrote.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ..llm.client import OpenAICompatibleClient
from ..llm.transport import Transport
from .classifier import ClassificationResult
from .detectors import (
    Detector,
    EnsembleDetector,
    KeywordDetector,
    LLMJudgeDetector,
)
from .evaluate import LABELS, map_result_to_label
from .llm_judge import LLMJudge

VALID_LABELS = frozenset(LABELS)


def load_ground_truth(path: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    samples = data.get("samples", [])
    bad = [s.get("id", "?") for s in samples if s.get("label") not in VALID_LABELS]
    if bad:
        raise ValueError(f"invalid labels in ground truth: {bad}")
    return samples


def confusion_for(
    samples: list[dict[str, Any]],
    detector: Detector,
) -> dict[str, dict[str, int]]:
    confusion: dict[str, dict[str, int]] = {
        truth: {pred: 0 for pred in LABELS} for truth in LABELS
    }
    for sample in samples:
        result: ClassificationResult = detector.classify(
            prompt=sample["prompt"], response=sample["response"]
        )
        predicted = map_result_to_label(result)
        confusion[sample["label"]][predicted] += 1
    return confusion


def validate_detectors(
    samples: list[dict[str, Any]],
    detectors: dict[str, Detector],
) -> dict[str, Any]:
    """Run every detector over the ground truth, return per-detector metrics."""
    report: dict[str, Any] = {
        "n_samples": len(samples),
        "label_distribution": {
            label: sum(1 for s in samples if s["label"] == label) for label in LABELS
        },
        "detectors": {},
    }
    for name, detector in detectors.items():
        confusion = confusion_for(samples, detector)
        metrics = _prf(confusion)
        report["detectors"][name] = {
            "confusion": confusion,
            "metrics": metrics,
            "accuracy": _accuracy(confusion),
        }
    return report


def _prf(confusion: dict[str, dict[str, int]]) -> dict[str, dict[str, float | int]]:
    metrics: dict[str, dict[str, float | int]] = {}
    for label in LABELS:
        tp = confusion[label][label]
        fp = sum(confusion[other][label] for other in LABELS if other != label)
        fn = sum(confusion[label][other] for other in LABELS if other != label)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (
            (2 * precision * recall / (precision + recall))
            if (precision + recall)
            else 0.0
        )
        support = sum(confusion[label].values())
        metrics[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
        }
    return metrics


def _accuracy(confusion: dict[str, dict[str, int]]) -> float:
    correct = sum(confusion[label][label] for label in LABELS)
    total = sum(confusion[label][pred] for label in LABELS for pred in LABELS)
    return correct / total if total else 0.0


def build_default_detectors(
    judge_client: OpenAICompatibleClient | None = None,
    judge_model: str = "llama3:8b",
) -> dict[str, Detector]:
    keyword = KeywordDetector()
    detectors: dict[str, Detector] = {"keyword": keyword}
    if judge_client is not None:
        llm_judge = LLMJudgeDetector(
            judge=LLMJudge(client=judge_client, model=judge_model)
        )
        detectors["llm_judge"] = llm_judge
        detectors["ensemble"] = EnsembleDetector(keyword=keyword, llm_judge=llm_judge)
    return detectors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="psg validate-detectors",
        description="Measure detector precision/recall against human labels (#2).",
    )
    parser.add_argument(
        "--ground-truth",
        default="eval/attack_outcomes_ground_truth.json",
        help="Path to the human-labeled ground truth JSON",
    )
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    parser.add_argument(
        "--with-judge",
        action="store_true",
        help="Also run LLM judge + ensemble (needs an OpenAI-compatible endpoint)",
    )
    parser.add_argument("--judge-url", default=None, help="Judge endpoint URL")
    parser.add_argument("--judge-model", default="llama3:8b")
    parser.add_argument("--judge-api-key", default=None)
    args = parser.parse_args(argv)

    samples = load_ground_truth(args.ground_truth)
    judge_client = None
    if args.with_judge:
        judge_url = args.judge_url or "http://localhost:11434/v1"
        transport = Transport(timeout_seconds=120.0, max_retries=2)
        judge_client = OpenAICompatibleClient(
            judge_url, transport, api_key=args.judge_api_key
        )
    report = validate_detectors(
        samples,
        build_default_detectors(
            judge_client=judge_client, judge_model=args.judge_model
        ),
    )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_report(report)
    return 0


def _print_report(report: dict[str, Any]) -> None:
    print(f"samples: {report['n_samples']}")
    print(
        "labels: "
        + ", ".join(f"{k}={v}" for k, v in report["label_distribution"].items())
    )
    for name, data in report["detectors"].items():
        print(f"\n{name} (accuracy {data['accuracy']:.3f}):")
        for label, m in data["metrics"].items():
            print(
                f"  {label:24s} P={m['precision']:.3f} R={m['recall']:.3f} "
                f"F1={m['f1']:.3f} n={m['support']}"
            )


if __name__ == "__main__":
    raise SystemExit(main())
