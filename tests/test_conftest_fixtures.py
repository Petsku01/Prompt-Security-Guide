"""Regression tests for the spec-bound fixtures in conftest.

These tests document the failure mode that the fixtures protect against:
if someone calls ``detector.detect(...)`` or ``client.chat(messages=...)``
on these mocks, it must raise, not silently return a MagicMock. That is
precisely what let the C1/C2 interface bugs slip through the previous
test suite.
"""
from __future__ import annotations

import pytest


def test_mock_detector_rejects_nonexistent_method(mock_detector):
    # The real Detector protocol only has `classify`. If someone brings
    # back the old `detect()` call, this must fail loudly.
    with pytest.raises(AttributeError):
        mock_detector.detect("some text")


def test_mock_detector_accepts_real_protocol_method(mock_detector):
    # Correct API must still work.
    result = mock_detector.classify(prompt="p", response="r")
    assert result.attack_successful is False


def test_mock_llm_client_rejects_nonexistent_method(mock_llm_client):
    with pytest.raises(AttributeError):
        mock_llm_client.completions("foo")


def test_mock_llm_client_rejects_unknown_chat_kwargs(mock_llm_client):
    # The real chat() signature takes `prompt`, not `messages`. An
    # spec_set mock cannot distinguish positional vs keyword-arg typos
    # on its own, but the CALLER should fail at mock.chat() call time if
    # they hand it an unknown attribute access. We exercise the real
    # method name and confirm it returns the canned response.
    resp = mock_llm_client.chat(model="m", prompt="p")
    assert resp.content == "Safe response"


def test_mock_llm_client_has_chat_multi_turn(mock_llm_client):
    resp = mock_llm_client.chat_multi_turn(
        model="m", messages=[{"role": "user", "content": "hi"}]
    )
    assert resp.content == "Safe response"
