from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from psg.automation.config import PipelineConfig, load_config


# ── Existing tests (kept) ────────────────────────────────────────────────

def test_load_config_empty_yaml_returns_defaults(tmp_path: Path) -> None:
    """An empty YAML file should produce a PipelineConfig with all defaults."""
    config_file = tmp_path / "empty.yaml"
    config_file.write_text("")
    config = load_config(config_file)
    assert isinstance(config, PipelineConfig)


def test_load_config_no_path_returns_defaults() -> None:
    """Passing None should produce a PipelineConfig with all defaults."""
    config = load_config(None)
    assert isinstance(config, PipelineConfig)


# ── New tests (Task 0.2) ────────────────────────────────────────────────

def test_default_config_has_search_queries() -> None:
    """Default PipelineConfig must ship a non-empty search_queries list."""
    config = PipelineConfig(
        base_dir=Path("/tmp/psg-test"),
        project_root=Path("/tmp/psg-test"),
        output_dir=Path("/tmp/psg-test"),
        datasets_dir=Path("/tmp/psg-test/ds"),
        results_dir=Path("/tmp/psg-test/rs"),
        logs_dir=Path("/tmp/psg-test/lg"),
        known_sources_path=Path("/tmp/psg-test/ks.json"),
        known_vectors_path=Path("/tmp/psg-test/kv.json"),
        reports_dir=Path("/tmp/psg-test/rp"),
    )
    assert isinstance(config.search_queries, list)
    assert len(config.search_queries) > 0


def test_default_config_has_test_models() -> None:
    """Default PipelineConfig must ship a non-empty test_models list."""
    config = PipelineConfig(
        base_dir=Path("/tmp/psg-test"),
        project_root=Path("/tmp/psg-test"),
        output_dir=Path("/tmp/psg-test"),
        datasets_dir=Path("/tmp/psg-test/ds"),
        results_dir=Path("/tmp/psg-test/rs"),
        logs_dir=Path("/tmp/psg-test/lg"),
        known_sources_path=Path("/tmp/psg-test/ks.json"),
        known_vectors_path=Path("/tmp/psg-test/kv.json"),
        reports_dir=Path("/tmp/psg-test/rp"),
    )
    assert isinstance(config.test_models, list)
    assert len(config.test_models) > 0


def test_default_config_paths_are_path_objects() -> None:
    """All path-typed fields on a default PipelineConfig must be Path objs."""
    config = PipelineConfig(
        base_dir=Path("/tmp/psg-test"),
        project_root=Path("/tmp/psg-test"),
        output_dir=Path("/tmp/psg-test"),
        datasets_dir=Path("/tmp/psg-test/ds"),
        results_dir=Path("/tmp/psg-test/rs"),
        logs_dir=Path("/tmp/psg-test/lg"),
        known_sources_path=Path("/tmp/psg-test/ks.json"),
        known_vectors_path=Path("/tmp/psg-test/kv.json"),
        reports_dir=Path("/tmp/psg-test/rp"),
    )
    path_fields = [
        "scrapling_venv_path",
        "base_dir",
        "project_root",
        "output_dir",
        "datasets_dir",
        "results_dir",
        "logs_dir",
        "known_sources_path",
        "known_vectors_path",
        "reports_dir",
    ]
    for field_name in path_fields:
        value = getattr(config, field_name)
        assert isinstance(value, Path), f"{field_name} is {type(value)}, expected Path"


def test_post_init_creates_directories(tmp_path: Path) -> None:
    """PipelineConfig.__post_init__ must create the dir-type paths that are
    expected to exist (datasets_dir, results_dir, logs_dir, reports_dir)."""
    datasets = tmp_path / "datasets"
    results = tmp_path / "results"
    logs = tmp_path / "logs"
    reports = tmp_path / "reports"

    config = PipelineConfig(
        base_dir=tmp_path,
        project_root=tmp_path,
        output_dir=tmp_path,
        datasets_dir=datasets,
        results_dir=results,
        logs_dir=logs,
        known_sources_path=tmp_path / "known_sources.json",
        known_vectors_path=tmp_path / "known_vectors.json",
        reports_dir=reports,
    )

    # __post_init__ already ran in the constructor above
    for d in (datasets, results, logs, reports):
        assert d.is_dir(), f"{d} was not created by __post_init__"


def test_load_config_from_yaml_file(tmp_path: Path) -> None:
    """Loading a YAML file with valid keys should override defaults."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({"max_vectors_per_run": 5}))

    config = load_config(config_file)
    assert config.max_vectors_per_run == 5


def test_load_config_unknown_keys_raises_typerror(tmp_path: Path) -> None:
    """PipelineConfig is a dataclass — unknown YAML keys must cause TypeError,
    NOT be silently ignored."""
    config_file = tmp_path / "bad.yaml"
    config_file.write_text(yaml.dump({"bogus_key_that_does_not_exist": True}))

    with pytest.raises(TypeError):
        load_config(config_file)


# ── validate_environment tests (I7) ──────────────────────────────────────────

def test_validate_environment_happy_path(tmp_path: Path) -> None:
    """validate_environment succeeds when scrapling_python exists and can
    import scrapling."""
    from unittest.mock import patch, MagicMock

    scrapling_bin = tmp_path / "bin" / "python"
    scrapling_bin.parent.mkdir(parents=True)
    scrapling_bin.touch()

    config = PipelineConfig(
        base_dir=tmp_path,
        project_root=tmp_path,
        output_dir=tmp_path,
        datasets_dir=tmp_path / "ds",
        results_dir=tmp_path / "rs",
        logs_dir=tmp_path / "lg",
        known_sources_path=tmp_path / "ks.json",
        known_vectors_path=tmp_path / "kv.json",
        reports_dir=tmp_path / "rp",
        scrapling_python=str(scrapling_bin),
    )

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stderr = ""
    mock_result.stdout = ""

    with patch("psg.automation.config.subprocess.run", return_value=mock_result):
        # Should not raise
        from psg.automation.config import validate_environment
        validate_environment(config)


def test_validate_environment_raises_on_missing_scrapling(tmp_path: Path) -> None:
    """validate_environment raises RuntimeError when scrapling_python
    import fails (non-zero returncode)."""
    from unittest.mock import patch, MagicMock

    scrapling_bin = tmp_path / "bin" / "python"
    scrapling_bin.parent.mkdir(parents=True)
    scrapling_bin.touch()

    config = PipelineConfig(
        base_dir=tmp_path,
        project_root=tmp_path,
        output_dir=tmp_path,
        datasets_dir=tmp_path / "ds",
        results_dir=tmp_path / "rs",
        logs_dir=tmp_path / "lg",
        known_sources_path=tmp_path / "ks.json",
        known_vectors_path=tmp_path / "kv.json",
        reports_dir=tmp_path / "rp",
        scrapling_python=str(scrapling_bin),
    )

    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "ModuleNotFoundError: No module named 'scrapling'"
    mock_result.stdout = ""

    with patch("psg.automation.config.subprocess.run", return_value=mock_result):
        from psg.automation.config import validate_environment
        with pytest.raises(RuntimeError, match="Scrapling import failed"):
            validate_environment(config)


