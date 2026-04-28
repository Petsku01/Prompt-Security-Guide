"""Shared test fixtures for PSG modules."""

from __future__ import annotations

import pytest

from psg.models import Attack, LLMResponse


@pytest.fixture
def sample_attack() -> Attack:
    return Attack(id="A-1", prompt="Test prompt", metadata={"category": "test"})


@pytest.fixture
def sample_llm_response() -> LLMResponse:
    return LLMResponse(
        content="Safe response", raw={"id": "resp_1"}, model="test-model"
    )
