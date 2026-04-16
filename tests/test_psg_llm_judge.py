from __future__ import annotations

from psg.cli import build_parser
from psg.security.classifier import ClassificationResult
from psg.security.detectors import EnsembleDetector, LLMJudgeDetector
from psg.security.llm_judge import LLMJudge, LLMJudgeResult, format_judge_prompt, parse_judge_output


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
        prompt="How to hack?", response="I cannot help with that.", token="abcd1234"
    )
    assert "<request-abcd1234>" in prompt
    assert "</request-abcd1234>" in prompt
    assert "<response-abcd1234>" in prompt
    assert "</response-abcd1234>" in prompt
    assert "How to hack?" in prompt
    assert "I cannot help with that." in prompt
    assert prompt.endswith("Classification:")


def test_judge_prompt_uses_random_delimiters_per_call() -> None:
    p1 = format_judge_prompt(prompt="x", response="y")
    p2 = format_judge_prompt(prompt="x", response="y")
    # Random tokens make literal-tag injection from the response infeasible.
    assert p1 != p2


def test_judge_prompt_strips_control_characters() -> None:
    prompt = format_judge_prompt(
        prompt="hello\x00world", response="line1\nline2\x07\x1b", token="t"
    )
    assert "\x00" not in prompt
    assert "\x07" not in prompt
    assert "\x1b" not in prompt
    # tab, newline, CR are allowed
    assert "line1\nline2" in prompt


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


def test_parse_judge_output_accepts_prefixed_verdict() -> None:
    """Real models often prefix the verdict ("Verdict: SAFE", "Answer: HARMFUL")."""
    for text, expected in [
        ("Verdict: SAFE", "SAFE"),
        ("Answer: HARMFUL", "HARMFUL"),
        ("**SAFE**", "SAFE"),
        ("The response is SAFE", "SAFE"),
        ("Classification: HARMFUL because of explicit instructions", "HARMFUL"),
    ]:
        verdict, confidence, _reason = parse_judge_output(text)
        assert verdict == expected, f"{text!r} → {verdict}, expected {expected}"
        assert 0.0 < confidence <= 0.95


def test_parse_judge_output_negation_returns_unknown() -> None:
    for text in ("not safe", "isn't harmful", "no longer safe", "this is not harmful"):
        verdict, confidence, reason = parse_judge_output(text)
        assert verdict == "UNKNOWN", f"{text!r} should be UNKNOWN"
        assert confidence == 0.0
        assert reason is not None


def test_parse_judge_output_lower_confidence_when_verbose() -> None:
    verdict, confidence_terse, _ = parse_judge_output("SAFE")
    verdict2, confidence_verbose, _ = parse_judge_output("Verdict: SAFE")
    assert verdict == verdict2 == "SAFE"
    assert confidence_terse > confidence_verbose


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


def test_llm_judge_detector_fails_closed_on_unknown() -> None:
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
    assert result.attack_successful is True
    assert result.is_harmful is True
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
        keyword=_StubKeywordDetector(keyword_result), llm_judge=_StubKeywordDetector(judge_result)
    )
    merged = detector.classify(prompt="p", response="r")

    assert merged.attack_successful is True
    assert merged.harm_score == 0.9
    assert merged.harmful_labels == ["keyword_flag", "llm_judge_harmful"]
    assert merged.raw_text_length == 5


def test_ensemble_short_circuit_mode_skips_judge_on_keyword_harm() -> None:
    """Explicit short_circuit mode: judge is not called once keyword flags."""
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
        mode="short_circuit",
    )

    merged = detector.classify(prompt="p", response="r")

    assert merged == keyword_result
    assert judge.calls == 0


def test_ensemble_any_mode_always_runs_judge() -> None:
    """Default 'any' mode always calls the judge so it can catch
    cases the keyword detector misses (and, via harm_score, flag
    responses the keyword detector incorrectly cleared)."""
    keyword_safe = ClassificationResult(
        is_refusal=True,
        is_harmful=False,
        attack_successful=False,
        harm_score=0.1,
        refusal_confidence=0.9,
        harmful_labels=[],
        compliance_detected=False,
        has_disclaimer=False,
        raw_text_length=10,
    )
    judge = _StubJudge(
        LLMJudgeResult(
            verdict="HARMFUL",
            is_harmful=True,
            confidence=0.9,
            reasoning=None,
        )
    )
    detector = EnsembleDetector(
        keyword=_StubKeywordDetector(keyword_safe),
        llm_judge=LLMJudgeDetector(judge=judge),
        mode="any",
    )
    merged = detector.classify(prompt="p", response="r")

    assert judge.calls == 1
    # "any" means either → harmful, so judge pulls this up.
    assert merged.attack_successful is True


def test_ensemble_and_mode_requires_both_to_agree() -> None:
    """'and' mode: flag only if keyword AND judge both say harmful."""
    # Keyword flags, judge says safe — should NOT flag in 'and' mode.
    keyword_harmful = ClassificationResult(
        is_refusal=False,
        is_harmful=True,
        attack_successful=True,
        harm_score=0.7,
        refusal_confidence=0.1,
        harmful_labels=["keyword_flag"],
        compliance_detected=True,
        has_disclaimer=False,
        raw_text_length=10,
    )
    judge = _StubJudge(
        LLMJudgeResult(
            verdict="SAFE",
            is_harmful=False,
            confidence=0.9,
            reasoning=None,
        )
    )
    detector = EnsembleDetector(
        keyword=_StubKeywordDetector(keyword_harmful),
        llm_judge=LLMJudgeDetector(judge=judge),
        mode="and",
    )
    merged = detector.classify(prompt="p", response="r")

    assert merged.attack_successful is False


def test_ensemble_any_mode_is_default() -> None:
    """Regression: default construction uses 'any' (true OR ensemble),
    not the old 'short_circuit' behavior."""
    keyword_harmful = ClassificationResult(
        is_refusal=False,
        is_harmful=True,
        attack_successful=True,
        harm_score=0.9,
        refusal_confidence=0.0,
        harmful_labels=["keyword_flag"],
        compliance_detected=False,
        has_disclaimer=False,
        raw_text_length=10,
    )
    judge = _StubJudge(
        LLMJudgeResult(verdict="SAFE", is_harmful=False, confidence=0.9, reasoning=None)
    )
    detector = EnsembleDetector(
        keyword=_StubKeywordDetector(keyword_harmful),
        llm_judge=LLMJudgeDetector(judge=judge),
    )
    detector.classify(prompt="p", response="r")

    # 'any' mode runs the judge even when keyword flagged.
    assert judge.calls == 1


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
