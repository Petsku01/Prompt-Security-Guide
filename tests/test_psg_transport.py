from __future__ import annotations

import pytest

from psg.llm.errors import HTTPStatusError
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
    monkeypatch.setattr(
        Transport, "_sleep", lambda _self, attempt: sleeps.append(attempt)
    )

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
    monkeypatch.setattr(
        "psg.llm.transport.time.sleep", lambda seconds: slept.append(seconds)
    )

    transport._sleep(attempt=3)

    assert uniform_args == [(0, 0.75)]
    assert slept == [3.25]


def test_post_json_raises_http_status_error_for_4xx(monkeypatch) -> None:
    transport = Transport(max_retries=3)

    monkeypatch.setattr(
        "psg.llm.transport.requests.post",
        lambda *_args, **_kwargs: _Resp(404, "not found"),
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
