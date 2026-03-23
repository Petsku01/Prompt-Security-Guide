from __future__ import annotations

from urllib.parse import urljoin

from ..models import LLMResponse
from .schema import parse_chat_completion
from .transport import Transport


class OpenAICompatibleClient:
    def __init__(self, base_url: str, transport: Transport, api_key: str | None = None) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.transport = transport
        self.api_key = api_key

    def chat(
        self, 
        *, 
        model: str, 
        prompt: str, 
        temperature: float = 0.0,
        max_tokens: int = 512
    ) -> LLMResponse:
        endpoint = urljoin(self.base_url, "chat/completions")
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        data = self.transport.post_json(endpoint, payload, headers=headers)
        return parse_chat_completion(data)
