from __future__ import annotations

import logging
from typing import Any

try:
    from langchain_core.callbacks import AsyncCallbackHandler, BaseCallbackHandler
except ImportError:  # pragma: no cover - optional dependency fallback
    class BaseCallbackHandler:  # type: ignore[no-redef]
        """Fallback base class when langchain-core is not installed."""

    class AsyncCallbackHandler:  # type: ignore[no-redef]
        """Fallback async base class when langchain-core is not installed."""


from psg.errors import PSGSecurityException
from psg.security.classifier import classify_response_v2

logger = logging.getLogger(__name__)


class PSGGuardMiddleware(BaseCallbackHandler):
    """LangChain callback middleware that screens LLM inputs and outputs.
    
    Features:
    - Output screening via on_llm_end (blocks harmful responses)
    - Input screening via on_llm_start (blocks prompt injection attempts)
    - Configurable threshold (default 0.5)
    - Raises PSGSecurityException when harm_score >= threshold
    
    Usage:
        from langchain_openai import ChatOpenAI
        from psg.integrations.langchain import PSGGuardMiddleware
        
        llm = ChatOpenAI(callbacks=[PSGGuardMiddleware(threshold=0.5)])
    """

    def __init__(
        self,
        threshold: float = 0.5,
        screen_input: bool = True,
        screen_output: bool = True,
    ) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")
        self.threshold = threshold
        self.screen_input = screen_input
        self.screen_output = screen_output

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        **kwargs: Any,
    ) -> None:
        """Screen input prompts for potential injection attempts."""
        if not self.screen_input:
            return
        
        for prompt in prompts:
            self._check_text(prompt, direction="input")

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Screen LLM output for harmful content."""
        if not self.screen_output:
            return
        
        text = self._extract_response_text(response)
        self._check_text(text, direction="output")

    def _check_text(self, text: str, direction: str) -> None:
        """Classify text and raise if above threshold."""
        try:
            result = classify_response_v2(text)
        except Exception as exc:
            logger.warning("PSG classification failed for %s: %s", direction, exc)
            return  # Fail open - don't block on classifier errors
        
        logger.debug(
            "PSG %s check: harm_score=%.2f, threshold=%.2f, labels=%s",
            direction,
            result.harm_score,
            self.threshold,
            result.harmful_labels,
        )
        
        if result.harm_score >= self.threshold:
            labels = ", ".join(result.harmful_labels) if result.harmful_labels else "unknown"
            raise PSGSecurityException(
                f"PSG blocked LLM {direction} "
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


class AsyncPSGGuardMiddleware(AsyncCallbackHandler):
    """Async version of PSGGuardMiddleware for async LangChain chains.
    
    Same features as PSGGuardMiddleware but with async methods.
    """

    def __init__(
        self,
        threshold: float = 0.5,
        screen_input: bool = True,
        screen_output: bool = True,
    ) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")
        self.threshold = threshold
        self.screen_input = screen_input
        self.screen_output = screen_output
        self._sync = PSGGuardMiddleware(threshold, screen_input, screen_output)

    async def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        **kwargs: Any,
    ) -> None:
        """Screen input prompts for potential injection attempts."""
        self._sync.on_llm_start(serialized, prompts, **kwargs)

    async def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Screen LLM output for harmful content."""
        self._sync.on_llm_end(response, **kwargs)
