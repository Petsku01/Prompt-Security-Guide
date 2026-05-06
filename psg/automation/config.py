"""Configuration for Auto Vector Pipeline."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]


@dataclass
class PipelineConfig:
    """Pipeline configuration."""

    # Discovery settings
    search_queries: list[str] = field(
        default_factory=lambda: [
            "LLM jailbreak 2026",
            "prompt injection techniques",
            "AI safety bypass methods",
        ]
    )
    max_sources_per_query: int = 5
    max_total_sources: int = 10

    # Generator settings
    max_vectors_per_run: int = 10
    max_vectors_per_source: int = 5
    generator_model: str = "dolphin-llama3:8b"

    # Tester settings
    test_models: list[str] = field(
        default_factory=lambda: [
            "llama3:8b",
            "mistral:7b",
            "qwen2.5:3b",
            "phi3:mini",
            "gemma2:2b",
        ]
    )
    test_timeout: int = 120
    ollama_base_url: str = field(
        default_factory=lambda: os.environ.get(
            "PSG_OLLAMA_URL", "http://localhost:11434"
        )
    )

    # Configurable tool paths (env var overrides)
    python_executable: str = field(
        default_factory=lambda: os.environ.get("PYTHON_PATH", "python3")
    )
    scrapling_venv_path: Path = field(
        default_factory=lambda: Path(
            os.environ.get(
                "PSG_SCRAPLING_VENV",
                str(Path.home() / ".openclaw/workspace/tools/scrapling-venv"),
            )
        )
    )
    scrapling_python: str = field(
        default_factory=lambda: os.environ.get(
            "SCRAPLING_PYTHON",
            str(
                Path(
                    os.environ.get(
                        "PSG_SCRAPLING_VENV",
                        str(Path.home() / ".openclaw/workspace/tools/scrapling-venv"),
                    )
                )
                / "bin"
                / "python"
            ),
        )
    )
    search_script: str = field(
        default_factory=lambda: os.environ.get(
            "SEARCH_SCRIPT",
            str(Path.home() / ".openclaw/workspace/tools/search_ddg.py"),
        )
    )

    # Root and output paths
    base_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent)
    project_root: Path = field(
        default_factory=lambda: Path(__file__).resolve().parents[2]
    )
    output_dir: Path = field(
        default_factory=lambda: Path(__file__).resolve().parents[2]
    )
    datasets_dir: Path = field(
        default_factory=lambda: Path(__file__).resolve().parents[2] / "datasets"
    )
    results_dir: Path = field(
        default_factory=lambda: Path(__file__).resolve().parents[2] / "results"
    )
    logs_dir: Path = field(
        default_factory=lambda: Path(__file__).resolve().parents[2] / "logs"
    )

    # Internal state/report paths
    known_sources_path: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent / "known_sources.json"
    )
    known_vectors_path: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent / "known_vectors.json"
    )
    reports_dir: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent / "reports"
    )

    # Cron scheduler
    cron_schedule: str = "0 3 * * *"

    def __post_init__(self) -> None:
        """Ensure paths exist and normalize output locations."""
        self.scrapling_venv_path = Path(self.scrapling_venv_path)
        self.base_dir = Path(self.base_dir)
        self.project_root = Path(self.project_root)
        self.output_dir = Path(self.output_dir)
        self.datasets_dir = Path(self.datasets_dir)
        self.results_dir = Path(self.results_dir)
        self.logs_dir = Path(self.logs_dir)
        self.known_sources_path = Path(self.known_sources_path)
        self.known_vectors_path = Path(self.known_vectors_path)
        self.reports_dir = Path(self.reports_dir)

        self.datasets_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)


def validate_environment(config: PipelineConfig) -> None:
    """Validate required external dependencies for automation pipeline."""
    errors: list[str] = []

    scrapling_python = Path(config.scrapling_python)
    if not scrapling_python.exists():
        errors.append(
            f"Scrapling Python not found: {scrapling_python}. "
            "Set PSG_SCRAPLING_VENV to the Scrapling venv root."
        )
    else:
        result = subprocess.run(
            [str(scrapling_python), "-c", "import scrapling"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            errors.append(
                "Scrapling import failed using "
                f"{scrapling_python}: {result.stderr.strip() or result.stdout.strip()}"
            )

    if errors:
        raise RuntimeError("Environment validation failed:\n- " + "\n- ".join(errors))


def load_config(config_path: Path | None = None) -> PipelineConfig:
    """Load config from YAML file or use defaults."""
    if config_path and config_path.exists():
        with open(config_path) as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}
        return PipelineConfig(**data)
    return PipelineConfig()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    cfg = load_config()
    logger = logging.getLogger("psg.automation")
    logger.info("Config loaded: %s", cfg)
