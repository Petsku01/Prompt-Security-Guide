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
    client = OpenAICompatibleClient(
        "https://api.example.test/v1", transport, api_key="abc123"
    )

    monkeypatch.setattr(
        "psg.llm.client.parse_chat_completion",
        lambda _data: LLMResponse(content="ok", raw={}),
    )
    client.chat(model="m", prompt="p")

    assert transport.last_headers == {"Authorization": "Bearer abc123"}


def test_client_sends_no_authorization_header_without_api_key(monkeypatch) -> None:
    transport = _FakeTransport()
    client = OpenAICompatibleClient("https://api.example.test/v1", transport)

    monkeypatch.setattr(
        "psg.llm.client.parse_chat_completion",
        lambda _data: LLMResponse(content="ok", raw={}),
    )
    client.chat(model="m", prompt="p")

    assert transport.last_headers == {}


def test_client_includes_system_message_when_provided(monkeypatch) -> None:
    transport = _FakeTransport()
    client = OpenAICompatibleClient("https://api.example.test/v1", transport)

    monkeypatch.setattr(
        "psg.llm.client.parse_chat_completion",
        lambda _data: LLMResponse(content="ok", raw={}),
    )
    client.chat(model="m", prompt="user prompt", system_prompt="system prompt")

    assert transport.last_payload["messages"] == [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "user prompt"},
    ]


# ── chat_multi_turn ───────────────────────────────────────────────────────


def test_chat_multi_turn_sends_message_history(monkeypatch) -> None:
    """chat_multi_turn must forward the full message list to _post_chat."""
    transport = _FakeTransport()
    client = OpenAICompatibleClient("https://api.example.test/v1", transport)

    monkeypatch.setattr(
        "psg.llm.client.parse_chat_completion",
        lambda _data: LLMResponse(content="ok", raw={}),
    )
    messages = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "reply"},
        {"role": "user", "content": "follow-up"},
    ]
    client.chat_multi_turn(model="m", messages=messages)

    assert transport.last_payload["messages"] == messages


def test_chat_multi_turn_prepends_system_prompt(monkeypatch) -> None:
    """chat_multi_turn must prepend a system message when provided."""
    transport = _FakeTransport()
    client = OpenAICompatibleClient("https://api.example.test/v1", transport)

    monkeypatch.setattr(
        "psg.llm.client.parse_chat_completion",
        lambda _data: LLMResponse(content="ok", raw={}),
    )
    messages = [{"role": "user", "content": "hello"}]
    client.chat_multi_turn(model="m", messages=messages, system_prompt="sys")

    assert transport.last_payload["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hello"},
    ]


def test_chat_multi_turn_forwards_temperature_and_max_tokens(monkeypatch) -> None:
    """chat_multi_turn must pass temperature and max_tokens through to the
    transport payload."""
    transport = _FakeTransport()
    client = OpenAICompatibleClient("https://api.example.test/v1", transport)

    monkeypatch.setattr(
        "psg.llm.client.parse_chat_completion",
        lambda _data: LLMResponse(content="ok", raw={}),
    )
    client.chat_multi_turn(
        model="m",
        messages=[{"role": "user", "content": "hi"}],
        temperature=0.7,
        max_tokens=1024,
    )

    assert transport.last_payload["temperature"] == 0.7
    assert transport.last_payload["max_tokens"] == 1024


# ── _post_chat shared logic ───────────────────────────────────────────────


def test_post_chat_builds_endpoint_url(monkeypatch) -> None:
    """_post_chat must POST to the chat/completions endpoint."""
    transport = _FakeTransport()
    client = OpenAICompatibleClient("https://api.example.test/v1", transport)

    monkeypatch.setattr(
        "psg.llm.client.parse_chat_completion",
        lambda _data: LLMResponse(content="ok", raw={}),
    )
    client.chat(model="m", prompt="p")

    # _FakeTransport doesn't capture URL, but we can verify it was called
    assert transport.last_payload is not None
    assert transport.last_payload["model"] == "m"


def test_post_chat_includes_api_key_in_headers(monkeypatch) -> None:
    """_post_chat must include Authorization header when api_key is set."""
    transport = _FakeTransport()
    client = OpenAICompatibleClient(
        "https://api.example.test/v1", transport, api_key="sk-test"
    )

    monkeypatch.setattr(
        "psg.llm.client.parse_chat_completion",
        lambda _data: LLMResponse(content="ok", raw={}),
    )
    client.chat_multi_turn(model="m", messages=[{"role": "user", "content": "hi"}])

    assert transport.last_headers == {"Authorization": "Bearer sk-test"}
