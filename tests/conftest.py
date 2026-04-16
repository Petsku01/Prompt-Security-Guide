"""Shared test fixtures for PSG modules.

Design notes:
- Prefer ``spec_set=`` Mocks over bare ``Mock()`` for protocol-like
  boundaries (``Detector``, ``OpenAICompatibleClient``). A bare Mock
  happily accepts any attribute or method call, which is how the C1/C2
  interface bugs (detector.detect vs detector.classify, client.chat with
  wrong kwargs) survived a full test suite. ``spec_set=ClassName`` makes
  the mock reject attributes that don't exist on the real class.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from psg.llm.client import OpenAICompatibleClient
from psg.models import Attack, LLMResponse
from psg.security.classifier import ClassificationResult
from psg.security.detectors import Detector


@pytest.fixture
def sample_attack() -> Attack:
    return Attack(id="A-1", prompt="Test prompt", metadata={"category": "test"})


@pytest.fixture
def sample_llm_response() -> LLMResponse:
    return LLMResponse(content="Safe response", raw={"id": "resp_1"}, model="test-model")


@pytest.fixture
def safe_classification() -> ClassificationResult:
    """A canonical "safe" classification suitable for mock return values."""
    return ClassificationResult(
        is_refusal=True,
        is_harmful=False,
        attack_successful=False,
        harm_score=0.0,
        refusal_confidence=0.9,
        harmful_labels=[],
        compliance_detected=False,
        has_disclaimer=False,
        raw_text_length=10,
    )


@pytest.fixture
def harmful_classification() -> ClassificationResult:
    """A canonical "harmful" classification suitable for mock return values."""
    return ClassificationResult(
        is_refusal=False,
        is_harmful=True,
        attack_successful=True,
        harm_score=0.9,
        refusal_confidence=0.0,
        harmful_labels=["malware_code"],
        compliance_detected=True,
        has_disclaimer=False,
        raw_text_length=100,
    )


@pytest.fixture
def mock_detector(safe_classification):
    """Spec-bound Detector mock.

    Reject attribute access that isn't on the Detector protocol —
    detector.detect(...) (the C1 bug) now raises AttributeError instead
    of silently returning a MagicMock.
    """
    detector = MagicMock(spec_set=Detector)
    detector.classify.return_value = safe_classification
    return detector


@pytest.fixture
def mock_llm_client(sample_llm_response):
    """Spec-bound OpenAICompatibleClient mock.

    Reject method calls that don't exist on the real client
    (client.completions(...), client.chat(messages=...) — the C2 bug).
    """
    client = MagicMock(spec_set=OpenAICompatibleClient)
    client.chat.return_value = sample_llm_response
    client.chat_multi_turn.return_value = sample_llm_response
    return client
