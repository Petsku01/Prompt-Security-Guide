from __future__ import annotations

import json
from pathlib import Path

import pytest

from psg.security.classifier import ClassificationResult
from psg.security.evaluate import (
    LABELS,
    build_baseline_snapshot,
    compute_prf,
    evaluate_golden,
    format_summary,
    load_golden_set,
    map_result_to_label,
)


@pytest.fixture
def golden_payload() -> dict[str, object]:
    return {
        "version": "test-v1",
        "examples": [
            {
                "id": "ex-1",
                "response": "resp_refusal",
                "expected_label": "refusal",
                "expected_flagged": False,
            },
            {
                "id": "ex-2",
                "response": "resp_success",
                "expected_label": "success",
                "expected_flagged": True,
            },
            {
                "id": "ex-3",
                "response": "resp_partial",
                "expected_label": "partial",
                "expected_flagged": False,
            },
            {
                "id": "ex-4",
                "response": "resp_disclaimer",
                "expected_label": "harmful_with_disclaimer",
                "expected_flagged": True,
            },
        ],
    }


@pytest.fixture
def golden_file(tmp_path: Path, golden_payload: dict[str, object]) -> Path:
    path = tmp_path / "golden.json"
    path.write_text(json.dumps(golden_payload), encoding="utf-8")
    return path


@pytest.fixture
def mocked_classifications() -> dict[str, ClassificationResult]:
    return {
        "resp_refusal": ClassificationResult(
            is_refusal=True,
            is_harmful=False,
            attack_successful=False,
            harm_score=0.0,
            refusal_confidence=0.9,
            harmful_labels=[],
            compliance_detected=False,
            has_disclaimer=False,
            raw_text_length=12,
        ),
        "resp_success": ClassificationResult(
            is_refusal=False,
            is_harmful=True,
            attack_successful=True,
            harm_score=0.9,
            refusal_confidence=0.0,
            harmful_labels=["malware_code"],
            compliance_detected=True,
            has_disclaimer=False,
            raw_text_length=12,
        ),
        "resp_partial": ClassificationResult(
            is_refusal=False,
            is_harmful=False,
            attack_successful=False,
            harm_score=0.2,
            refusal_confidence=0.0,
            harmful_labels=[],
            compliance_detected=False,
            has_disclaimer=False,
            raw_text_length=12,
        ),
        "resp_disclaimer": ClassificationResult(
            is_refusal=False,
            is_harmful=True,
            attack_successful=True,
            harm_score=0.7,
            refusal_confidence=0.0,
            harmful_labels=["exploit_terms"],
            compliance_detected=True,
            has_disclaimer=True,
            raw_text_length=15,
        ),
    }


def test_load_golden_set_loads_json(golden_file: Path, golden_payload: dict[str, object]) -> None:
    assert load_golden_set(golden_file) == golden_payload


@pytest.mark.parametrize(
    ("result", "expected_label"),
    [
        (
            ClassificationResult(
                is_refusal=True,
                is_harmful=False,
                attack_successful=False,
                harm_score=0.0,
                refusal_confidence=1.0,
                harmful_labels=[],
                compliance_detected=False,
                has_disclaimer=False,
                raw_text_length=10,
            ),
            "refusal",
        ),
        (
            ClassificationResult(
                is_refusal=False,
                is_harmful=True,
                attack_successful=True,
                harm_score=1.0,
                refusal_confidence=0.0,
                harmful_labels=["x"],
                compliance_detected=True,
                has_disclaimer=True,
                raw_text_length=10,
            ),
            "harmful_with_disclaimer",
        ),
        (
            ClassificationResult(
                is_refusal=False,
                is_harmful=True,
                attack_successful=True,
                harm_score=1.0,
                refusal_confidence=0.0,
                harmful_labels=["x"],
                compliance_detected=True,
                has_disclaimer=False,
                raw_text_length=10,
            ),
            "success",
        ),
        (
            ClassificationResult(
                is_refusal=False,
                is_harmful=False,
                attack_successful=False,
                harm_score=0.0,
                refusal_confidence=0.0,
                harmful_labels=[],
                compliance_detected=False,
                has_disclaimer=False,
                raw_text_length=10,
            ),
            "partial",
        ),
    ],
)
def test_map_result_to_label_all_mappings(result: ClassificationResult, expected_label: str) -> None:
    assert map_result_to_label(result) == expected_label


def test_compute_prf_returns_expected_values() -> None:
    confusion = {
        "refusal": {"refusal": 3, "success": 1, "partial": 0, "harmful_with_disclaimer": 0},
        "success": {"refusal": 0, "success": 2, "partial": 1, "harmful_with_disclaimer": 0},
        "partial": {"refusal": 1, "success": 0, "partial": 2, "harmful_with_disclaimer": 0},
        "harmful_with_disclaimer": {
            "refusal": 0,
            "success": 0,
            "partial": 0,
            "harmful_with_disclaimer": 1,
        },
    }

    metrics = compute_prf(confusion)

    assert metrics["refusal"]["tp"] == 3
    assert metrics["refusal"]["fp"] == 1
    assert metrics["refusal"]["fn"] == 1
    assert metrics["refusal"]["support"] == 4
    assert metrics["refusal"]["precision"] == pytest.approx(0.75)
    assert metrics["refusal"]["recall"] == pytest.approx(0.75)
    assert metrics["refusal"]["f1"] == pytest.approx(0.75)


def test_evaluate_golden_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    golden_file: Path,
    mocked_classifications: dict[str, ClassificationResult],
) -> None:
    def _mock_classify(response: str) -> ClassificationResult:
        return mocked_classifications[response]

    monkeypatch.setattr("psg.security.evaluate.classify_response_v2", _mock_classify)

    report = evaluate_golden(golden_file)

    assert report["golden_version"] == "test-v1"
    assert report["total_examples"] == 4
    assert report["overall_accuracy"] == 1.0
    assert report["flagged_accuracy"] == 1.0
    assert report["macro_f1"] == pytest.approx(1.0)
    assert report["critical_regressions"] == []
    assert report["confusion_matrix"]["success"]["success"] == 1
    assert len(report["evaluations"]) == 4


def test_build_baseline_snapshot(golden_file: Path) -> None:
    report = {
        "golden_version": "v0",
        "golden_path": str(golden_file),
        "total_examples": 12,
        "overall_accuracy": 0.75,
        "flagged_accuracy": 0.8,
        "macro_f1": 0.7,
        "per_class": {label: {"f1": 0.0} for label in LABELS},
        "critical_regressions": [{"id": "x"}, {"id": "y"}],
    }

    baseline = build_baseline_snapshot(report)

    assert baseline == {
        "golden_version": "v0",
        "golden_path": str(golden_file),
        "total_examples": 12,
        "overall_accuracy": 0.75,
        "flagged_accuracy": 0.8,
        "macro_f1": 0.7,
        "per_class": {label: {"f1": 0.0} for label in LABELS},
        "critical_regression_count": 2,
    }


def test_format_summary_contains_expected_sections() -> None:
    report = {
        "golden_path": "datasets/classifier_golden.json",
        "golden_version": "v2",
        "total_examples": 4,
        "overall_accuracy": 0.5,
        "flagged_accuracy": 0.75,
        "macro_f1": 0.66,
        "per_class": {
            label: {"precision": 0.5, "recall": 0.5, "f1": 0.5, "support": 1}
            for label in LABELS
        },
        "critical_regressions": [{"id": "reg-1"}],
    }

    summary = format_summary(report)

    assert "Classifier Evaluation Summary" in summary
    assert "- Golden set: datasets/classifier_golden.json (vv2)" in summary
    assert "- Overall accuracy: 0.500" in summary
    assert "- Per-class metrics:" in summary
    for label in LABELS:
        assert f"  {label}: precision=0.500 recall=0.500 f1=0.500 support=1" in summary
    assert "- Critical regressions (refusal->success): 1" in summary
