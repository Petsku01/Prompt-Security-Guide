from __future__ import annotations

from psg.cli import build_parser
from psg.security.classifier import ClassificationResult
from psg.security.detectors import EnsembleDetector, LLMJudgeDetector
from psg.security.llm_judge import (
    LLMJudge,
    LLMJudgeResult,
    format_judge_prompt,
    parse_judge_output,
)


class _FailingClient:
    def chat(self, **_kwargs):
        raise TimeoutError("timeout")


class _Response:
    def __init__(self, content: str):
        self.content = content


class _ReturningClient:
    def __init__(self, content: str):
        self._content = content

    def chat(self, **_kwargs):
        return _Response(self._content)


class _StubJudge:
    def __init__(self, result: LLMJudgeResult):
        self._result = result
        self.calls = 0

    def classify(self, prompt: str, response: str) -> LLMJudgeResult:
        del prompt, response
        self.calls += 1
        return self._result


class _StubKeywordDetector:
    def __init__(self, result: ClassificationResult):
        self._result = result

    def classify(self, prompt: str, response: str) -> ClassificationResult:
        del prompt, response
        return self._result


def test_judge_prompt_formatting() -> None:
    prompt = format_judge_prompt(
        prompt="How to hack?", response="I cannot help with that."
    )
    # Random delimiter means tags are like <request_HEX>, <response_HEX>
    assert "<request_" in prompt
    assert "</request_" in prompt
    assert "<response_" in prompt
    assert "</response_" in prompt
    assert "How to hack?" in prompt
    assert "I cannot help with that." in prompt
    assert prompt.endswith("Classification:")
    # Verify delimiter is consistent within one call
    import re

    delimiters = re.findall(r"<request_([a-f0-9]+)>", prompt)
    assert len(delimiters) == 1, "Should have exactly one delimiter per call"
    delim = delimiters[0]
    assert f"</request_{delim}>" in prompt
    assert f"<response_{delim}>" in prompt
    assert f"</response_{delim}>" in prompt


def test_judge_response_parsing_safe_and_harmful() -> None:
    safe_verdict, safe_confidence, _ = parse_judge_output("SAFE")
    harm_verdict, harm_confidence, _ = parse_judge_output("HARMFUL")

    assert safe_verdict == "SAFE"
    assert safe_confidence > 0.0
    assert harm_verdict == "HARMFUL"
    assert harm_confidence > 0.0


def test_judge_fallback_on_timeout() -> None:
    judge = LLMJudge(client=_FailingClient(), model="llama3:8b")
    result = judge.classify(prompt="p", response="r")

    assert result.verdict == "UNKNOWN"
    assert result.is_harmful is False
    assert result.confidence == 0.0
    assert result.reasoning is not None
    assert "judge-request-failed" in result.reasoning


def test_parse_judge_output_unknown_for_maybe() -> None:
    verdict, confidence, reason = parse_judge_output("MAYBE")
    assert verdict == "UNKNOWN"
    assert confidence == 0.0
    assert reason is not None


def test_parse_judge_output_not_harmful_is_unknown() -> None:
    verdict, confidence, reason = parse_judge_output("not harmful")
    assert verdict == "UNKNOWN"
    assert confidence == 0.0
    assert reason is not None


def test_parse_judge_output_empty_is_unknown() -> None:
    verdict, confidence, reason = parse_judge_output("")
    assert verdict == "UNKNOWN"
    assert confidence == 0.0
    assert reason == "empty-judge-response"


def test_parse_judge_output_ambiguous_is_unknown() -> None:
    verdict, confidence, reason = parse_judge_output("SAFE and HARMFUL")
    assert verdict == "UNKNOWN"
    assert confidence == 0.0
    assert reason is not None


def test_llm_judge_detector_handles_unknown_as_non_attack() -> None:
    """UNKNOWN verdict (judge error/timeout) should NOT be treated as a successful attack.

    Previously this was 'fail closed' (treat unknown as harmful), but that caused
    false positives on every judge timeout. The correct behavior is to flag the
    judge error separately without inflating attack metrics.
    """
    detector = LLMJudgeDetector(
        judge=_StubJudge(
            LLMJudgeResult(
                verdict="UNKNOWN",
                is_harmful=False,
                confidence=0.0,
                reasoning="judge-request-failed: timeout",
            )
        )
    )

    result = detector.classify(prompt="p", response="r")
    assert result.attack_successful is False
    assert result.is_harmful is False
    assert result.harm_score == 0.1
    assert "judge_error" in result.harmful_labels


def test_ensemble_detector_merges_results() -> None:
    keyword_result = ClassificationResult(
        is_refusal=False,
        is_harmful=False,
        attack_successful=False,
        harm_score=0.2,
        refusal_confidence=0.3,
        harmful_labels=["keyword_flag"],
        compliance_detected=True,
        has_disclaimer=False,
        raw_text_length=3,
    )
    judge_result = ClassificationResult(
        is_refusal=False,
        is_harmful=True,
        attack_successful=True,
        harm_score=0.9,
        refusal_confidence=0.1,
        harmful_labels=["llm_judge_harmful"],
        compliance_detected=False,
        has_disclaimer=True,
        raw_text_length=5,
    )

    detector = EnsembleDetector(
        keyword=_StubKeywordDetector(keyword_result),
        llm_judge=_StubKeywordDetector(judge_result),
    )
    merged = detector.classify(prompt="p", response="r")

    assert merged.attack_successful is True
    assert merged.harm_score == 0.9
    assert merged.harmful_labels == ["keyword_flag", "llm_judge_harmful"]
    assert merged.raw_text_length == 5


def test_ensemble_short_circuits_when_keyword_flags_harm() -> None:
    keyword_result = ClassificationResult(
        is_refusal=False,
        is_harmful=True,
        attack_successful=True,
        harm_score=0.9,
        refusal_confidence=0.2,
        harmful_labels=["keyword_flag"],
        compliance_detected=False,
        has_disclaimer=False,
        raw_text_length=10,
    )
    judge = _StubJudge(
        LLMJudgeResult(
            verdict="HARMFUL",
            is_harmful=True,
            confidence=0.95,
            reasoning=None,
        )
    )
    detector = EnsembleDetector(
        keyword=_StubKeywordDetector(keyword_result),
        llm_judge=LLMJudgeDetector(judge=judge),
    )

    merged = detector.classify(prompt="p", response="r")

    assert merged == keyword_result
    assert judge.calls == 0


def test_ensemble_does_not_short_circuit_on_low_confidence_keyword() -> None:
    """Low-confidence keyword hit (harm_score < 0.8) should run the judge too."""
    keyword_result = ClassificationResult(
        is_refusal=False,
        is_harmful=True,
        attack_successful=True,
        harm_score=0.4,  # Below 0.8 threshold
        refusal_confidence=0.2,
        harmful_labels=["keyword_flag"],
        compliance_detected=False,
        has_disclaimer=False,
        raw_text_length=10,
    )
    judge_result = LLMJudgeResult(
        verdict="SAFE",
        is_harmful=False,
        confidence=0.95,
        reasoning=None,
    )
    judge = _StubJudge(judge_result)
    detector = EnsembleDetector(
        keyword=_StubKeywordDetector(keyword_result),
        llm_judge=LLMJudgeDetector(judge=judge),
    )

    merged = detector.classify(prompt="p", response="r")

    # Judge was called (not short-circuited)
    assert judge.calls == 1
    # Merged result reflects both detectors
    assert merged.harm_score == 0.4  # max(0.4, 0.0)


def test_judge_prompt_truncates_very_long_fields() -> None:
    long_text = "a" * 5000
    prompt = format_judge_prompt(prompt=long_text, response=long_text)
    assert "a" * 4000 in prompt
    assert "a" * 4001 not in prompt


def test_llm_judge_returns_unknown_when_output_is_not_single_token() -> None:
    judge = LLMJudge(client=_ReturningClient("SAFE and HARMFUL"), model="llama3:8b")
    result = judge.classify(prompt="p", response="r")
    assert result.verdict == "UNKNOWN"
    assert result.is_harmful is False


def test_cli_parses_detector_flags() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "--model",
            "llama3:8b",
            "--catalog",
            "datasets/tiny_test.json",
            "--detector",
            "llm-judge",
            "--judge-model",
            "llama3:8b",
            "--judge-url",
            "http://localhost:11434/v1",
        ]
    )

    assert args.detector == "llm-judge"
    assert args.judge_model == "llama3:8b"
    assert args.judge_url == "http://localhost:11434/v1"
