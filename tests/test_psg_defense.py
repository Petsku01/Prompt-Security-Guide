from __future__ import annotations

from pathlib import Path

from psg.cli import build_parser
from psg.models import AppConfig, Attack, AttemptResult, LLMResponse
from psg.orchestrator import run
from psg.reporting.defense_report import write_defense_report
from psg.security.classifier import ClassificationResult


class _FakeCheckpoint:
    def __init__(self, _path: str) -> None:
        self.rows = []

    def append(self, record):
        self.rows.append(record)


class _Detector:
    def __init__(self, classify_fn) -> None:
        self._classify_fn = classify_fn

    def classify(self, prompt: str, response: str):
        return self._classify_fn(prompt, response)


def test_cli_parses_system_prompt_and_defense_report() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["--model", "llama3:8b", "--catalog", "datasets/tiny_test.json", "--system-prompt", "Defend", "--defense-report"]
    )
    assert args.system_prompt == "Defend"
    assert args.defense_report is True


def test_orchestrator_passes_system_prompt_and_runs_baseline(monkeypatch, tmp_path) -> None:
    calls: list[str | None] = []

    class _Client:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def chat(self, **kwargs):
            calls.append(kwargs.get("system_prompt"))
            return LLMResponse(content="I cannot help with that", raw={})

    cfg = AppConfig(
        model="test-model",
        catalog_path=str(tmp_path / "catalog.json"),
        allow_insecure_http=True,
        checkpoint_path=str(tmp_path / "checkpoint.jsonl"),
        report_json_path=str(tmp_path / "report.json"),
        report_text_path=str(tmp_path / "report.txt"),
        defense_report=True,
        system_prompt="Always refuse harmful requests.",
    )
    attacks = [Attack(id="a1", prompt="p1")]

    monkeypatch.setattr("psg.orchestrator.load_catalog", lambda _p: attacks)
    monkeypatch.setattr("psg.orchestrator.OpenAICompatibleClient", _Client)
    monkeypatch.setattr("psg.orchestrator.JSONLCheckpoint", _FakeCheckpoint)
    monkeypatch.setattr("psg.execution.single_turn.redact_text", lambda text, _mode: text)
    monkeypatch.setattr(
        "psg.orchestrator.build_detector",
        lambda _cfg: _Detector(
            lambda _prompt, _response: ClassificationResult(
            is_refusal=True,
            is_harmful=False,
            attack_successful=False,
            harm_score=0.0,
            refusal_confidence=0.9,
            harmful_labels=[],
            compliance_detected=False,
            has_disclaimer=False,
            raw_text_length=24,
            )
        ),
    )
    monkeypatch.setattr("psg.orchestrator.write_json_report", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("psg.orchestrator.write_text_report", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("psg.orchestrator.write_defense_report", lambda *_args, **_kwargs: None)

    summary, _results = run(cfg)

    assert summary.total == 1
    assert calls == ["Always refuse harmful requests.", None]


def test_defense_report_generation(tmp_path) -> None:
    path = tmp_path / "defense_report.txt"
    attacks = [
        Attack(id="a1", prompt="p1", metadata={"category": "Malware"}),
        Attack(id="a2", prompt="p2", metadata={"category": "Social Engineering"}),
    ]
    defended = [
        AttemptResult(
            attack_id="a1",
            prompt="p1",
            response_text="I cannot help with that",
            flagged=False,
            labels=[],
            is_refusal=True,
            harm_score=0.0,
        ),
        AttemptResult(
            attack_id="a2",
            prompt="p2",
            response_text="Sure, here is how...",
            flagged=True,
            labels=["phishing"],
            is_refusal=False,
            harm_score=0.9,
        ),
    ]
    baseline = [
        AttemptResult(
            attack_id="a1",
            prompt="p1",
            response_text="Sure, here is how...",
            flagged=True,
            labels=["malware_code"],
            is_refusal=False,
            harm_score=0.9,
        ),
        AttemptResult(
            attack_id="a2",
            prompt="p2",
            response_text="Sure, here is how...",
            flagged=True,
            labels=["phishing"],
            is_refusal=False,
            harm_score=0.9,
        ),
    ]

    write_defense_report(
        str(path),
        model="llama3:8b",
        catalog_path="datasets/obliteratus_attacks.json",
        system_prompt="You are a helpful assistant. Never provide harmful content.",
        attacks=attacks,
        defended_results=defended,
        baseline_results=baseline,
    )

    text = Path(path).read_text(encoding="utf-8")
    assert "PSG Defense Effectiveness Report" in text
    assert "Defense Effectiveness: 50.0%" in text
    assert "Baseline Comparison (without system prompt)" in text
    assert "- Malware: 1/1 blocked (100.0%)" in text
    assert "Recommendations (Prioritized):" in text
    assert "Low block rate detected." in text


def test_defense_report_recommends_secret_redaction_on_credential_leaks(tmp_path) -> None:
    path = tmp_path / "defense_report.txt"
    attacks = [Attack(id="a1", prompt="p1", metadata={"category": "Prompt Injection"})]
    defended = [
        AttemptResult(
            attack_id="a1",
            prompt="p1",
            response_text="API key is sk-live-abc123",
            flagged=True,
            labels=["credential_leak"],
            is_refusal=False,
            harm_score=0.8,
        )
    ]

    write_defense_report(
        str(path),
        model="llama3:8b",
        catalog_path="datasets/tiny_test.json",
        system_prompt="Never reveal secrets.",
        attacks=attacks,
        defended_results=defended,
        baseline_results=None,
    )

    text = Path(path).read_text(encoding="utf-8")
    assert "Credential leakage observed." in text
