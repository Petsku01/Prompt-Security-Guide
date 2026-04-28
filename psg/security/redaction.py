from __future__ import annotations

import re

from ..models import RedactionMode

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"\b(?:\+?\d[\d\-\s]{7,}\d)\b")
KEY_RE = re.compile(
    r"\b("
    r"sk-[A-Za-z0-9]{16,}"  # OpenAI
    r"|AKIA[0-9A-Z]{16}"  # AWS IAM
    r"|sk-ant-[A-Za-z0-9\-]{20,}"  # Anthropic
    r"|ghp_[A-Za-z0-9]{36}"  # GitHub PAT
    r"|gho_[A-Za-z0-9]{36}"  # GitHub OAuth
    r"|ya29\.[A-Za-z0-9\-_]{30,}"  # Google OAuth
    r"|AIza[A-Za-z0-9_\-]{35}"  # Google API
    r")\b"
)


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
