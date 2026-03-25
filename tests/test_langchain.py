from __future__ import annotations

import pytest

from psg.errors import PSGSecurityException
from psg.integrations.langchain import PSGGuardMiddleware
from psg.security.classifier import ClassificationResult


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeGeneration:
    def __init__(self, text: str | None = None, message_content: str | None = None) -> None:
        self.text = text
        self.message = _FakeMessage(message_content) if message_content is not None else None


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


def test_raises_when_harm_score_meets_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    guard = PSGGuardMiddleware(threshold=0.5)
    observed: dict[str, str] = {}

    def _classify(text: str) -> ClassificationResult:
        observed["text"] = text
        return _result(0.9, ["malware_code"])

    monkeypatch.setattr("psg.integrations.langchain.classify_response_v2", _classify)

    with pytest.raises(PSGSecurityException):
        guard.on_llm_end(_FakeLLMResult(_FakeGeneration(text="harmful instructions")))

    assert observed["text"] == "harmful instructions"


def test_allows_when_harm_score_below_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    guard = PSGGuardMiddleware(threshold=0.8)

    monkeypatch.setattr("psg.integrations.langchain.classify_response_v2", lambda _text: _result(0.4))

    guard.on_llm_end(_FakeLLMResult(_FakeGeneration(text="benign content")))


def test_uses_message_content_when_text_missing(monkeypatch: pytest.MonkeyPatch) -> None:
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
