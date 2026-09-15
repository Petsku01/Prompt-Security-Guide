from __future__ import annotations

import pytest

from psg.llm.errors import HTTPStatusError, LLMError
from psg.llm.transport import Transport


class _Resp:
    def __init__(
        self, status_code: int, body: str = "", data: dict | None = None
    ) -> None:
        self.status_code = status_code
        self.text = body
        self._data = data if data is not None else {}

    def json(self) -> dict:
        return self._data


class _FakeSession:
    """Shape-compatible with PinnedSession (audit P0-4)."""

    def __init__(self, responder=None) -> None:
        self.posts: list[tuple[str, dict]] = []
        self._responder = responder or (lambda: _Resp(200, data={"ok": True}))

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        return self._responder()


def test_post_json_retries_then_succeeds(monkeypatch) -> None:
    transport = Transport(max_retries=2)
    sleeps: list[int] = []
    calls: dict[str, int] = {"n": 0}

    def _responder():
        calls["n"] += 1
        if calls["n"] == 1:
            return _Resp(500, "server down")
        return _Resp(200, data={"ok": True})

    session = _FakeSession(_responder)
    monkeypatch.setattr(
        "psg.llm.transport.resolve_and_pin", lambda url: (url, session)
    )
    monkeypatch.setattr(
        Transport, "_sleep", lambda _self, attempt: sleeps.append(attempt)
    )

    out = transport.post_json("https://example.test/v1", {"x": 1})

    assert out == {"ok": True}
    assert calls["n"] == 2
    assert sleeps == [1]
    # Audit P0-4: pinned transport must NOT follow redirects
    assert session.posts[0][1]["allow_redirects"] is False


def test_post_json_pins_hostname(monkeypatch) -> None:
    """Audit P0-4: hostname must be replaced by the pinned IP in the URL."""
    transport = Transport(max_retries=0)

    session = _FakeSession()
    captured: list[str] = []

    def _pin(url: str) -> tuple[str, _FakeSession]:
        pinned = url.replace("example.test", "93.184.216.34")
        captured.append(pinned)
        return pinned, session

    monkeypatch.setattr("psg.llm.transport.resolve_and_pin", _pin)

    transport.post_json("https://example.test/v1", {"x": 1})

    assert captured, "resolve_and_pin must be called"
    assert "example.test" not in captured[0], (
        f"hostname must be replaced by pinned IP: {captured[0]}"
    )
    assert "93.184.216.34" in captured[0]


def test_post_json_rejects_cross_host_redirect(monkeypatch) -> None:
    """Audit P0-4: a redirect must not be silently followed."""
    transport = Transport(max_retries=0)

    session = _FakeSession(lambda: _Resp(302, "redirect"))
    monkeypatch.setattr(
        "psg.llm.transport.resolve_and_pin", lambda url: (url, session)
    )

    with pytest.raises(Exception) as exc_info:
        transport.post_json("https://example.test/v1", {"x": 1})
    # Fail-closed outcomes: LLMError (PinnedSession guard) or
    # HTTPStatusError (302 treated as non-2xx because allow_redirects=False
    # surfaces the redirect status to the transport's error path).
    assert type(exc_info.value) in (LLMError, HTTPStatusError)


def test_backoff_sleep_uses_cap_and_jitter(monkeypatch) -> None:
    transport = Transport(backoff_base_seconds=1.0, backoff_cap_seconds=3.0)
    slept: list[float] = []
    uniform_args: list[tuple[float, float]] = []

    def _fake_uniform(a: float, b: float) -> float:
        uniform_args.append((a, b))
        return 0.25

    monkeypatch.setattr("psg.llm.transport.random.uniform", _fake_uniform)
    monkeypatch.setattr(
        "psg.llm.transport.time.sleep", lambda seconds: slept.append(seconds)
    )

    transport._sleep(attempt=3)

    assert uniform_args == [(0, 0.75)]
    assert slept == [3.25]


def test_post_json_raises_http_status_error_for_4xx(monkeypatch) -> None:
    transport = Transport(max_retries=3)

    session = _FakeSession(lambda: _Resp(404, "not found"))
    monkeypatch.setattr(
        "psg.llm.transport.resolve_and_pin", lambda url: (url, session)
    )
    monkeypatch.setattr(
        Transport,
        "_sleep",
        lambda *_args, **_kwargs: pytest.fail("should not retry 4xx"),
    )

    with pytest.raises(HTTPStatusError) as exc_info:
        transport.post_json("https://example.test/v1", {"x": 1})

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.body