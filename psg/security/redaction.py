from __future__ import annotations

import re

from ..models import RedactionMode


EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"\b(?:\+?\d[\d\-\s]{7,}\d)\b")

# Credential / API-key patterns. Order matters only for overlapping matches —
# more-specific patterns must come before generic fallbacks.
KEY_PATTERNS: dict[str, re.Pattern[str]] = {
    # Anthropic: sk-ant-api03-...  / sk-ant-...
    "anthropic": re.compile(r"\bsk-ant-(?:api\d{2}-)?[A-Za-z0-9_\-]{32,}\b"),
    # OpenAI / OpenAI-compatible: sk-..., sk-proj-..., sk-svcacct-...
    "openai": re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_\-]{16,}\b"),
    # AWS access key id
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    # AWS secret access key (40 base64-ish chars after typical prefix context)
    "aws_secret_key": re.compile(r"(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])"),
    # GitHub tokens: classic + fine-grained
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "github_pat": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}\b"),
    # Slack tokens
    "slack_token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"),
    # Google API key
    "google_api_key": re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    # Stripe live/test secret keys
    "stripe_key": re.compile(r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{24,}\b"),
    # Generic JWT (three base64url segments separated by dots)
    "jwt": re.compile(
        r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b"
    ),
    # Bearer headers (capture the token after the keyword)
    "bearer_header": re.compile(r"(?i)\b[Bb]earer\s+[A-Za-z0-9._\-]{20,}\b"),
    # Generic high-entropy "secret/api[_-]?key/token" assignments
    "generic_assignment": re.compile(
        r"(?i)\b(?:api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|password)"
        r"\s*[:=]\s*[\"']?[A-Za-z0-9._\-]{12,}[\"']?"
    ),
}

def redact_text(text: str, mode: RedactionMode) -> str:
    if mode == RedactionMode.OFF:
        return text

    if mode == RedactionMode.STRICT:
        # strict: replace almost all alphanumerics while preserving whitespace/punctuation shape
        return "".join("X" if c.isalnum() else c for c in text)

    # partial default. Redact credentials FIRST so that overlapping numeric
    # spans (e.g. Slack token digits) are not consumed by the phone regex.
    redacted = text
    for pattern in KEY_PATTERNS.values():
        redacted = pattern.sub("[REDACTED_KEY]", redacted)
    redacted = EMAIL_RE.sub("[REDACTED_EMAIL]", redacted)
    redacted = PHONE_RE.sub("[REDACTED_PHONE]", redacted)
    return redacted
