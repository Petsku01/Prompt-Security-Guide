"""Tests for psg.eval module."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from psg.eval import EvalMetrics, evaluate, load_golden, main


def test_eval_metrics_perfect_score() -> None:
    metrics = EvalMetrics(
        true_positives=5, true_negatives=5, false_positives=0, false_negatives=0
    )
    assert metrics.total == 10
    assert metrics.accuracy == 1.0
    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.f1 == 1.0


def test_eval_metrics_with_errors() -> None:
    metrics = EvalMetrics(
        true_positives=3, true_negatives=4, false_positives=1, false_negatives=2
    )
    assert metrics.total == 10
    assert metrics.accuracy == 0.7
    assert metrics.precision == 0.75  # 3 / (3 + 1)
    assert metrics.recall == 0.6  # 3 / (3 + 2)
    # F1 = 2 * (0.75 * 0.6) / (0.75 + 0.6) = 2 * 0.45 / 1.35 = 0.666...
    assert abs(metrics.f1 - 0.6666666666666666) < 0.001


def test_eval_metrics_zero_division() -> None:
    metrics = EvalMetrics(
        true_positives=0, true_negatives=0, false_positives=0, false_negatives=0
    )
    assert metrics.accuracy == 0.0
    assert metrics.precision == 0.0
    assert metrics.recall == 0.0
    assert metrics.f1 == 0.0


def test_load_golden_valid() -> None:
    data = [
        {"text": "test1", "expected_harmful": True},
        {"text": "test2", "expected_harmful": False},
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        golden = load_golden(Path(f.name))

    assert len(golden) == 2
    assert golden[0]["text"] == "test1"


def test_load_golden_missing_text() -> None:
    data = [{"expected_harmful": True}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        with pytest.raises(ValueError, match="missing 'text'"):
            load_golden(Path(f.name))


def test_load_golden_missing_expected() -> None:
    data = [{"text": "test"}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        with pytest.raises(ValueError, match="missing 'expected_harmful'"):
            load_golden(Path(f.name))


def test_load_golden_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        load_golden(Path("/nonexistent/file.json"))


def test_evaluate_calls_classifier(monkeypatch: pytest.MonkeyPatch) -> None:
    from psg.security.classifier import ClassificationResult

    def _classify(text: str) -> ClassificationResult:
        # Return harmful if text contains "harmful"
        is_harmful = "harmful" in text.lower()
        return ClassificationResult(
            is_refusal=False,
            is_harmful=is_harmful,
            attack_successful=is_harmful,
            harm_score=0.9 if is_harmful else 0.1,
            refusal_confidence=0.0,
            harmful_labels=["test"] if is_harmful else [],
            compliance_detected=False,
            has_disclaimer=False,
            raw_text_length=len(text),
        )

    monkeypatch.setattr("psg.eval.classify_response_v2", _classify)

    golden = [
        {"text": "harmless text", "expected_harmful": False},
        {"text": "harmful content", "expected_harmful": True},
        {"text": "also harmless", "expected_harmful": False},
    ]

    metrics = evaluate(golden, threshold=0.5)

    assert metrics.true_positives == 1
    assert metrics.true_negatives == 2
    assert metrics.false_positives == 0
    assert metrics.false_negatives == 0


def test_main_exit_code_success() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(
            [
                {"text": "I cannot help", "expected_harmful": False},
            ],
            f,
        )
        f.flush()
        # Should pass because harmless text scores below threshold
        exit_code = main(["--golden", f.name, "--fail-on-macro-f1-below", "0.0"])

    assert exit_code == 0


def test_main_exit_code_failure() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        # Create a case that will fail: mark harmless text as harmful
        json.dump(
            [
                {"text": "Hello world", "expected_harmful": True},
            ],
            f,
        )
        f.flush()
        # Should fail because classifier won't flag "Hello world"
        exit_code = main(["--golden", f.name, "--fail-on-macro-f1-below", "0.99"])

    assert exit_code == 1


def test_main_json_output(capsys: pytest.CaptureFixture[str]) -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(
            [
                {"text": "I cannot help with that", "expected_harmful": False},
            ],
            f,
        )
        f.flush()
        main(["--golden", f.name, "--json"])

    captured = capsys.readouterr()
    output = json.loads(captured.out)

    assert "f1" in output
    assert "accuracy" in output
    assert "total" in output
