from __future__ import annotations

import socket

import pytest

from psg.automation.validation import (
    validate_query,
    validate_url,
)


# ── validate_url: DNS resolution tests (original 3) ──────────────────────


def test_validate_url_blocks_dns_resolved_loopback(monkeypatch) -> None:
    monkeypatch.setattr(
        "psg.automation.validation.socket.getaddrinfo",
        lambda *_args, **_kwargs: [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("127.0.0.1", 443),
            )
        ],
    )

    assert validate_url("https://attacker.example") is False


def test_validate_url_allows_public_dns_resolution(monkeypatch) -> None:
    monkeypatch.setattr(
        "psg.automation.validation.socket.getaddrinfo",
        lambda *_args, **_kwargs: [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", 443),
            )
        ],
    )

    assert validate_url("https://example.com/page") is True


def test_validate_url_blocks_if_any_resolved_ip_is_private(monkeypatch) -> None:
    monkeypatch.setattr(
        "psg.automation.validation.socket.getaddrinfo",
        lambda *_args, **_kwargs: [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", 443),
            ),
            (
                socket.AF_INET6,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("::1", 443, 0, 0),
            ),
        ],
    )

    assert validate_url("https://mixed.example") is False


# ── validate_url: scheme & direct-IP tests (new) ─────────────────────────


def test_validate_url_blocks_literal_private_ip() -> None:
    """A URL with a literal RFC-1918 IP must be rejected without DNS."""
    assert validate_url("http://10.0.0.1/admin") is False


def test_validate_url_blocks_dangerous_scheme() -> None:
    """javascript: / data: / file: schemes embedded in the URL string are blocked."""
    assert validate_url("javascript:alert(1)") is False
    assert validate_url("data:text/html,<h1>hi</h1>") is False


# ── validate_query tests (new) ───────────────────────────────────────────


def test_validate_query_valid() -> None:
    """Normal alphanumeric queries pass through unchanged (after strip)."""
    assert validate_query("  prompt injection defense  ") == "prompt injection defense"


def test_validate_query_empty_raises() -> None:
    """Empty or whitespace-only queries are rejected."""
    with pytest.raises(ValueError, match="cannot be empty"):
        validate_query("")


def test_validate_query_too_long_raises() -> None:
    """Queries exceeding MAX_QUERY_LENGTH are rejected."""
    with pytest.raises(ValueError, match="too long"):
        validate_query("a" * 201)


def test_validate_query_invalid_chars_raises() -> None:
    """Queries with disallowed characters (e.g. < or >) are rejected."""
    with pytest.raises(ValueError, match="invalid characters"):
        validate_query("<script>alert(1)</script>")

