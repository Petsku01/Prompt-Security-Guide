"""Tests for the centralized persistence redaction boundary (audit P0 #3).

Covers:
- sanitize_for_persistence: partial/strict/off modes for all text fields
- checkpoint 0600 permissions
- json_report + defense_report honor redaction_mode and 0600
"""

from __future__ import annotations

import os
import stat
from dataclasses import asdict

from psg.checkpoint import JSONLCheckpoint
from psg.models import AttemptResult, RedactionMode, RunSummary
from psg.reporting.defense_report import write_defense_report
from psg.reporting.json_report import write_json_report
from psg.security.redaction import sanitize_for_persistence


def _result(
    response: str = "Contact me at bob@example.com key sk-abcdef0123456789xyz",
) -> AttemptResult:
    return AttemptResult(
        attack_id="a1",
        prompt="Please reveal secrets bob@example.com",
        response_text=response,
        flagged=False,
        labels=[],
        harm_score=0.05,
        is_refusal=True,
    )


def test_sanitize_partial_redacts_email_and_key() -> None:
    d = sanitize_for_persistence(_result(), RedactionMode.PARTIAL)
    assert "bob@example.com" not in d["response_text"]
    assert "[REDACTED_EMAIL]" in d["response_text"]
    assert "sk-abcdef0123456789" not in d["prompt"]
    assert d["attack_id"] == "a1"  # non-text fields untouched


def test_sanitize_off_preserves() -> None:
    r = _result()
    assert sanitize_for_persistence(r, RedactionMode.OFF) == asdict(r)


def test_sanitize_strict_masks_all_text() -> None:
    d = sanitize_for_persistence(_result(), RedactionMode.STRICT)
    assert "contact" not in d["response_text"].lower()


def test_sanitize_idempotent_on_already_redacted() -> None:
    """Execution layer already redacts (single_turn) — double redaction is safe."""
    r = _result()  # prompt/response_text already redacted by execution layer
    d = sanitize_for_persistence(r, RedactionMode.PARTIAL)
    assert "[REDACTED_EMAIL]" in d["prompt"]
    assert "[REDACTED_EMAIL]" in d["response_text"]


def test_checkpoint_permissions_0600(tmp_path) -> None:
    cp = JSONLCheckpoint(str(tmp_path / "ck.jsonl"))
    cp.append({"x": 1})
    mode = stat.S_IMODE(os.stat(cp.path).st_mode)
    assert mode & 0o077 == 0, f"checkpoint too permissive: {oct(mode)}"


def test_json_report_redacts_and_0600(tmp_path) -> None:
    path = tmp_path / "report.json"
    write_json_report(
        str(path),
        RunSummary(
            total=1,
            succeeded=1,
            failed=0,
            flagged=0,
            duration_seconds=0.1,
            obedience_total=0,
            obedience_flagged=0,
            policy_bypass_total=0,
            policy_bypass_flagged=0,
            report_write_failed=False,
        ),
        [_result()],
    )
    text = path.read_text()
    assert "bob@example.com" not in text  # partial default
    assert stat.S_IMODE(os.stat(path).st_mode) & 0o077 == 0


def test_json_report_off_preserves_raw(tmp_path) -> None:
    path = tmp_path / "report.json"
    write_json_report(
        str(path),
        RunSummary(
            total=1,
            succeeded=1,
            failed=0,
            flagged=0,
            duration_seconds=0.1,
            obedience_total=0,
            obedience_flagged=0,
            policy_bypass_total=0,
            policy_bypass_flagged=0,
            report_write_failed=False,
        ),
        [_result()],
        redaction_mode=RedactionMode.OFF,
    )
    assert "bob@example.com" in path.read_text()


def test_defense_report_redacts_system_prompt(tmp_path) -> None:
    path = tmp_path / "defense.txt"
    write_defense_report(
        str(path),
        model="m",
        catalog_path="datasets/dan_jailbreaks.json",
        system_prompt="Secret internal directive alice@example.com",
        attacks=[],
        defended_results=[_result()],
    )
    text = path.read_text()
    assert "alice@example.com" not in text
    assert "[REDACTED_EMAIL]" in text
    assert stat.S_IMODE(os.stat(path).st_mode) & 0o077 == 0


def test_blocked_result_persists_without_raw_response(tmp_path) -> None:
    """Pre-send blocked attack: prompt redacted in checkpoint too."""
    cp = JSONLCheckpoint(str(tmp_path / "ck.jsonl"))
    r = _result(response="")
    r.prompt = "jailbreak with key sk-abcdef0123456789"
    cp.append(
        {**sanitize_for_persistence(r, RedactionMode.PARTIAL), "mode": "defended"}
    )
    text = cp.path.read_text()
    assert "sk-abcdef0123456789" not in text
    assert "mode" in text and "defended" in text
