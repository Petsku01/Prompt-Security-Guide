from __future__ import annotations

import re

from ..models import RedactionMode


EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"\b(?:\+?\d[\d\-\s]{7,}\d)\b")
KEY_RE = re.compile(r"\b(sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16})\b")


def redact_text(text: str, mode: RedactionMode) -> str:
    if mode == RedactionMode.OFF:
        return text

    if mode == RedactionMode.STRICT:
        # strict: replace almost all alphanumerics while preserving whitespace/punctuation shape
        return "".join("X" if c.isalnum() else c for c in text)

    # partial default
    redacted = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    redacted = PHONE_RE.sub("[REDACTED_PHONE]", redacted)
    redacted = KEY_RE.sub("[REDACTED_KEY]", redacted)
    return redacted
