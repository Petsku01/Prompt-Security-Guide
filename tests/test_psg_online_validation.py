from __future__ import annotations

import requests

from psg.validation.online import clear_validation_cache, validate_doi, validate_url


class _Resp:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


def setup_function() -> None:
    clear_validation_cache()


def test_validate_url_returns_true_for_redirect(monkeypatch) -> None:
    monkeypatch.setattr("psg.validation.online.requests.head", lambda *_args, **_kwargs: _Resp(302))
    assert validate_url("https://example.com") is True


def test_validate_url_returns_false_on_timeout(monkeypatch) -> None:
    def _raise(*_args, **_kwargs):
        raise requests.Timeout("timed out")

    monkeypatch.setattr("psg.validation.online.requests.head", _raise)
    assert validate_url("https://example.com") is False


def test_validate_url_uses_cache(monkeypatch) -> None:
    calls = {"n": 0}

    def _head(*_args, **_kwargs):
        calls["n"] += 1
        return _Resp(200)

    monkeypatch.setattr("psg.validation.online.requests.head", _head)
    assert validate_url("https://example.com") is True
    assert validate_url("https://example.com") is True
    assert calls["n"] == 1


def test_validate_doi_returns_true_for_200(monkeypatch) -> None:
    monkeypatch.setattr("psg.validation.online.requests.get", lambda *_args, **_kwargs: _Resp(200))
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
