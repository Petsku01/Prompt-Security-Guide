from __future__ import annotations

import socket

from psg.automation.validation import validate_url


def test_validate_url_blocks_dns_resolved_loopback(monkeypatch) -> None:
    monkeypatch.setattr(
        "psg.validation.network.socket.getaddrinfo",
        lambda *_args, **_kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 443))
        ],
    )

    assert validate_url("https://attacker.example") is False


def test_validate_url_allows_public_dns_resolution(monkeypatch) -> None:
    monkeypatch.setattr(
        "psg.validation.network.socket.getaddrinfo",
        lambda *_args, **_kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443))
        ],
    )

    assert validate_url("https://example.com/page") is True


def test_validate_url_blocks_if_any_resolved_ip_is_private(monkeypatch) -> None:
    monkeypatch.setattr(
        "psg.validation.network.socket.getaddrinfo",
        lambda *_args, **_kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443)),
            (socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("::1", 443, 0, 0)),
        ],
    )

    assert validate_url("https://mixed.example") is False
