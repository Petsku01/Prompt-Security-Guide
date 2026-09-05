"""Tests for psg.benchmark module."""

from __future__ import annotations

from pathlib import Path

import pytest

from psg.attack_sets import AttackSetSizeError
from psg.benchmark import (
    PRESETS,
    BenchmarkResult,
    build_parser,
    find_catalog_path,
    main,
    run_benchmark,
)
from psg.errors import CatalogError
from psg.models import RunSummary


def test_presets_defined() -> None:
    assert "jbb" in PRESETS
    assert "owasp" in PRESETS
    assert "hallucination" in PRESETS
    assert "data-leakage" in PRESETS
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
    for preset in PRESETS:
        assert preset in captured.out
    assert "JailbreakBench" in captured.out


def test_main_missing_args(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["--preset", "jbb"])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert "--model" in captured.err or "required" in captured.err.lower()


def test_build_parser_parses_attack_set() -> None:
    parser = build_parser()
    args = parser.parse_args(["--preset", "jbb", "--model", "m", "--attack-set", "core-14"])
    assert args.attack_set == "core-14"


def test_run_benchmark_full_skips_undersized_catalog_for_attack_set(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    big_catalog = tmp_path / "datasets" / "big.json"
    small_catalog = tmp_path / "datasets" / "small.json"
    big_catalog.parent.mkdir(parents=True)
    big_catalog.write_text(
        '{"attacks": [' + ",".join(
            f'{{"id": "a{i}", "prompt": "prompt {i}"}}' for i in range(61)
        ) + "]}",
        encoding="utf-8",
    )
    small_catalog.write_text(
        '{"attacks": [' + ",".join(
            f'{{"id": "b{i}", "prompt": "prompt {i}"}}' for i in range(3)
        ) + "]}",
        encoding="utf-8",
    )
    monkeypatch.setitem(
        PRESETS,
        "full",
        {
            "name": "Full Suite",
            "description": "All available attack datasets combined",
            "catalogs": ["datasets/big.json", "datasets/small.json"],
        },
    )
    seen_catalogs: list[str] = []
    monkeypatch.setattr("psg.benchmark.validate_config", lambda cfg: None)

    def _fake_run(cfg):
        if cfg.catalog_path == str(small_catalog):
            raise CatalogError(f"failed to load catalog {cfg.catalog_path}: undersized") from AttackSetSizeError(
                "full-61", 61, 3
            )
        seen_catalogs.append(cfg.catalog_path)
        return RunSummary(61, 61, 0, 0, 0.1), []

    monkeypatch.setattr("psg.benchmark.run", _fake_run)

    result = run_benchmark(
        preset="full",
        model="test-model",
        attack_set="full-61",
        base_dir=tmp_path,
        output_dir=str(tmp_path / "results"),
    )

    assert result.total_attacks == 61
    assert seen_catalogs == [str(big_catalog)]
    assert result.catalogs_used == [str(big_catalog)]
    captured = capsys.readouterr()
    assert "Skipping undersized catalog for attack set full-61" in captured.err


def test_run_benchmark_full_preserves_catalog_load_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bad_catalog = tmp_path / "datasets" / "bad.json"
    bad_catalog.parent.mkdir(parents=True)
    bad_catalog.write_text('{"attacks": []}', encoding="utf-8")
    monkeypatch.setitem(
        PRESETS,
        "full",
        {
            "name": "Full Suite",
            "description": "All available attack datasets combined",
            "catalogs": ["datasets/bad.json"],
        },
    )
    monkeypatch.setattr("psg.benchmark.validate_config", lambda cfg: None)
    monkeypatch.setattr(
        "psg.benchmark.run",
        lambda cfg: (_ for _ in ()).throw(
            CatalogError(f"failed to load catalog {cfg.catalog_path}: bad json")
        ),
    )

    with pytest.raises(CatalogError, match="failed to load catalog"):
        run_benchmark(
            preset="full",
            model="test-model",
            attack_set="full-61",
            base_dir=tmp_path,
            output_dir=str(tmp_path / "results"),
        )
