from __future__ import annotations

from urllib.parse import urljoin

from ..models import LLMResponse
from .schema import parse_chat_completion
from .transport import Transport


class OpenAICompatibleClient:
    def __init__(
        self, base_url: str, transport: Transport, api_key: str | None = None
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.transport = transport
        self.api_key = api_key

    def _post_chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Send a chat completion request and parse the response."""
        endpoint = urljoin(self.base_url, "chat/completions")
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        data = self.transport.post_json(endpoint, payload, headers=headers)
        return parse_chat_completion(data)

    def chat(
        self,
        *,
        model: str,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> LLMResponse:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self._post_chat(model, messages, temperature, max_tokens)

    def chat_multi_turn(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> LLMResponse:
        """Multi-turn chat with message history."""
        full_messages: list[dict[str, str]] = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)
        return self._post_chat(model, full_messages, temperature, max_tokens)
