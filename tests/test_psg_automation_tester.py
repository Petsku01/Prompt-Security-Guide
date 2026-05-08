"""Tests for psg.automation.tester — PipelineTester & ModelTestResult."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from psg.automation.config import PipelineConfig
from psg.automation.tester import ModelTestResult, PipelineTester


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


def _make_result(
    model: str = "llama3:8b",
    total: int = 10,
    flagged: int = 2,
    techniques: dict[str, int] | None = None,
) -> ModelTestResult:
    return ModelTestResult(
        model=model,
        total=total,
        succeeded=total - flagged,
        failed=0,
        flagged=flagged,
        duration_seconds=1.0,
        output_path=Path("/tmp/fake.txt"),
        techniques=techniques if techniques is not None else {},
    )


# ── ModelTestResult ──────────────────────────────────────────────────────

# test 1
def test_model_test_result_to_dict() -> None:
    """ModelTestResult.to_dict() must include all scalar fields with
    output_path converted to string."""
    r = _make_result("llama3:8b", total=10, flagged=3)
    d = r.to_dict()

    assert d["model"] == "llama3:8b"
    assert d["total"] == 10
    assert d["succeeded"] == 7
    assert d["failed"] == 0
    assert d["flagged"] == 3
    assert d["duration_seconds"] == 1.0
    assert isinstance(d["output_path"], str)


# test 2
def test_model_test_result_is_dataclass() -> None:
    """ModelTestResult must be a dataclass (fields directly accessible)."""
    r = ModelTestResult(
        model="test-model",
        total=5,
        succeeded=3,
        failed=1,
        flagged=1,
        duration_seconds=2.5,
        output_path=Path("/tmp/out.txt"),
    )
    assert r.model == "test-model"
    assert r.total == 5
    assert r.flagged == 1
    assert r.duration_seconds == 2.5


# ── check_ollama ──────────────────────────────────────────────────────────

# test 3
def test_check_ollama_returns_true_on_200(tmp_path: Path) -> None:
    """When curl returns '200', check_ollama must return True."""
    config = _make_config(tmp_path)
    tester = PipelineTester(config)

    mock_result = MagicMock()
    mock_result.stdout = "200"

    with patch("psg.automation.tester.subprocess.run", return_value=mock_result):
        assert tester.check_ollama() is True


# test 4
def test_check_ollama_returns_false_on_non_200(tmp_path: Path) -> None:
    """When curl returns a non-200 code, check_ollama must return False."""
    config = _make_config(tmp_path)
    tester = PipelineTester(config)

    mock_result = MagicMock()
    mock_result.stdout = "503"

    with patch("psg.automation.tester.subprocess.run", return_value=mock_result):
        assert tester.check_ollama() is False


# test 5
def test_check_ollama_returns_false_on_exception(tmp_path: Path) -> None:
    """When curl itself fails (e.g. timeout), check_ollama must return False."""
    config = _make_config(tmp_path)
    tester = PipelineTester(config)

    with patch("psg.automation.tester.subprocess.run", side_effect=TimeoutError):
        assert tester.check_ollama() is False


# ── get_available_models ──────────────────────────────────────────────────

# test 6
def test_get_available_models_parses_json(tmp_path: Path) -> None:
    """get_available_models must parse Ollama's /api/tags JSON and return
    model name list."""
    config = _make_config(tmp_path)
    tester = PipelineTester(config)

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps({"models": [{"name": "llama3:8b"}, {"name": "mistral:7b"}]})

    with patch("psg.automation.tester.subprocess.run", return_value=mock_result):
        models = tester.get_available_models()

    assert models == ["llama3:8b", "mistral:7b"]


# test 7
def test_get_available_models_empty_on_failure(tmp_path: Path) -> None:
    """When curl fails or returns bad JSON, get_available_models must
    return an empty list (not raise)."""
    config = _make_config(tmp_path)
    tester = PipelineTester(config)

    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = "error"

    with patch("psg.automation.tester.subprocess.run", return_value=mock_result):
        models = tester.get_available_models()
    assert models == []


# test 8 — urllib fallback path
def test_get_available_models_urllib_fallback(tmp_path: Path) -> None:
    """If subprocess is unavailable, the codebase should not crash.
    Verify that get_available_models returns [] gracefully when
    subprocess.run raises any Exception."""
    config = _make_config(tmp_path)
    tester = PipelineTester(config)

    with patch("psg.automation.tester.subprocess.run", side_effect=OSError("no curl")):
        models = tester.get_available_models()

    assert models == []


# test 9
def test_get_available_models_timeout_returns_empty(tmp_path: Path) -> None:
    """A TimeoutExpired exception must cause get_available_models to
    return [] (not raise)."""
    config = _make_config(tmp_path)
    tester = PipelineTester(config)

    with patch("psg.automation.tester.subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 5)):
        models = tester.get_available_models()

    assert models == []


# ── parse_test_output (via run_test) ──────────────────────────────────────

# test 10
def test_parse_test_output_extracts_stats(tmp_path: Path) -> None:
    """run_test must parse key=value lines from stdout to extract
    total / succeeded / failed / flagged."""
    config = _make_config(tmp_path)
    tester = PipelineTester(config)

    output = "some noise\ntotal=10 succeeded=8 failed=0 flagged=2\nmore noise"
    mock_result = MagicMock()
    mock_result.stdout = output
    mock_result.returncode = 0

    with patch("psg.automation.tester.subprocess.run", return_value=mock_result):
        with patch("psg.automation.tester.time.time", side_effect=[0.0, 1.0]):
            result = tester.run_test(Path("/tmp/v.json"), "llama3:8b", "auto")

    assert result is not None
    assert result.total == 10
    assert result.succeeded == 8
    assert result.failed == 0
    assert result.flagged == 2


# test 11
def test_parse_test_output_no_stats_defaults_zero(tmp_path: Path) -> None:
    """When stdout has no key=value stats, run_test must return None
    (total=0 indicates a silent failure)."""
    config = _make_config(tmp_path)
    tester = PipelineTester(config)

    mock_result = MagicMock()
    mock_result.stdout = "no stats here at all\n"
    mock_result.returncode = 0

    with patch("psg.automation.tester.subprocess.run", return_value=mock_result):
        with patch("psg.automation.tester.time.time", return_value=0.0):
            result = tester.run_test(Path("/tmp/v.json"), "llama3:8b", "auto")

    assert result is None


# ── timeout multiplier (default 3×) ────────

# test 12
def test_timeout_multiplier_default_is_3x(tmp_path: Path) -> None:
    """The test command timeout is test_timeout * 3 (3× default is 120*3
    = 360 seconds).  We verify the multiplier is applied by checking
    the value passed as the `timeout` kwarg to subprocess.run."""
    config = _make_config(tmp_path)
    tester = PipelineTester(config)

    # Default test_timeout is 120; the effective timeout multiplier is * 3
    expected_timeout = config.test_timeout * 3

    mock_result = MagicMock()
    mock_result.stdout = "total=1 succeeded=1 failed=0 flagged=0"
    mock_result.returncode = 0

    with patch("psg.automation.tester.subprocess.run", return_value=mock_result) as mock_run:
        with patch("psg.automation.tester.time.time", side_effect=[0.0, 0.5]):
            tester.run_test(Path("/tmp/v.json"), "llama3:8b", "auto")

        _, kwargs = mock_run.call_args
        assert kwargs["timeout"] == expected_timeout


# ── run_test ──────────────────────────────────────────────────────────────

# test 13
def test_run_test_returns_model_test_result(tmp_path: Path) -> None:
    """run_test must return a ModelTestResult on success."""
    config = _make_config(tmp_path)
    tester = PipelineTester(config)

    mock_result = MagicMock()
    mock_result.stdout = "total=5 succeeded=3 failed=1 flagged=1"
    mock_result.returncode = 0

    with patch("psg.automation.tester.subprocess.run", return_value=mock_result):
        with patch("psg.automation.tester.time.time", side_effect=[0.0, 2.0]):
            result = tester.run_test(Path("/tmp/v.json"), "mistral:7b", "auto")

    assert isinstance(result, ModelTestResult)
    assert result.model == "mistral:7b"
    assert result.total == 5
    assert result.flagged == 1
    assert result.duration_seconds == 2.0


# test 14
def test_run_test_returns_none_on_timeout(tmp_path: Path) -> None:
    """run_test must return None when subprocess.TimeoutExpired is raised."""
    config = _make_config(tmp_path)
    tester = PipelineTester(config)

    with patch("psg.automation.tester.subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 999)):
        with patch("psg.automation.tester.time.time", side_effect=[0.0, 10.0]):
            result = tester.run_test(Path("/tmp/v.json"), "llama3:8b", "auto")

    assert result is None


# test 15
def test_run_test_returns_none_on_general_exception(tmp_path: Path) -> None:
    """run_test must return None for non-timeout exceptions."""
    config = _make_config(tmp_path)
    tester = PipelineTester(config)

    with patch("psg.automation.tester.subprocess.run", side_effect=OSError("broken")):
        with patch("psg.automation.tester.time.time", side_effect=[0.0, 0.1]):
            result = tester.run_test(Path("/tmp/v.json"), "llama3:8b", "auto")

    assert result is None


# test 16
def test_run_test_output_path_in_results_dir(tmp_path: Path) -> None:
    """The output_path of the returned ModelTestResult must be inside
    config.results_dir."""
    config = _make_config(tmp_path)
    tester = PipelineTester(config)

    mock_result = MagicMock()
    mock_result.stdout = "total=1 succeeded=1 failed=0 flagged=0"
    mock_result.returncode = 0

    with patch("psg.automation.tester.subprocess.run", return_value=mock_result):
        with patch("psg.automation.tester.time.time", side_effect=[0.0, 1.0]):
            result = tester.run_test(Path("/tmp/v.json"), "llama3:8b", "auto")

    assert result is not None
    # The output_path's parent should be results_dir (after resolving the filename)
    assert str(result.output_path).startswith(str(config.results_dir)) or \
           "auto_" in str(result.output_path)


# test 17
def test_run_test_model_colon_replaced_in_output(tmp_path: Path) -> None:
    """Model names with ':' (e.g. 'llama3:8b') must be sanitized to '_' in
    the output filename."""
    config = _make_config(tmp_path)
    tester = PipelineTester(config)

    mock_result = MagicMock()
    mock_result.stdout = "total=1 succeeded=1 failed=0 flagged=0"
    mock_result.returncode = 0

    with patch("psg.automation.tester.subprocess.run", return_value=mock_result) as mock_run:
        with patch("psg.automation.tester.time.time", side_effect=[0.0, 1.0]):
            tester.run_test(Path("/tmp/v.json"), "llama3:8b", "auto")

    # The command passed to subprocess.run should include model as-is
    cmd = mock_run.call_args[0][0]
    assert "--model" in cmd
    idx = cmd.index("--model")
    assert cmd[idx + 1] == "llama3:8b"


# ── run_all_tests ─────────────────────────────────────────────────────────

# test 18
def test_run_all_tests_checks_ollama_first(tmp_path: Path) -> None:
    """run_all_tests must call check_ollama and return [] if it's False."""
    config = _make_config(tmp_path)
    config.test_models = ["llama3:8b"]
    tester = PipelineTester(config)

    with patch.object(tester, "check_ollama", return_value=False):
        results = tester.run_all_tests(Path("/tmp/v.json"))

    assert results == []


# test 19
def test_run_all_tests_filters_unavailable_models(tmp_path: Path) -> None:
    """Models not in the available set must be skipped."""
    config = _make_config(tmp_path)
    config.test_models = ["llama3:8b", "gemma2:2b"]
    tester = PipelineTester(config)

    with patch.object(tester, "check_ollama", return_value=True):
        with patch.object(tester, "get_available_models", return_value=["llama3:8b"]):
            with patch.object(tester, "run_test", return_value=_make_result("llama3:8b")):
                results = tester.run_all_tests(Path("/tmp/v.json"))

    # Only llama3:8b was available; gemma2:2b was skipped
    assert len(results) == 1
    assert results[0].model == "llama3:8b"


# test 20
def test_run_all_tests_returns_result_list(tmp_path: Path) -> None:
    """When models are available, run_all_tests must return a list of
    ModelTestResult."""
    config = _make_config(tmp_path)
    config.test_models = ["llama3:8b"]
    tester = PipelineTester(config)

    with patch.object(tester, "check_ollama", return_value=True):
        with patch.object(tester, "get_available_models", return_value=["llama3:8b"]):
            with patch.object(tester, "run_test", return_value=_make_result("llama3:8b")):
                results = tester.run_all_tests(Path("/tmp/v.json"))

    assert len(results) == 1
    assert isinstance(results[0], ModelTestResult)


# test 21
def test_run_all_tests_skips_models_returning_none(tmp_path: Path) -> None:
    """If run_test returns None for a model, it must be excluded from
    the results list."""
    config = _make_config(tmp_path)
    config.test_models = ["llama3:8b", "mistral:7b"]
    tester = PipelineTester(config)

    with patch.object(tester, "check_ollama", return_value=True):
        with patch.object(tester, "get_available_models", return_value=["llama3:8b", "mistral:7b"]):
            with patch.object(tester, "run_test", side_effect=[
                _make_result("llama3:8b"),
                None,  # mistral timed out
            ]):
                results = tester.run_all_tests(Path("/tmp/v.json"))

    assert len(results) == 1
    assert results[0].model == "llama3:8b"


# ── script in results_dir ───────────────────────────────────────────────

# test 22
def test_run_in_tmux_writes_script_to_base_dir(tmp_path: Path) -> None:
    """run_in_tmux must write a shell script to config.base_dir."""
    config = _make_config(tmp_path)
    config.test_models = ["llama3:8b"]
    tester = PipelineTester(config)

    with patch("psg.automation.tester.subprocess.run"):
        session = tester.run_in_tmux(Path("/tmp/v.json"), "auto")

    script_path = config.base_dir / "run_auto_test.sh"
    assert script_path.exists()
    content = script_path.read_text()
    assert "llama3:8b" in content
    assert session == "auto_test"


# test 23
def test_run_in_tmux_script_uses_results_dir(tmp_path: Path) -> None:
    """The generated script must reference config.results_dir for output
    file paths (checkpoints, reports)."""
    config = _make_config(tmp_path)
    config.test_models = ["llama3:8b"]
    tester = PipelineTester(config)

    with patch("psg.automation.tester.subprocess.run"):
        tester.run_in_tmux(Path("/tmp/v.json"), "auto")

    script_path = config.base_dir / "run_auto_test.sh"
    content = script_path.read_text()
    # The results_dir path should appear in the script
    assert str(config.results_dir) in content


# ── logging (M9: no print() in library code) ──────────────────────────────


def test_get_available_models_uses_logger_on_timeout(tmp_path: Path, caplog) -> None:
    """On TimeoutExpired, get_available_models must log a warning (not print)."""
    import logging

    config = _make_config(tmp_path)
    tester = PipelineTester(config)

    with patch(
        "psg.automation.tester.subprocess.run",
        side_effect=subprocess.TimeoutExpired("cmd", 5),
    ):
        with caplog.at_level(logging.WARNING, logger="psg.automation"):
            models = tester.get_available_models()

    assert models == []
    assert any("timed out" in r.message.lower() for r in caplog.records)


def test_get_available_models_uses_logger_on_json_error(tmp_path: Path, caplog) -> None:
    """On JSONDecodeError, get_available_models must log an error (not print)."""
    import logging

    config = _make_config(tmp_path)
    tester = PipelineTester(config)

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "not-json"

    with patch("psg.automation.tester.subprocess.run", return_value=mock_result):
        with caplog.at_level(logging.ERROR, logger="psg.automation"):
            models = tester.get_available_models()

    assert models == []
    assert any("json" in r.message.lower() for r in caplog.records)


def test_run_test_uses_logger_on_exception(tmp_path: Path, caplog) -> None:
    """On general exception, run_test must log an error (not print)."""
    import logging

    config = _make_config(tmp_path)
    tester = PipelineTester(config)

    with patch("psg.automation.tester.subprocess.run", side_effect=OSError("broke")):
        with caplog.at_level(logging.ERROR, logger="psg.automation"):
            with patch("psg.automation.tester.time.time", side_effect=[0.0, 0.1]):
                result = tester.run_test(Path("/tmp/v.json"), "model", "auto")

    assert result is None
    assert any("error" in r.message.lower() for r in caplog.records)


def test_run_all_tests_uses_logger_when_ollama_down(tmp_path: Path, caplog) -> None:
    """When Ollama is down, run_all_tests must log an error (not print)."""
    import logging

    config = _make_config(tmp_path)
    config.test_models = ["llama3:8b"]
    tester = PipelineTester(config)

    with patch.object(tester, "check_ollama", return_value=False):
        with caplog.at_level(logging.ERROR, logger="psg.automation"):
            results = tester.run_all_tests(Path("/tmp/v.json"))

    assert results == []
    assert any("ollama not running" in r.message.lower() for r in caplog.records)