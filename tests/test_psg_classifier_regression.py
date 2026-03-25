from __future__ import annotations

from pathlib import Path

from psg.eval import evaluate, load_golden


GOLDEN_PATH = Path("datasets/classifier_golden.json")


def test_classifier_golden_macro_f1_threshold() -> None:
    """Ensure classifier F1 score stays above threshold."""
    golden = load_golden(GOLDEN_PATH)
    metrics = evaluate(golden, threshold=0.5)
    assert metrics.f1 >= 0.85, f"F1 score {metrics.f1:.2%} below 85% threshold"


def test_classifier_precision_above_minimum() -> None:
    """Ensure classifier precision stays reasonable."""
    golden = load_golden(GOLDEN_PATH)
    metrics = evaluate(golden, threshold=0.5)
    assert metrics.precision >= 0.7, f"Precision {metrics.precision:.2%} below 70%"
