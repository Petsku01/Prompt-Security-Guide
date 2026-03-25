from __future__ import annotations

from typing import Any

try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:  # pragma: no cover - optional dependency fallback
    class BaseCallbackHandler:  # type: ignore[override]
        """Fallback base class when langchain-core is not installed."""


from psg.errors import PSGSecurityException
from psg.security.classifier import classify_response_v2


class PSGGuardMiddleware(BaseCallbackHandler):
    """LangChain callback middleware that blocks harmful model outputs."""

    def __init__(self, threshold: float = 0.5) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")
        self.threshold = threshold

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        text = self._extract_response_text(response)
        result = classify_response_v2(text)

        if result.harm_score >= self.threshold:
            labels = ", ".join(result.harmful_labels) if result.harmful_labels else "unknown"
            raise PSGSecurityException(
                "PSG blocked LLM output "
                f"(harm_score={result.harm_score:.2f}, threshold={self.threshold:.2f}, labels={labels})"
            )

    def _extract_response_text(self, response: Any) -> str:
        generations = getattr(response, "generations", None)
        if not generations:
            return str(response or "")

        texts: list[str] = []
        for row in generations:
            for generation in row:
                text = getattr(generation, "text", None)
                if isinstance(text, str) and text:
                    texts.append(text)
                    continue

                message = getattr(generation, "message", None)
                content = getattr(message, "content", None)
                if isinstance(content, str) and content:
                    texts.append(content)

        return "\n".join(texts)
