from __future__ import annotations

import pytest

from psg.llm.errors import HTTPStatusError
from psg.llm.transport import RETRY_AFTER_MAX_SECONDS, Transport, _parse_retry_after


class _Resp:
    def __init__(
        self,
        status_code: int,
        body: str = "",
        data: dict | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.text = body
        self._data = data if data is not None else {}
        self.headers = headers or {}

    def json(self) -> dict:
        return self._data


def test_post_json_retries_then_succeeds(monkeypatch) -> None:
    transport = Transport(max_retries=2)
    sleeps: list[int] = []
    calls = {"n": 0}

    def _fake_post(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return _Resp(500, "server down")
        return _Resp(200, data={"ok": True})

    monkeypatch.setattr("psg.llm.transport.requests.post", _fake_post)
    monkeypatch.setattr(Transport, "_sleep", lambda _self, attempt, **_kw: sleeps.append(attempt))

    out = transport.post_json("https://example.test/v1", {"x": 1})

    assert out == {"ok": True}
    assert calls["n"] == 2
    assert sleeps == [1]


def test_backoff_sleep_uses_cap_and_jitter(monkeypatch) -> None:
    transport = Transport(backoff_base_seconds=1.0, backoff_cap_seconds=3.0)
    slept: list[float] = []
    uniform_args: list[tuple[float, float]] = []

    def _fake_uniform(a: float, b: float) -> float:
        uniform_args.append((a, b))
        return 0.25

    monkeypatch.setattr("psg.llm.transport.random.uniform", _fake_uniform)
    monkeypatch.setattr("psg.llm.transport.time.sleep", lambda seconds: slept.append(seconds))

    transport._sleep(attempt=3)

    assert uniform_args == [(0, 0.75)]
    assert slept == [3.25]


def test_post_json_raises_http_status_error_for_4xx(monkeypatch) -> None:
    transport = Transport(max_retries=3)

    monkeypatch.setattr("psg.llm.transport.requests.post", lambda *_args, **_kwargs: _Resp(404, "not found"))
    monkeypatch.setattr(Transport, "_sleep", lambda *_args, **_kwargs: pytest.fail("should not retry 4xx"))

    with pytest.raises(HTTPStatusError) as exc_info:
        transport.post_json("https://example.test/v1", {"x": 1})

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.body


def test_parse_retry_after_seconds() -> None:
    assert _parse_retry_after("5") == 5.0
    assert _parse_retry_after("0") == 0.0


def test_parse_retry_after_caps_excessive_values() -> None:
    assert _parse_retry_after("99999") == RETRY_AFTER_MAX_SECONDS


def test_parse_retry_after_rejects_negative_and_garbage() -> None:
    assert _parse_retry_after("-5") is None
    assert _parse_retry_after("not a number") is None
    assert _parse_retry_after(None) is None
    assert _parse_retry_after("") is None


def test_parse_retry_after_http_date_in_past_returns_zero() -> None:
    # RFC 7231 IMF-fixdate format
    assert _parse_retry_after("Wed, 21 Oct 2015 07:28:00 GMT") == 0.0


def test_post_json_honors_retry_after_on_429(monkeypatch) -> None:
    transport = Transport(max_retries=2)
    sleeps: list[tuple[int, float | None]] = []
    calls = {"n": 0}

    def _fake_post(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return _Resp(429, "rate limited", headers={"Retry-After": "7"})
        return _Resp(200, data={"ok": True})

    monkeypatch.setattr("psg.llm.transport.requests.post", _fake_post)
    monkeypatch.setattr(
        Transport,
        "_sleep",
        lambda _self, attempt, *, retry_after=None: sleeps.append((attempt, retry_after)),
    )

    out = transport.post_json("https://example.test/v1", {"x": 1})

    assert out == {"ok": True}
    assert sleeps == [(1, 7.0)]


def test_sleep_with_retry_after_bypasses_exponential_backoff(monkeypatch) -> None:
    transport = Transport(backoff_base_seconds=10.0, backoff_cap_seconds=20.0)
    slept: list[float] = []

    monkeypatch.setattr("psg.llm.transport.random.uniform", lambda _a, _b: 0.0)
    monkeypatch.setattr("psg.llm.transport.time.sleep", lambda s: slept.append(s))

    transport._sleep(attempt=5, retry_after=3.0)

    # Should sleep ~3s (the server hint), not 20s (the exponential cap).
    assert slept == [3.0]
