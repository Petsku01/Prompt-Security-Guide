from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

from psg.automation.config import PipelineConfig, load_config


def test_load_config_empty_yaml_returns_defaults() -> None:
    with NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        path = Path(f.name)

    try:
        config = load_config(path)
        assert isinstance(config, PipelineConfig)
    finally:
        path.unlink(missing_ok=True)


def test_load_config_no_path_returns_defaults() -> None:
    config = load_config(None)
    assert isinstance(config, PipelineConfig)
