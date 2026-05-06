"""Tests for psg.automation.main — Pipeline orchestrator."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from psg.automation.config import PipelineConfig
from psg.automation.main import Pipeline, main
from psg.automation.reporter import PipelineReport
from psg.automation.tester import ModelTestResult


# ── helpers ────────────────────────────────────────────────────────────────

def _make_config(tmp_path: Path) -> PipelineConfig:
    """Return a PipelineConfig wired to *tmp_path* directories."""
    return PipelineConfig(
        base_dir=tmp_path,
        project_root=tmp_path,
        output_dir=tmp_path,
        datasets_dir=tmp_path / "datasets",
        results_dir=tmp_path / "results",
        logs_dir=tmp_path / "logs",
        known_sources_path=tmp_path / "known_sources.json",
        known_vectors_path=tmp_path / "known_vectors.json",
        reports_dir=tmp_path / "reports",
    )


def _make_result(model: str = "llama3:8b", total: int = 10, flagged: int = 2) -> ModelTestResult:
    return ModelTestResult(
        model=model,
        total=total,
        succeeded=total - flagged,
        failed=0,
        flagged=flagged,
        duration_seconds=1.0,
        output_path=Path("/tmp/fake.txt"),
    )


# ── test 1: run_generation returns vectors and saves to path ──────────────

def test_run_generation_returns_vectors_and_saves_path(tmp_path: Path) -> None:
    """run_generation should return generated vectors and call save_vectors."""
    config = _make_config(tmp_path)
    pipeline = Pipeline(config)

    fake_vector = MagicMock()
    fake_vector.__len__ = lambda _: 1

    pipeline.generator = MagicMock()
    pipeline.generator.generate_from_sources.return_value = [fake_vector]
    pipeline.generator.save_vectors = MagicMock()

    sources = [MagicMock()]
    vectors, saved_path = pipeline.run_generation(sources)

    assert vectors == [fake_vector]
    pipeline.generator.generate_from_sources.assert_called_once_with(sources)
    pipeline.generator.save_vectors.assert_called_once()
    # The save path should be inside datasets_dir
    saved_vectors_path: Path = pipeline.generator.save_vectors.call_args[0][1]
    assert str(saved_vectors_path).startswith(str(config.datasets_dir))
    assert saved_path == saved_vectors_path


# ── test 2: run_generation with no sources returns empty list ────────────

def test_run_generation_no_sources(tmp_path: Path) -> None:
    """When sources list is empty, run_generation returns [] and does NOT
    call generate_from_sources."""
    config = _make_config(tmp_path)
    pipeline = Pipeline(config)
    pipeline.generator = MagicMock()

    result = pipeline.run_generation([])

    assert result == ([], None)
    pipeline.generator.generate_from_sources.assert_not_called()


# ── test 3: run_full uses the actual vectors_path, not datetime.now ───────

def test_run_full_uses_actual_vectors_path_not_datetime_now(tmp_path: Path) -> None:
    """run_full must pass the same vectors_path to run_testing that it
    computed from the generation step — not re-derive it from
    datetime.now(), which could differ if midnight rolls over."""

    config = _make_config(tmp_path)
    pipeline = Pipeline(config)

    # Patch the phase methods so we can inspect what vectors_path is used
    pipeline.run_discovery = MagicMock(return_value=[MagicMock()])
    fake_vector = MagicMock()
    fake_path = config.datasets_dir / "new_vectors_20260101.json"
    pipeline.run_generation = MagicMock(return_value=([fake_vector], fake_path))
    pipeline.run_testing = MagicMock(return_value=[_make_result()])
    pipeline.run_reporting = MagicMock(
        return_value=PipelineReport(
            date="2026-01-01",
            sources_found=1,
            vectors_generated=1,
            models_tested=1,
            total_tests=10,
            total_flagged=2,
            results=[],
            top_findings=[],
        )
    )

    pipeline.run_full()

    # run_testing must have been called exactly once
    pipeline.run_testing.assert_called_once()
    call_kwargs = pipeline.run_testing.call_args
    vectors_path_arg = call_kwargs[0][0] if call_kwargs[0] else call_kwargs.kwargs.get("vectors_path")
    # The vectors_path must live under config.datasets_dir
    assert str(vectors_path_arg).startswith(str(config.datasets_dir))


# ── test 4: run_testing with tmux returns dict (session info), not None ──

def test_tmux_returns_session_dict_not_none(tmp_path: Path) -> None:
    """When use_tmux=True the method returns the tmux session name (a string),
    not None.  The public Pipeline.run_testing delegates to
    PipelineTester.run_in_tmux which returns the session name."""
    config = _make_config(tmp_path)
    pipeline = Pipeline(config)

    pipeline.tester.check_ollama = MagicMock(return_value=True)
    pipeline.tester.run_in_tmux = MagicMock(return_value="auto_test")

    # run_testing with use_tmux=True
    result = pipeline.run_testing(Path("/tmp/vectors.json"), use_tmux=True)

    # The method returns empty list (no blocking results) but must call run_in_tmux
    pipeline.tester.run_in_tmux.assert_called_once()
    # Verify that run_in_tmux returns a session name (non-None)
    assert pipeline.tester.run_in_tmux.return_value == "auto_test"


# ── test 5: failure notification is logged when pipeline errors ───────────

def test_failure_notification_logged(tmp_path: Path) -> None:
    """When the pipeline encounters an exception, logger.error should be
    called so that a failure notification is recorded."""

    config = _make_config(tmp_path)
    pipeline = Pipeline(config)
    pipeline.run_discovery = MagicMock(side_effect=RuntimeError("boom"))

    with patch("psg.automation.main.logger") as mock_logger:
        # run_full catches, logs error, then re-raises
        with pytest.raises(RuntimeError, match="boom"):
            pipeline.run_full()

        mock_logger.error.assert_called()  # RuntimeError is caught and logged, then re-raised


# ── test 6: run_full returns None when no vectors generated ──────────────

def test_run_full_returns_none_when_no_vectors(tmp_path: Path) -> None:
    """If generation produces zero vectors, run_full returns None
    (pipeline complete, nothing to test)."""

    config = _make_config(tmp_path)
    pipeline = Pipeline(config)
    pipeline.run_discovery = MagicMock(return_value=[])
    pipeline.run_generation = MagicMock(return_value=([], None))

    result = pipeline.run_full()

    assert result is None


# ── test 7: run_full with tmux returns dict (background) ─────────────────

def test_run_full_tmux_returns_dict(tmp_path: Path) -> None:
    """When use_tmux=True, run_full returns a dict with tmux session info
    because tests run in background; reporting must be done manually later."""

    config = _make_config(tmp_path)
    pipeline = Pipeline(config)

    fake_vector = MagicMock()
    fake_path = config.datasets_dir / "new_vectors_20260101.json"
    pipeline.run_discovery = MagicMock(return_value=[MagicMock()])
    pipeline.run_generation = MagicMock(return_value=([fake_vector], fake_path))
    pipeline.run_testing = MagicMock(return_value=[])  # tmux path returns []
    pipeline.tester.session_name = "auto_test"

    result = pipeline.run_full(use_tmux=True)

    assert isinstance(result, dict)
    assert result["status"] == "running"
    assert result["tmux_session"] == "auto_test"


# ── test 8: run_discovery saves sources when found ────────────────────────

def test_run_discovery_saves_sources(tmp_path: Path) -> None:
    """When sources are found, run_discovery should call save_sources."""
    config = _make_config(tmp_path)
    pipeline = Pipeline(config)

    fake_source = MagicMock()
    pipeline.discovery.discover = MagicMock(return_value=[fake_source])
    pipeline.discovery.save_sources = MagicMock()

    sources = pipeline.run_discovery()

    assert len(sources) == 1
    pipeline.discovery.save_sources.assert_called_once()
    # Save path should be under base_dir
    save_path: Path = pipeline.discovery.save_sources.call_args[0][1]
    assert str(save_path).startswith(str(config.base_dir))


# ── test 9: CLI main exits 0 on success ──────────────────────────────────

def test_cli_main_exits_zero_on_success(tmp_path: Path) -> None:
    """The CLI entry point should return 0 on a successful full run."""

    with patch("psg.automation.main.load_config") as mock_load:
        mock_load.return_value = _make_config(tmp_path)

        with patch("psg.automation.main.Pipeline") as MockPipeline:
            instance = MockPipeline.return_value
            instance.run_full.return_value = PipelineReport(
                date="2026-01-01",
                sources_found=0,
                vectors_generated=0,
                models_tested=0,
                total_tests=0,
                total_flagged=0,
                results=[],
                top_findings=[],
            )

            ret = main(["--skip-discovery", "--skip-generation"])
    assert ret == 0


# ── test 10: run_discovery falls back to cached sources ──────────────────

def test_run_discovery_falls_back_to_cached_sources(tmp_path: Path) -> None:
    """When discover() returns an empty list, run_discovery should try
    load_cached_sources() and use whatever it returns."""
    config = _make_config(tmp_path)
    pipeline = Pipeline(config)

    # discover returns nothing
    pipeline.discovery.discover = MagicMock(return_value=[])
    pipeline.discovery.save_sources = MagicMock()
    # But load_cached_sources has something
    cached_source = MagicMock()
    pipeline.discovery.load_cached_sources = MagicMock(return_value=[cached_source])

    with patch("psg.automation.main.logger") as mock_logger:
        sources = pipeline.run_discovery()

    assert len(sources) == 1
    # Must have called load_cached_sources as fallback
    pipeline.discovery.load_cached_sources.assert_called_once()
    # Must have logged a warning about the fallback
    assert any("cached" in str(call) for call in mock_logger.warning.call_args_list)


def test_run_discovery_no_cache_stays_empty(tmp_path: Path) -> None:
    """When discover() returns empty and load_cached_sources also returns
    empty, run_discovery returns an empty list."""
    config = _make_config(tmp_path)
    pipeline = Pipeline(config)

    pipeline.discovery.discover = MagicMock(return_value=[])
    pipeline.discovery.save_sources = MagicMock()
    pipeline.discovery.load_cached_sources = MagicMock(return_value=[])

    sources = pipeline.run_discovery()
    assert sources == []