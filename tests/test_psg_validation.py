"""Tests for psg/security/validation.py — human validation baseline (#2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from psg.security.classifier import ClassificationResult
from psg.security.detectors import KeywordDetector
from psg.security.validation import (
    VALID_LABELS,
    build_default_detectors,
    confusion_for,
    load_ground_truth,
    validate_detectors,
)

GT = Path(__file__).resolve().parents[1] / "eval" / "attack_outcomes_ground_truth.json"


def test_ground_truth_loads_and_labels_are_valid() -> None:
    samples = load_ground_truth(GT)
    assert len(samples) >= 20, "ground truth has shrunk below the useful minimum"
    for s in samples:
        assert s["label"] in VALID_LABELS
        assert s["prompt"] and s["response"]


def test_ground_truth_ids_unique() -> None:
    samples = load_ground_truth(GT)
    ids = [s["id"] for s in samples]
    assert len(ids) == len(set(ids)), f"duplicate ids: {ids}"


def test_confusion_counts_add_up() -> None:
    samples = load_ground_truth(GT)
    confusion = confusion_for(samples, KeywordDetector())
    total = sum(confusion[t][p] for t in confusion for p in confusion[t])
    assert total == len(samples)


def test_perfect_detector_gets_perfect_metrics() -> None:
    samples_cache = load_ground_truth(GT)
    label_by_response = {s["response"]: s["label"] for s in samples_cache}

    class Oracle:
        def classify(self, prompt: str, response: str):  # noqa: ANN001
            label = label_by_response[response]
            return ClassificationResult(
                is_refusal=label == "refusal",
                is_harmful=label in ("success", "harmful_with_disclaimer"),
                attack_successful=label in ("success", "harmful_with_disclaimer"),
                harm_score=0.9
                if label in ("success", "harmful_with_disclaimer")
                else 0.1,
                refusal_confidence=0.9 if label == "refusal" else 0.0,
                harmful_labels=[],
                compliance_detected=False,
                has_disclaimer=label == "harmful_with_disclaimer",
                raw_text_length=len(response),
            )

    report = validate_detectors(samples_cache, {"oracle": Oracle()})
    metrics = report["detectors"]["oracle"]["metrics"]
    for label, m in metrics.items():
        if m["support"] > 0:
            assert m["precision"] == pytest.approx(1.0)
            assert m["recall"] == pytest.approx(1.0)
    assert report["detectors"]["oracle"]["accuracy"] == pytest.approx(1.0)


def test_validation_report_is_json_serializable() -> None:
    samples = load_ground_truth(GT)
    report = validate_detectors(samples, build_default_detectors(judge_client=None))
    text = json.dumps(report)  # must not raise
    assert '"n_samples"' in text


def test_invalid_label_rejected() -> None:

    bad = {
        "samples": [
            {"id": "X", "prompt": "p", "response": "r", "label": "nonsense"},
        ]
    }
    with pytest.raises(ValueError, match="invalid labels"):
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(Path, "read_text", lambda *a, **k: json.dumps(bad))
            load_ground_truth("dummy.json")
