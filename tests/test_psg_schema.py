from __future__ import annotations

import pytest

from psg.llm.errors import ParseError
from psg.llm.schema import parse_chat_completion


def test_parse_chat_completion_valid_data() -> None:
    data = {
        "model": "llama3:8b",
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"content": "Safe response"},
            }
        ],
    }

    parsed = parse_chat_completion(data)

    assert parsed.model == "llama3:8b"
    assert parsed.finish_reason == "stop"
    assert parsed.content == "Safe response"
    assert parsed.raw == data


def test_parse_chat_completion_missing_fields() -> None:
    parsed = parse_chat_completion({})

    assert parsed.model is None
    assert parsed.finish_reason is None
    assert parsed.content == ""
    assert parsed.raw == {}


def test_parse_chat_completion_raises_parse_error_on_invalid_data() -> None:
    with pytest.raises(ParseError):
        parse_chat_completion([])  # type: ignore[arg-type]
