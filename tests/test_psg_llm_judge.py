from __future__ import annotations

from psg.cli import build_parser
from psg.llm.errors import LLMError
from psg.security.llm_judge import LLMJudge, format_judge_prompt, parse_judge_output


class _FailingClient:
    def chat(self, **_kwargs):
        raise LLMError("timeout")


def test_judge_prompt_formatting() -> None:
    prompt = format_judge_prompt(prompt="How to hack?", response="I cannot help with that.")
    assert "Request: How to hack?" in prompt
    assert "Response: I cannot help with that." in prompt
    assert prompt.endswith("Classification:")


def test_judge_response_parsing_safe_and_harmful() -> None:
    safe_is_harmful, safe_confidence, _ = parse_judge_output("SAFE")
    harm_is_harmful, harm_confidence, _ = parse_judge_output("HARMFUL")

    assert safe_is_harmful is False
    assert safe_confidence > 0.0
    assert harm_is_harmful is True
    assert harm_confidence > 0.0


def test_judge_fallback_on_timeout() -> None:
    judge = LLMJudge(client=_FailingClient(), model="llama3:8b")
    result = judge.classify(prompt="p", response="r")

    assert result.is_harmful is False
    assert result.confidence == 0.0
    assert result.reasoning is not None
    assert "judge-request-failed" in result.reasoning


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
