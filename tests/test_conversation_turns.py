"""Tests for Phase 4.1 — first-class conversation turns.

Crescendo and many-shot attacks now populate ``AttemptResult.turns`` so
the JSON report preserves the full dialogue instead of flattening the
conversation into a single response string.
"""
from __future__ import annotations

import json
from pathlib import Path

from psg.execution.crescendo import run_crescendo_attack
from psg.execution.many_shot import run_many_shot_attack
from psg.models import AppConfig, Attack, ConversationTurn, LLMResponse, RunSummary
from psg.reporting.json_report import write_json_report
from psg.security.classifier import ClassificationResult


class _StubClient:
    def __init__(self, content: str = "Here's detailed info about the topic."):
        self._content = content
        self.calls: list[list[dict]] = []

    def chat_multi_turn(self, **kwargs):
        self.calls.append(list(kwargs.get("messages") or []))
        return LLMResponse(content=self._content, raw={})


class _StubDetector:
    def __init__(self, successful_on_turn: int | None = None):
        self.count = 0
        self.successful_on_turn = successful_on_turn

    def classify(self, prompt: str, response: str) -> ClassificationResult:
        self.count += 1
        successful = (
            self.successful_on_turn is not None and self.count == self.successful_on_turn
        )
        return ClassificationResult(
            is_refusal=not successful,
            is_harmful=successful,
            attack_successful=successful,
            harm_score=0.9 if successful else 0.1,
            refusal_confidence=0.9 if not successful else 0.0,
            harmful_labels=["malware_code"] if successful else [],
            compliance_detected=successful,
            has_disclaimer=False,
            raw_text_length=len(response),
        )


def _cfg() -> AppConfig:
    return AppConfig(
        model="test-model",
        catalog_path="datasets/tiny_test.json",
        allow_insecure_http=True,
    )


def test_crescendo_result_populates_turns_list() -> None:
    cfg = _cfg()
    attack = Attack(id="c1", prompt="topic")
    # Succeed on turn 3 so we get 3 recorded turns.
    detector = _StubDetector(successful_on_turn=3)
    result = run_crescendo_attack(
        cfg=cfg,
        attack=attack,
        client=_StubClient(),
        detector=detector,
        max_turns=7,
    )

    assert result.attack_mode == "crescendo"
    assert result.turns is not None
    assert len(result.turns) == 3
    assert all(isinstance(t, ConversationTurn) for t in result.turns)
    # Only the last turn is marked successful.
    assert result.turns[-1].attack_successful is True
    assert result.turns[0].attack_successful is False


def test_many_shot_result_populates_single_final_turn() -> None:
    cfg = _cfg()
    attack = Attack(id="m1", prompt="topic")
    result = run_many_shot_attack(
        cfg=cfg,
        attack=attack,
        client=_StubClient(),
        detector=_StubDetector(),
        num_examples=5,
    )

    assert result.attack_mode == "many-shot"
    assert result.turns is not None
    assert len(result.turns) == 1
    # Many-shot records only the final turn (priming examples are omitted
    # because they're deterministic from the attack prompt).
    assert result.turns[0].turn_number == 5  # num_examples primers + 1 final
    assert result.turns[0].user_message == "topic"


def test_conversation_turns_survive_json_round_trip(tmp_path: Path) -> None:
    cfg = _cfg()
    attack = Attack(id="c2", prompt="topic")
    detector = _StubDetector(successful_on_turn=2)
    result = run_crescendo_attack(
        cfg=cfg,
        attack=attack,
        client=_StubClient(),
        detector=detector,
        max_turns=7,
    )

    summary = RunSummary(total=1, succeeded=1, failed=0, flagged=1, duration_seconds=0.1)
    json_path = tmp_path / "report.json"
    write_json_report(str(json_path), summary, [result])

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    dumped = payload["results"][0]
    assert dumped["attack_mode"] == "crescendo"
    assert isinstance(dumped["turns"], list)
    assert len(dumped["turns"]) == 2
    turn = dumped["turns"][0]
    assert "turn_number" in turn
    assert "user_message" in turn
    assert "assistant_response" in turn


def test_single_turn_attack_has_no_turns() -> None:
    """Regression: default (non-crescendo) attacks have turns=None."""
    from psg.execution.single_turn import _process_attack
    from psg.security.redaction import redact_text  # noqa: F401 (needed by _process_attack)

    class _Client:
        def chat(self, **_kwargs):
            return LLMResponse(content="I cannot help with that.", raw={})

    result = _process_attack(
        cfg=_cfg(),
        attack=Attack(id="s1", prompt="hi"),
        client=_Client(),
        detector=_StubDetector(),
        system_prompt=None,
    )
    assert result.attack_mode == "single"
    assert result.turns is None
