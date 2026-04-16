"""Tests for psg.security.redaction.

Covers the expanded credential pattern set added in Phase 1.5: each provider's
key format must be redacted in PARTIAL mode without false-positive matches on
similar-looking but unrelated text.

Test fixtures are assembled at runtime from a prefix plus an "A"-filled body
so that the literal provider-key patterns never appear as contiguous strings
in source (which would trip GitHub's secret-scanning push protection).
"""
from __future__ import annotations

import pytest

from psg.models import RedactionMode
from psg.security.redaction import redact_text


# Prefix + body-length pairs. Assembling at runtime keeps the full literal
# pattern out of source code while still exercising each provider regex.
_CREDENTIAL_FIXTURES = [
    ("sk-ant-api03-", 43),         # Anthropic
    ("sk-", 24),                    # OpenAI
    ("sk-proj-", 24),               # OpenAI project
    ("sk-svcacct-", 24),            # OpenAI service account
    ("AKIA", "IOSFODNN7EXAMPLE"),   # AWS access key id (fixed example from AWS docs)
    ("ghp_", 36),                   # GitHub classic PAT
    ("gho_", 36),                   # GitHub OAuth
    ("github_pat_", 40),            # GitHub fine-grained PAT
    ("xoxb-1234567890-1234567890-", 24),  # Slack bot token
    ("AIza", 35),                   # Google API key
    ("sk" + "_" + "live" + "_", 24),      # Stripe-shape live secret (split to dodge secret scan)
    ("sk" + "_" + "test" + "_", 24),      # Stripe-shape test secret
    ("rk" + "_" + "live" + "_", 24),      # Stripe-shape restricted
]


def _assemble(prefix: str, body) -> str:
    if isinstance(body, int):
        return prefix + ("A" * body)
    return prefix + body


@pytest.mark.parametrize(
    "prefix,body",
    _CREDENTIAL_FIXTURES,
    ids=[p[0].strip("-_") or "raw" for p in _CREDENTIAL_FIXTURES],
)
def test_partial_mode_redacts_known_credential_formats(prefix: str, body) -> None:
    secret = _assemble(prefix, body)
    text = f"My token is {secret} please don't share."
    redacted = redact_text(text, RedactionMode.PARTIAL)
    assert secret not in redacted
    assert "[REDACTED_KEY]" in redacted


def test_partial_mode_redacts_jwt() -> None:
    # JWT = three base64url segments joined by dots. Build at runtime.
    header = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    payload = "eyJzdWIiOiIxMjM0NSJ9"
    signature = "signature_part_abcdef"
    jwt = ".".join([header, payload, signature])
    redacted = redact_text(f"token={jwt}", RedactionMode.PARTIAL)
    assert jwt not in redacted
    assert "[REDACTED_KEY]" in redacted


def test_partial_mode_redacts_bearer_header() -> None:
    token_body = "A" * 32
    text = f"curl -H 'Authorization: Bearer {token_body}'"
    redacted = redact_text(text, RedactionMode.PARTIAL)
    assert token_body not in redacted
    assert "[REDACTED_KEY]" in redacted


def test_partial_mode_redacts_generic_assignment() -> None:
    body = "A" * 20
    text = f'config: api_key = "{body}"'
    redacted = redact_text(text, RedactionMode.PARTIAL)
    assert body not in redacted


@pytest.mark.parametrize(
    "benign",
    [
        "The book on page 42 is great",
        "ssh user@example.com -i id_rsa",  # Should redact email but not the rest as a key
        "git checkout main",
    ],
)
def test_partial_mode_does_not_redact_benign_text(benign: str) -> None:
    redacted = redact_text(benign, RedactionMode.PARTIAL)
    # We allow email/phone to still be redacted; just ensure the non-credential
    # tokens like "main", "checkout", "page", "book" are preserved.
    for word in ("page", "book", "main", "checkout", "ssh", "git"):
        if word in benign:
            assert word in redacted, f"benign word {word!r} was over-redacted in {redacted!r}"


def test_off_mode_returns_text_unchanged() -> None:
    body = "A" * 32
    text = f"Bearer {body} and email user@example.com"
    assert redact_text(text, RedactionMode.OFF) == text


def test_strict_mode_replaces_all_alphanumerics() -> None:
    text = "Hello, World 123!"
    redacted = redact_text(text, RedactionMode.STRICT)
    assert redacted == "XXXXX, XXXXX XXX!"
