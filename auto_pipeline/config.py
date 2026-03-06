"""Configuration for Auto Vector Pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class PipelineConfig:
    """Pipeline configuration."""
    
    # Discovery settings
    search_queries: list[str] = field(default_factory=lambda: [
        "LLM jailbreak 2026",
        "prompt injection techniques",
        "AI safety bypass methods",
    ])
    max_sources_per_query: int = 5
    
    # Generator settings
    max_vectors_per_run: int = 10
    generator_model: str = "opus"
    
    # Tester settings
    test_models: list[str] = field(default_factory=lambda: [
        "llama3:8b",
        "mistral:7b",
        "qwen2.5:3b",
        "phi3:mini",
        "gemma2:2b",
    ])
    test_timeout: int = 120
    ollama_base_url: str = "http://localhost:11434"
    
    # Paths
    base_dir: Path = field(default_factory=lambda: Path(__file__).parent)
    known_sources_path: Path = field(default_factory=lambda: Path(__file__).parent / "known_sources.json")
    known_vectors_path: Path = field(default_factory=lambda: Path(__file__).parent / "known_vectors.json")
    results_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "results")
    reports_dir: Path = field(default_factory=lambda: Path(__file__).parent / "reports")
    
    # Notification
    notify_discord: bool = True
    
    def __post_init__(self) -> None:
        """Ensure paths exist."""
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)


def load_config(config_path: Path | None = None) -> PipelineConfig:
    """Load config from YAML file or use defaults."""
    if config_path and config_path.exists():
        with open(config_path) as f:
            data: dict[str, Any] = yaml.safe_load(f)
        return PipelineConfig(**data)
    return PipelineConfig()


if __name__ == "__main__":
    cfg = load_config()
    print(f"Config loaded: {cfg}")
