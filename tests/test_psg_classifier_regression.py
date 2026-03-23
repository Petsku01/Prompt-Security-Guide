from __future__ import annotations

from pathlib import Path

from psg.security.evaluate import evaluate_golden


GOLDEN_PATH = Path("datasets/classifier_golden.json")


def test_classifier_golden_macro_f1_threshold() -> None:
    report = evaluate_golden(GOLDEN_PATH)
    assert report["macro_f1"] > 0.85


def test_classifier_no_refusal_to_success_regression() -> None:
    report = evaluate_golden(GOLDEN_PATH)
    assert report["critical_regressions"] == []
