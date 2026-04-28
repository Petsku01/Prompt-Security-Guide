from __future__ import annotations

import pytest

from psg.errors import CatalogError, ClassifierError
from psg.llm.errors import LLMError
from psg.models import AppConfig, Attack, ClassificationInputMode, LLMResponse
from psg.orchestrator import run
from psg.security.classifier import ClassificationResult


class _FakeCheckpoint:
    def __init__(self, _path: str) -> None:
        self.rows = []

    def append(self, record):
        self.rows.append(record)


class _FakeClient:
    def __init__(self, *_args, **_kwargs) -> None:
        self.calls = 0

    def chat(self, **_kwargs):
        self.calls += 1
        return LLMResponse(content="safe", raw={})


class _Detector:
    def __init__(self, classify_fn) -> None:
        self._classify_fn = classify_fn

    def classify(self, prompt: str, response: str):
        return self._classify_fn(prompt, response)


def _cfg(tmp_path) -> AppConfig:
    return AppConfig(
        model="test-model",
        catalog_path=str(tmp_path / "catalog.json"),
        allow_insecure_http=True,
        checkpoint_path=str(tmp_path / "checkpoint.jsonl"),
        report_json_path=str(tmp_path / "report.json"),
        report_text_path=str(tmp_path / "report.txt"),
    )


def test_run_success_path(monkeypatch, tmp_path) -> None:
    cfg = _cfg(tmp_path)
    attacks = [Attack(id="a1", prompt="p1"), Attack(id="a2", prompt="p2")]

    monkeypatch.setattr("psg.orchestrator.load_catalog", lambda _p: attacks)
    monkeypatch.setattr("psg.orchestrator.OpenAICompatibleClient", _FakeClient)
    monkeypatch.setattr("psg.orchestrator.JSONLCheckpoint", _FakeCheckpoint)
    monkeypatch.setattr(
        "psg.orchestrator.redact_text",
        lambda text, _mode: text.replace("p", "[REDACTED]"),
    )
    monkeypatch.setattr(
        "psg.orchestrator.build_detector",
        lambda _cfg: _Detector(
            lambda _prompt, _response: ClassificationResult(
                is_refusal=False,
                is_harmful=True,
                attack_successful=True,
                harm_score=0.9,
                refusal_confidence=0.0,
                harmful_labels=["malware_code"],
                compliance_detected=True,
                has_disclaimer=False,
                raw_text_length=4,
            )
        ),
    )
    monkeypatch.setattr(
        "psg.orchestrator.write_json_report", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "psg.orchestrator.write_text_report", lambda *_args, **_kwargs: None
    )

    summary, results = run(cfg)

    assert summary.total == 2
    assert summary.failed == 0
    assert summary.flagged == 2
    assert len(results) == 2
    assert results[0].prompt == "[REDACTED]1"


def test_run_continues_on_partial_failures(monkeypatch, tmp_path) -> None:
    cfg = _cfg(tmp_path)
    attacks = [
        Attack(id="a1", prompt="p1"),
        Attack(id="a2", prompt="p2"),
        Attack(id="a3", prompt="p3"),
    ]

    calls = {"n": 0}

    class _ClientMixed(_FakeClient):
        def chat(self, **_kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise LLMError("llm down")
            if calls["n"] == 2:
                return LLMResponse(content="x", raw={})
            return LLMResponse(content="y", raw={})

    monkeypatch.setattr("psg.orchestrator.load_catalog", lambda _p: attacks)
    monkeypatch.setattr("psg.orchestrator.OpenAICompatibleClient", _ClientMixed)
    monkeypatch.setattr("psg.orchestrator.JSONLCheckpoint", _FakeCheckpoint)
    monkeypatch.setattr("psg.orchestrator.redact_text", lambda text, _mode: text)

    def _classify(_prompt: str, response: str):
        if response == "x":
            raise ClassifierError("bad classify")
        return ClassificationResult(
            is_refusal=False,
            is_harmful=False,
            attack_successful=False,
            harm_score=0.0,
            refusal_confidence=0.0,
            harmful_labels=[],
            compliance_detected=False,
            has_disclaimer=False,
            raw_text_length=1,
        )

    monkeypatch.setattr(
        "psg.orchestrator.build_detector", lambda _cfg: _Detector(_classify)
    )
    monkeypatch.setattr(
        "psg.orchestrator.write_json_report", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "psg.orchestrator.write_text_report", lambda *_args, **_kwargs: None
    )

    summary, results = run(cfg)

    assert summary.total == 3
    assert summary.failed == 2
    assert summary.succeeded == 1
    assert len(results) == 3
    assert sum(1 for r in results if r.error) == 2


def test_run_raises_catalog_error(monkeypatch, tmp_path) -> None:
    cfg = _cfg(tmp_path)
    monkeypatch.setattr(
        "psg.orchestrator.load_catalog",
        lambda _p: (_ for _ in ()).throw(ValueError("bad")),
    )

    with pytest.raises(CatalogError):
        run(cfg)


def test_run_returns_partial_results_on_report_failure(monkeypatch, tmp_path) -> None:
    cfg = _cfg(tmp_path)
    monkeypatch.setattr(
        "psg.orchestrator.load_catalog", lambda _p: [Attack(id="a", prompt="p")]
    )
    monkeypatch.setattr("psg.orchestrator.OpenAICompatibleClient", _FakeClient)
    monkeypatch.setattr("psg.orchestrator.JSONLCheckpoint", _FakeCheckpoint)
    monkeypatch.setattr("psg.orchestrator.redact_text", lambda text, _mode: text)
    monkeypatch.setattr(
        "psg.orchestrator.build_detector",
        lambda _cfg: _Detector(
            lambda _prompt, _response: ClassificationResult(
                is_refusal=False,
                is_harmful=False,
                attack_successful=False,
                harm_score=0.0,
                refusal_confidence=0.0,
                harmful_labels=[],
                compliance_detected=False,
                has_disclaimer=False,
                raw_text_length=1,
            )
        ),
    )
    monkeypatch.setattr(
        "psg.orchestrator.write_json_report", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "psg.orchestrator.write_text_report",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk full")),
    )

    summary, results = run(cfg)

    assert summary.total == 1
    assert summary.report_write_failed is True
    assert len(results) == 1


def test_run_classifies_with_unredacted_response(monkeypatch, tmp_path) -> None:
    cfg = _cfg(tmp_path)
    attacks = [Attack(id="a1", prompt="p1")]
    observed = {"response": None}
    raw_response = "sk-ABCDEFGHIJKLMNOP"

    class _ClientRaw(_FakeClient):
        def chat(self, **_kwargs):
            return LLMResponse(content=raw_response, raw={})

    def _classify(_prompt: str, response: str):
        observed["response"] = response
        return ClassificationResult(
            is_refusal=False,
            is_harmful=True,
            attack_successful=True,
            harm_score=0.9,
            refusal_confidence=0.0,
            harmful_labels=["credential_leak"],
            compliance_detected=True,
            has_disclaimer=False,
            raw_text_length=len(response),
        )

    monkeypatch.setattr("psg.orchestrator.load_catalog", lambda _p: attacks)
    monkeypatch.setattr("psg.orchestrator.OpenAICompatibleClient", _ClientRaw)
    monkeypatch.setattr("psg.orchestrator.JSONLCheckpoint", _FakeCheckpoint)
    monkeypatch.setattr(
        "psg.orchestrator.build_detector", lambda _cfg: _Detector(_classify)
    )
    monkeypatch.setattr(
        "psg.orchestrator.write_json_report", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "psg.orchestrator.write_text_report", lambda *_args, **_kwargs: None
    )

    summary, results = run(cfg)

    assert summary.flagged == 1
    assert observed["response"] == raw_response
    assert results[0].response_text != raw_response


def test_run_auto_mode_uses_redacted_response_for_llm_judge(
    monkeypatch, tmp_path
) -> None:
    cfg = _cfg(tmp_path)
    cfg.detector = "llm-judge"
    attacks = [Attack(id="a1", prompt="p1")]
    observed = {"response": None}
    raw_response = "sk-ABCDEFGHIJKLMNOP"

    class _ClientRaw(_FakeClient):
        def chat(self, **_kwargs):
            return LLMResponse(content=raw_response, raw={})

    def _classify(_prompt: str, response: str):
        observed["response"] = response
        return ClassificationResult(
            is_refusal=False,
            is_harmful=True,
            attack_successful=True,
            harm_score=0.9,
            refusal_confidence=0.0,
            harmful_labels=["credential_leak"],
            compliance_detected=True,
            has_disclaimer=False,
            raw_text_length=len(response),
        )

    monkeypatch.setattr("psg.orchestrator.load_catalog", lambda _p: attacks)
    monkeypatch.setattr("psg.orchestrator.OpenAICompatibleClient", _ClientRaw)
    monkeypatch.setattr("psg.orchestrator.JSONLCheckpoint", _FakeCheckpoint)
    monkeypatch.setattr(
        "psg.orchestrator.build_detector", lambda _cfg: _Detector(_classify)
    )
    monkeypatch.setattr(
        "psg.orchestrator.write_json_report", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "psg.orchestrator.write_text_report", lambda *_args, **_kwargs: None
    )

    summary, _ = run(cfg)

    assert summary.flagged == 1
    assert observed["response"] != raw_response
    assert "[REDACTED_KEY]" in observed["response"]


def test_run_classification_input_both_merges_results(monkeypatch, tmp_path) -> None:
    cfg = _cfg(tmp_path)
    cfg.classification_input_mode = ClassificationInputMode.BOTH
    attacks = [Attack(id="a1", prompt="p1")]
    raw_response = "How to do malware with sk-ABCDEFGHIJKLMNOP"
    observed: list[str] = []

    class _ClientRaw(_FakeClient):
        def chat(self, **_kwargs):
            return LLMResponse(content=raw_response, raw={})

    def _classify(_prompt: str, response: str):
        observed.append(response)
        if "sk-" in response:
            return ClassificationResult(
                is_refusal=False,
                is_harmful=True,
                attack_successful=True,
                harm_score=0.8,
                refusal_confidence=0.1,
                harmful_labels=["credential_leak"],
                compliance_detected=True,
                has_disclaimer=False,
                raw_text_length=len(response),
            )
        return ClassificationResult(
            is_refusal=True,
            is_harmful=False,
            attack_successful=False,
            harm_score=0.0,
            refusal_confidence=0.7,
            harmful_labels=["redaction_observed"],
            compliance_detected=False,
            has_disclaimer=True,
            raw_text_length=len(response),
        )

    monkeypatch.setattr("psg.orchestrator.load_catalog", lambda _p: attacks)
    monkeypatch.setattr("psg.orchestrator.OpenAICompatibleClient", _ClientRaw)
    monkeypatch.setattr("psg.orchestrator.JSONLCheckpoint", _FakeCheckpoint)
    monkeypatch.setattr(
        "psg.orchestrator.build_detector", lambda _cfg: _Detector(_classify)
    )
    monkeypatch.setattr(
        "psg.orchestrator.write_json_report", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "psg.orchestrator.write_text_report", lambda *_args, **_kwargs: None
    )

    summary, results = run(cfg)

    assert summary.flagged == 1
    assert len(observed) == 2
    assert any("sk-" in r for r in observed)
    assert any("[REDACTED_KEY]" in r for r in observed)
    assert results[0].labels == ["credential_leak", "redaction_observed"]
    assert results[0].is_refusal is False
    assert results[0].has_disclaimer is True


def test_run_parallel_workers(monkeypatch, tmp_path) -> None:
    """Test that parallel workers process attacks correctly."""
    cfg = _cfg(tmp_path)
    cfg.workers = 4  # Enable parallel execution
    attacks = [Attack(id=f"a{i}", prompt=f"p{i}") for i in range(10)]

    monkeypatch.setattr("psg.orchestrator.load_catalog", lambda _: attacks)
    monkeypatch.setattr("psg.orchestrator.Transport", lambda **_: None)
    monkeypatch.setattr("psg.orchestrator.OpenAICompatibleClient", _FakeClient)
    monkeypatch.setattr("psg.orchestrator.JSONLCheckpoint", _FakeCheckpoint)
    monkeypatch.setattr(
        "psg.orchestrator.build_detector",
        lambda _: _Detector(
            lambda _prompt, _response: ClassificationResult(
                is_refusal=False,
                is_harmful=False,
                attack_successful=False,
                harm_score=0.1,
                refusal_confidence=0.0,
                harmful_labels=[],
                compliance_detected=False,
                has_disclaimer=False,
                raw_text_length=4,
            )
        ),
    )

    summary, results = run(cfg)

    assert summary.total == 10
    assert summary.succeeded == 10
    assert summary.failed == 0
    assert len(results) == 10
    # Check order is preserved
    assert [r.attack_id for r in results] == [f"a{i}" for i in range(10)]


def test_run_parallel_actually_concurrent(monkeypatch, tmp_path) -> None:
    """Test that parallel workers actually run concurrently."""
    import threading
    import time

    cfg = _cfg(tmp_path)
    cfg.workers = 4
    attacks = [Attack(id=f"a{i}", prompt=f"p{i}") for i in range(4)]

    # Track concurrent executions
    concurrent_count = 0
    max_concurrent = 0
    lock = threading.Lock()

    class _SlowClient:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def chat(self, **_kwargs):
            nonlocal concurrent_count, max_concurrent
            with lock:
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)
            time.sleep(0.1)  # Simulate slow API call
            with lock:
                concurrent_count -= 1
            return LLMResponse(content="safe", raw={})

    monkeypatch.setattr("psg.orchestrator.load_catalog", lambda _: attacks)
    monkeypatch.setattr("psg.orchestrator.Transport", lambda **_: None)
    monkeypatch.setattr("psg.orchestrator.OpenAICompatibleClient", _SlowClient)
    monkeypatch.setattr("psg.orchestrator.JSONLCheckpoint", _FakeCheckpoint)
    monkeypatch.setattr(
        "psg.orchestrator.build_detector",
        lambda _: _Detector(
            lambda _prompt, _response: ClassificationResult(
                is_refusal=False,
                is_harmful=False,
                attack_successful=False,
                harm_score=0.1,
                refusal_confidence=0.0,
                harmful_labels=[],
                compliance_detected=False,
                has_disclaimer=False,
                raw_text_length=4,
            )
        ),
    )

    start = time.perf_counter()
    summary, results = run(cfg)
    elapsed = time.perf_counter() - start

    # With 4 workers and 4 tasks of 0.1s each, should complete in ~0.1-0.2s
    # Sequential would take ~0.4s
    assert elapsed < 0.35, f"Expected parallel execution, took {elapsed:.2f}s"
    assert max_concurrent > 1, (
        f"Expected concurrent execution, max concurrent was {max_concurrent}"
    )
    assert summary.total == 4


def test_rate_limiter_limits_requests(monkeypatch, tmp_path) -> None:
    """Test that rate limiting actually limits request rate."""
    import time

    cfg = _cfg(tmp_path)
    cfg.workers = 4
    cfg.rate_limit = 10.0  # 10 requests per second = 0.1s between requests
    attacks = [Attack(id=f"a{i}", prompt=f"p{i}") for i in range(5)]

    request_times = []

    class _TimingClient:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def chat(self, **_kwargs):
            request_times.append(time.perf_counter())
            return LLMResponse(content="safe", raw={})

    monkeypatch.setattr("psg.orchestrator.load_catalog", lambda _: attacks)
    monkeypatch.setattr("psg.orchestrator.Transport", lambda **_: None)
    monkeypatch.setattr("psg.orchestrator.OpenAICompatibleClient", _TimingClient)
    monkeypatch.setattr("psg.orchestrator.JSONLCheckpoint", _FakeCheckpoint)
    monkeypatch.setattr(
        "psg.orchestrator.build_detector",
        lambda _: _Detector(
            lambda _prompt, _response: ClassificationResult(
                is_refusal=False,
                is_harmful=False,
                attack_successful=False,
                harm_score=0.1,
                refusal_confidence=0.0,
                harmful_labels=[],
                compliance_detected=False,
                has_disclaimer=False,
                raw_text_length=4,
            )
        ),
    )

    run(cfg)

    # Check that requests are spaced by at least ~0.08s (allowing some tolerance)
    assert len(request_times) == 5
    for i in range(1, len(request_times)):
        interval = request_times[i] - request_times[i - 1]
        assert interval >= 0.08, f"Request interval {interval:.3f}s is below rate limit"
