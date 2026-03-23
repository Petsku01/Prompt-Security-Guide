from __future__ import annotations

import pytest

from psg.errors import CatalogError, ClassifierError
from psg.llm.errors import LLMError
from psg.models import AppConfig, Attack, LLMResponse
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
    monkeypatch.setattr("psg.orchestrator.redact_text", lambda text, _mode: text)
    monkeypatch.setattr(
        "psg.orchestrator.classify_response_v2",
        lambda _text: ClassificationResult(
            is_refusal=False,
            is_harmful=True,
            attack_successful=True,
            harm_score=0.9,
            refusal_confidence=0.0,
            harmful_labels=["malware_code"],
            compliance_detected=True,
            has_disclaimer=False,
            raw_text_length=4,
        ),
    )
    monkeypatch.setattr("psg.orchestrator.write_json_report", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("psg.orchestrator.write_text_report", lambda *_args, **_kwargs: None)

    summary, results = run(cfg)

    assert summary.total == 2
    assert summary.failed == 0
    assert summary.flagged == 2
    assert len(results) == 2


def test_run_continues_on_partial_failures(monkeypatch, tmp_path) -> None:
    cfg = _cfg(tmp_path)
    attacks = [Attack(id="a1", prompt="p1"), Attack(id="a2", prompt="p2"), Attack(id="a3", prompt="p3")]

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

    def _classify(text: str):
        if text == "x":
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

    monkeypatch.setattr("psg.orchestrator.classify_response_v2", _classify)
    monkeypatch.setattr("psg.orchestrator.write_json_report", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("psg.orchestrator.write_text_report", lambda *_args, **_kwargs: None)

    summary, results = run(cfg)

    assert summary.total == 3
    assert summary.failed == 2
    assert summary.succeeded == 1
    assert len(results) == 3
    assert sum(1 for r in results if r.error) == 2


def test_run_raises_catalog_error(monkeypatch, tmp_path) -> None:
    cfg = _cfg(tmp_path)
    monkeypatch.setattr("psg.orchestrator.load_catalog", lambda _p: (_ for _ in ()).throw(ValueError("bad")))

    with pytest.raises(CatalogError):
        run(cfg)


def test_run_returns_partial_results_on_report_failure(monkeypatch, tmp_path) -> None:
    cfg = _cfg(tmp_path)
    monkeypatch.setattr("psg.orchestrator.load_catalog", lambda _p: [Attack(id="a", prompt="p")])
    monkeypatch.setattr("psg.orchestrator.OpenAICompatibleClient", _FakeClient)
    monkeypatch.setattr("psg.orchestrator.JSONLCheckpoint", _FakeCheckpoint)
    monkeypatch.setattr("psg.orchestrator.redact_text", lambda text, _mode: text)
    monkeypatch.setattr(
        "psg.orchestrator.classify_response_v2",
        lambda _text: ClassificationResult(
            is_refusal=False,
            is_harmful=False,
            attack_successful=False,
            harm_score=0.0,
            refusal_confidence=0.0,
            harmful_labels=[],
            compliance_detected=False,
            has_disclaimer=False,
            raw_text_length=1,
        ),
    )
    monkeypatch.setattr("psg.orchestrator.write_json_report", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "psg.orchestrator.write_text_report",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk full")),
    )

    summary, results = run(cfg)

    assert summary.total == 1
    assert len(results) == 1
