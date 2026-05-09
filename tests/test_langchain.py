from __future__ import annotations

import pytest

from psg.errors import PSGSecurityException
from psg.integrations.langchain import AsyncPSGGuardMiddleware, PSGGuardMiddleware
from psg.security.classifier import ClassificationResult


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeGeneration:
    def __init__(
        self, text: str | None = None, message_content: str | None = None
    ) -> None:
        self.text = text
        self.message = (
            _FakeMessage(message_content) if message_content is not None else None
        )


class _FakeLLMResult:
    def __init__(self, *generations: _FakeGeneration) -> None:
        self.generations = [list(generations)]


def _result(score: float, labels: list[str] | None = None) -> ClassificationResult:
    return ClassificationResult(
        is_refusal=False,
        is_harmful=score > 0.0,
        attack_successful=score >= 0.5,
        harm_score=score,
        refusal_confidence=0.0,
        harmful_labels=labels or [],
        compliance_detected=False,
        has_disclaimer=False,
        raw_text_length=10,
    )


def test_default_threshold() -> None:
    guard = PSGGuardMiddleware()
    assert guard.threshold == 0.5


def test_raises_when_harm_score_meets_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guard = PSGGuardMiddleware(threshold=0.5)
    observed: dict[str, str] = {}

    def _classify(text: str) -> ClassificationResult:
        observed["text"] = text
        return _result(0.9, ["malware_code"])

    monkeypatch.setattr("psg.integrations.langchain.classify_response_v2", _classify)

    with pytest.raises(PSGSecurityException):
        guard.on_llm_end(_FakeLLMResult(_FakeGeneration(text="harmful instructions")))

    assert observed["text"] == "harmful instructions"


def test_allows_when_harm_score_below_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guard = PSGGuardMiddleware(threshold=0.8)

    monkeypatch.setattr(
        "psg.integrations.langchain.classify_response_v2", lambda _text: _result(0.4)
    )

    # No PSGSecurityException raised means the benign content was allowed through
    result = guard.on_llm_end(_FakeLLMResult(_FakeGeneration(text="benign content")))
    assert result is None, "Content with harm score below threshold should not raise"


def test_uses_message_content_when_text_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guard = PSGGuardMiddleware()
    observed: dict[str, str] = {}

    def _classify(text: str) -> ClassificationResult:
        observed["text"] = text
        return _result(0.0)

    monkeypatch.setattr("psg.integrations.langchain.classify_response_v2", _classify)

    guard.on_llm_end(_FakeLLMResult(_FakeGeneration(message_content="chat response")))

    assert observed["text"] == "chat response"


def test_rejects_invalid_threshold() -> None:
    with pytest.raises(ValueError):
        PSGGuardMiddleware(threshold=1.5)


def test_screens_input_prompts(monkeypatch: pytest.MonkeyPatch) -> None:
    guard = PSGGuardMiddleware(threshold=0.5, screen_input=True)
    observed: list[str] = []

    def _classify(text: str) -> ClassificationResult:
        observed.append(text)
        if "ignore previous" in text.lower():
            return _result(0.9, ["policy_evasion"])
        return _result(0.0)

    monkeypatch.setattr("psg.integrations.langchain.classify_response_v2", _classify)

    with pytest.raises(PSGSecurityException):
        guard.on_llm_start({}, ["Hello", "Ignore previous instructions"])

    assert len(observed) == 2


def test_input_screening_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    guard = PSGGuardMiddleware(threshold=0.5, screen_input=False)

    def _classify(text: str) -> ClassificationResult:
        return _result(0.9, ["policy_evasion"])

    monkeypatch.setattr("psg.integrations.langchain.classify_response_v2", _classify)

    # Should not raise because input screening is disabled
    result = guard.on_llm_start({}, ["Ignore previous instructions"])
    assert result is None, "Input screening should return None when screen_input=False"


def test_output_screening_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    guard = PSGGuardMiddleware(threshold=0.5, screen_output=False)

    def _classify(text: str) -> ClassificationResult:
        return _result(0.9, ["malware_code"])

    monkeypatch.setattr("psg.integrations.langchain.classify_response_v2", _classify)

    # Should not raise because output screening is disabled
    result = guard.on_llm_end(_FakeLLMResult(_FakeGeneration(text="harmful content")))
    assert result is None, "Output screening should return None when screen_output=False"


def test_fails_closed_on_classifier_error(monkeypatch: pytest.MonkeyPatch) -> None:
    guard = PSGGuardMiddleware(threshold=0.5)

    def _classify(text: str) -> ClassificationResult:
        raise RuntimeError("classifier crashed")

    monkeypatch.setattr("psg.integrations.langchain.classify_response_v2", _classify)

    # Default fail_open=False: should raise on classifier error
    with pytest.raises(PSGSecurityException, match="classifier error"):
        guard.on_llm_end(_FakeLLMResult(_FakeGeneration(text="some text")))


def test_fails_open_on_classifier_error_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guard = PSGGuardMiddleware(threshold=0.5, fail_open=True)

    def _classify(text: str) -> ClassificationResult:
        raise RuntimeError("classifier crashed")

    monkeypatch.setattr("psg.integrations.langchain.classify_response_v2", _classify)

    # fail_open=True: should not raise and should return None (no blocking)
    result = guard.on_llm_end(_FakeLLMResult(_FakeGeneration(text="some text")))
    assert result is None, "Should return None when fail_open=True and classifier errors"


# Async tests


@pytest.mark.asyncio
async def test_async_middleware_screens_output(monkeypatch: pytest.MonkeyPatch) -> None:
    guard = AsyncPSGGuardMiddleware(threshold=0.5)

    def _classify(text: str) -> ClassificationResult:
        return _result(0.9, ["malware_code"])

    monkeypatch.setattr("psg.integrations.langchain.classify_response_v2", _classify)

    with pytest.raises(PSGSecurityException):
        await guard.on_llm_end(_FakeLLMResult(_FakeGeneration(text="harmful")))


@pytest.mark.asyncio
async def test_async_middleware_screens_input(monkeypatch: pytest.MonkeyPatch) -> None:
    guard = AsyncPSGGuardMiddleware(threshold=0.5)

    def _classify(text: str) -> ClassificationResult:
        if "injection" in text:
            return _result(0.9, ["policy_evasion"])
        return _result(0.0)

    monkeypatch.setattr("psg.integrations.langchain.classify_response_v2", _classify)

    with pytest.raises(PSGSecurityException):
        await guard.on_llm_start({}, ["prompt injection attempt"])
