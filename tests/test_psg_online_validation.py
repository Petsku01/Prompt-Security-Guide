from __future__ import annotations

import socket

import requests

from psg.validation.online import clear_validation_cache, validate_doi, validate_url


class _Resp:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


def setup_function() -> None:
    clear_validation_cache()


def _public_dns(*_args, **_kwargs):
    return [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("93.184.216.34", 443),
        )
    ]


def test_validate_url_returns_true_for_redirect(monkeypatch) -> None:
    monkeypatch.setattr("psg.validation.online.socket.getaddrinfo", _public_dns)
    monkeypatch.setattr(
        "psg.validation.online.requests.head", lambda *_args, **_kwargs: _Resp(302)
    )
    assert validate_url("https://example.com") is True


def test_validate_url_returns_false_on_timeout(monkeypatch) -> None:
    monkeypatch.setattr("psg.validation.online.socket.getaddrinfo", _public_dns)

    def _raise(*_args, **_kwargs):
        raise requests.Timeout("timed out")

    monkeypatch.setattr("psg.validation.online.requests.head", _raise)
    assert validate_url("https://example.com") is False


def test_validate_url_uses_cache(monkeypatch) -> None:
    monkeypatch.setattr("psg.validation.online.socket.getaddrinfo", _public_dns)
    calls = {"n": 0}

    def _head(*_args, **_kwargs):
        calls["n"] += 1
        return _Resp(200)

    monkeypatch.setattr("psg.validation.online.requests.head", _head)
    assert validate_url("https://example.com") is True
    assert validate_url("https://example.com") is True
    assert calls["n"] == 1


def test_validate_doi_returns_true_for_200(monkeypatch) -> None:
    monkeypatch.setattr(
        "psg.validation.online.requests.get", lambda *_args, **_kwargs: _Resp(200)
    )
    assert validate_doi("10.1000/xyz123") is True


def test_validate_doi_returns_false_on_request_error(monkeypatch) -> None:
    def _raise(*_args, **_kwargs):
        raise requests.RequestException("down")

    monkeypatch.setattr("psg.validation.online.requests.get", _raise)
    assert validate_doi("10.1000/xyz123") is False


def test_validate_doi_encodes_identifier(monkeypatch) -> None:
    seen = {"url": ""}

    def _get(url, *_args, **_kwargs):
        seen["url"] = url
        return _Resp(200)

    monkeypatch.setattr("psg.validation.online.requests.get", _get)
    assert validate_doi("10.1000/foo/bar") is True
    assert seen["url"].endswith("10.1000%2Ffoo%2Fbar")


def test_validate_url_blocks_non_http_schemes(monkeypatch) -> None:
    called = {"n": 0}

    def _head(*_args, **_kwargs):
        called["n"] += 1
        return _Resp(200)

    monkeypatch.setattr("psg.validation.online.requests.head", _head)
    assert validate_url("file:///etc/passwd") is False
    assert called["n"] == 0


def test_validate_url_blocks_private_ip(monkeypatch) -> None:
    called = {"n": 0}

    def _head(*_args, **_kwargs):
        called["n"] += 1
        return _Resp(200)

    monkeypatch.setattr("psg.validation.online.requests.head", _head)
    assert validate_url("http://127.0.0.1:8080") is False
    assert called["n"] == 0


def test_validate_url_blocks_if_dns_resolves_private(monkeypatch) -> None:
    monkeypatch.setattr(
        "psg.validation.online.socket.getaddrinfo",
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
    monkeypatch.setattr(
        "psg.validation.online.requests.head", lambda *_args, **_kwargs: _Resp(200)
    )
    assert validate_url("https://mixed.example") is False


def test_validate_url_allowlist_restricts_hosts(monkeypatch) -> None:
    monkeypatch.setattr("psg.validation.online.socket.getaddrinfo", _public_dns)
    monkeypatch.setattr(
        "psg.validation.online.requests.head", lambda *_args, **_kwargs: _Resp(200)
    )

    assert validate_url("https://example.com", allowlist=("example.com",)) is True
    assert validate_url("https://not-example.com", allowlist=("example.com",)) is False


def test_validate_url_rate_limit_blocks_after_burst(monkeypatch) -> None:
    monkeypatch.setattr("psg.validation.online.socket.getaddrinfo", _public_dns)
    monkeypatch.setattr(
        "psg.validation.online.requests.head", lambda *_args, **_kwargs: _Resp(200)
    )

    results = [
        validate_url(f"https://example.com/{i}", max_requests_per_second=10.0)
        for i in range(11)
    ]
    assert results.count(True) == 10
    assert results.count(False) == 1


def test_validate_doi_rate_limit_blocks_after_burst(monkeypatch) -> None:
    monkeypatch.setattr(
        "psg.validation.online.requests.get", lambda *_args, **_kwargs: _Resp(200)
    )

    results = [
        validate_doi(f"10.1000/xyz{i}", max_requests_per_second=10.0) for i in range(11)
    ]
    assert results.count(True) == 10
    assert results.count(False) == 1
