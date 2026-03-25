"""Tests for psg.benchmark module."""
from __future__ import annotations

from pathlib import Path

import pytest

from psg.benchmark import PRESETS, BenchmarkResult, find_catalog_path, main


def test_presets_defined() -> None:
    assert "jbb" in PRESETS
    assert "owasp" in PRESETS
    assert "full" in PRESETS
    
    for name, info in PRESETS.items():
        assert "name" in info
        assert "description" in info
        assert "catalogs" in info
        assert len(info["catalogs"]) > 0


def test_find_catalog_path_relative(tmp_path: Path) -> None:
    catalog = tmp_path / "datasets" / "test.json"
    catalog.parent.mkdir(parents=True)
    catalog.write_text("[]")
    
    result = find_catalog_path("datasets/test.json", tmp_path)
    assert result == catalog


def test_find_catalog_path_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        find_catalog_path("nonexistent.json", tmp_path)


def test_benchmark_result_dataclass() -> None:
    result = BenchmarkResult(
        preset="jbb",
        model="test-model",
        total_attacks=100,
        successful_attacks=10,
        blocked_attacks=85,
        failed_attacks=5,
        attack_success_rate=0.1,
        defense_rate=0.85,
        duration_seconds=10.5,
        catalogs_used=["test.json"],
    )
    
    assert result.preset == "jbb"
    assert result.attack_success_rate == 0.1
    assert result.defense_rate == 0.85


def test_main_list_presets(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["--list"])
    
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "jbb" in captured.out
    assert "owasp" in captured.out
    assert "JailbreakBench" in captured.out


def test_main_missing_args(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["--preset", "jbb"])
    
    assert exit_code == 2
    captured = capsys.readouterr()
    assert "--model" in captured.err or "required" in captured.err.lower()
