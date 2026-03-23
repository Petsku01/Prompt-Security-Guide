from __future__ import annotations

from psg.llm.client import OpenAICompatibleClient
from psg.models import LLMResponse


class _FakeTransport:
    def __init__(self) -> None:
        self.last_headers = None
        self.last_payload = None

    def post_json(self, _url, payload, headers=None):
        self.last_headers = headers
        self.last_payload = payload
        return {"choices": [{"message": {"content": "ok"}}]}


def test_client_sends_authorization_header_when_api_key(monkeypatch) -> None:
    transport = _FakeTransport()
    client = OpenAICompatibleClient("https://api.example.test/v1", transport, api_key="abc123")

    monkeypatch.setattr("psg.llm.client.parse_chat_completion", lambda _data: LLMResponse(content="ok", raw={}))
    client.chat(model="m", prompt="p")

    assert transport.last_headers == {"Authorization": "Bearer abc123"}


def test_client_sends_no_authorization_header_without_api_key(monkeypatch) -> None:
    transport = _FakeTransport()
    client = OpenAICompatibleClient("https://api.example.test/v1", transport)

    monkeypatch.setattr("psg.llm.client.parse_chat_completion", lambda _data: LLMResponse(content="ok", raw={}))
    client.chat(model="m", prompt="p")

    assert transport.last_headers == {}


def test_client_includes_system_message_when_provided(monkeypatch) -> None:
    transport = _FakeTransport()
    client = OpenAICompatibleClient("https://api.example.test/v1", transport)

    monkeypatch.setattr("psg.llm.client.parse_chat_completion", lambda _data: LLMResponse(content="ok", raw={}))
    client.chat(model="m", prompt="user prompt", system_prompt="system prompt")

    assert transport.last_payload["messages"] == [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "user prompt"},
    ]
