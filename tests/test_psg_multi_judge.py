"""Tests for MultiJudgeDetector (P1 kohda 3: N-judge voting ensemble)."""

import pytest

from psg.cli import build_parser
from psg.config import ConfigError, validate_config
from psg.models import AppConfig
from psg.security.detectors import build_detector
from psg.security.llm_judge import LLMJudgeResult
from psg.security.multi_judge import MultiJudgeDetector


class _StubJudge:
    def __init__(self, result: LLMJudgeResult):
        self._result = result
        self.calls = 0

    def classify(self, prompt: str, response: str) -> LLMJudgeResult:
        del prompt, response
        self.calls += 1
        return self._result


def _res(verdict: str) -> LLMJudgeResult:
    return LLMJudgeResult(
        verdict=verdict,  # type: ignore[arg-type]
        is_harmful=verdict == "HARMFUL",
        confidence=0.95 if verdict != "UNKNOWN" else 0.0,
        reasoning=None if verdict != "UNKNOWN" else "err",
    )


def _detector(*verdicts: str) -> MultiJudgeDetector:
    """Type-ignore: stubs replace LLMJudge (structural duck typing)."""
    return MultiJudgeDetector(
        judges=[(f"model{i}", _StubJudge(_res(v))) for i, (v) in enumerate(verdicts)]  # type: ignore[arg-type]
    )


def test_any_harmful_wins_fail_closed() -> None:
    """One judge HARMFUL, one SAFE -> HARMFUL (defense-first quorum)."""
    r = _detector("HARMFUL", "SAFE").classify("p", "resp")
    assert r.attack_successful
    assert r.is_harmful
    assert "multi_judge_harmful:model0" in r.harmful_labels


def test_all_safe_is_safe() -> None:
    r = _detector("SAFE", "SAFE").classify("p", "resp")
    assert not r.attack_successful
    assert not r.is_harmful
    assert r.harm_score == 0.0


def test_all_unknown_is_not_attack() -> None:
    """Total judge failure must not be an attack signal."""
    r = _detector("UNKNOWN", "UNKNOWN").classify("p", "resp")
    assert not r.attack_successful
    assert "judge_error" in r.harmful_labels
    assert r.harm_score == 0.1


def test_disagreement_labels_show_per_judge() -> None:
    r = _detector("SAFE", "HARMFUL").classify("p", "resp")
    assert "multi_judge_harmful:model1" in r.harmful_labels
    assert "multi_judge_harmful:model0" not in r.harmful_labels


def test_three_judges_majority_not_required() -> None:
    """2 SAFE + 1 HARMFUL still fails closed."""
    r = _detector("SAFE", "SAFE", "HARMFUL").classify("p", "resp")
    assert r.attack_successful


# --- config validation -------------------------------------------------------


def _cfg(**kw) -> AppConfig:
    """AppConfig with the fields multi-judge validation touches."""
    cfg = AppConfig(
        model="test-model",
        catalog_path="datasets/tiny_test.json",
        base_url="https://8.8.8.8/v1",
        judge_url="https://8.8.8.8/v1",
        detector="multi-judge",
        judge_models="llama3:8b,qwen2.5:7b",
    )
    for k, v in kw.items():
        setattr(cfg, k, v)
    return cfg


def test_config_accepts_multi_judge() -> None:
    validate_config(_cfg())  # no raise


def test_config_rejects_single_judge_model() -> None:
    with pytest.raises(ConfigError, match="at least 2"):
        validate_config(_cfg(judge_models="llama3:8b"))


def test_config_rejects_empty_judge_models() -> None:
    with pytest.raises(ConfigError):
        validate_config(_cfg(judge_models=None))


# --- CLI wiring --------------------------------------------------------------


def test_cli_parses_judge_models() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "--base-url",
            "https://8.8.8.8/v1",
            "--model",
            "m",
            "--catalog",
            "datasets/tiny_test.json",
            "--detector",
            "multi-judge",
            "--judge-models",
            "llama3:8b,qwen2.5:7b",
        ]
    )
    assert args.judge_models == "llama3:8b,qwen2.5:7b"


def test_build_detector_multi_judge() -> None:
    cfg = _cfg()
    detector = build_detector(cfg)
    assert isinstance(detector, MultiJudgeDetector)
    assert len(detector.judges) == 2
