from __future__ import annotations

import json

from psg.compare_runs import compare_reports, main


def test_compare_reports_detects_attack_set_mismatch() -> None:
    left = {"run_metadata": {"attack_set": "core-14", "attack_ids": ["a1", "a2"]}}
    right = {"run_metadata": {"attack_set": "full-61", "attack_ids": ["a1", "a2"]}}
    result = compare_reports(left, right)
    assert result["aligned"] is False
    assert result["reason"] == "attack_set_mismatch"


def test_compare_runs_main_returns_1_for_misaligned_reports(
    tmp_path, capsys
) -> None:
    left_path = tmp_path / "left.json"
    right_path = tmp_path / "right.json"
    left_path.write_text(
        json.dumps({"run_metadata": {"attack_set": "core-14", "attack_ids": ["a1"]}}),
        encoding="utf-8",
    )
    right_path.write_text(
        json.dumps({"run_metadata": {"attack_set": "core-14", "attack_ids": ["a2"]}}),
        encoding="utf-8",
    )

    rc = main(["--left", str(left_path), "--right", str(right_path)])
    captured = capsys.readouterr()

    assert rc == 1
    assert "MISALIGNED" in captured.out
    assert "apples-to-oranges" in captured.err
