from __future__ import annotations

from urllib.parse import urljoin

from ..models import LLMResponse
from .schema import parse_chat_completion
from .transport import Transport


class OpenAICompatibleClient:
    def __init__(self, base_url: str, transport: Transport) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.transport = transport

    def chat(self, *, model: str, prompt: str, temperature: float = 0.0) -> LLMResponse:
        endpoint = urljoin(self.base_url, "chat/completions")
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        data = self.transport.post_json(endpoint, payload)
        return parse_chat_completion(data)
