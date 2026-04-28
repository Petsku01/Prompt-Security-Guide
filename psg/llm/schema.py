from __future__ import annotations

from typing import Any

from .errors import ParseError
from ..models import LLMResponse


def parse_chat_completion(data: dict[str, Any]) -> LLMResponse:
    """Defensive parser for OpenAI-compatible variants."""
    if not isinstance(data, dict):
        raise ParseError("response is not an object")

    model = _as_str(data.get("model"))
    content = ""
    finish_reason = None

    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0] if isinstance(choices[0], dict) else {}
        finish_reason = _as_str(first.get("finish_reason"))

        message = first.get("message") if isinstance(first, dict) else None
        if isinstance(message, dict):
            # content may be string or list parts
            msg_content = message.get("content")
            content = _content_to_text(msg_content)

        if not content:
            # some providers put plain text under 'text'
            content = _as_str(first.get("text")) or ""

    # legacy or malformed variants
    if not content:
        if "response" in data:
            content = _content_to_text(data.get("response"))
        elif "message" in data and isinstance(data["message"], dict):
            content = _content_to_text(data["message"].get("content"))
        elif "content" in data:
            content = _content_to_text(data.get("content"))

    return LLMResponse(
        content=content or "", raw=data, model=model, finish_reason=finish_reason
    )


def _content_to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return ""


def _as_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None
