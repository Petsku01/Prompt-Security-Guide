"""Runtime configuration for test runs."""
from dataclasses import dataclass
from typing import Optional
import platform
import sys


@dataclass
class EnvironmentInfo:
    """Captured at runtime for reproducibility."""
    python_version: str
    platform: str
    hostname: str

    @classmethod
    def capture(cls) -> "EnvironmentInfo":
        return cls(
            python_version=sys.version,
            platform=platform.platform(),
            hostname=platform.node(),
        )


@dataclass
class RunConfig:
    """User-provided configuration for a test run."""
    # Provider settings
    provider: str = "ollama"
    model: str = "qwen2.5:3b"
    api_key: Optional[str] = None

    # Reproducibility
    seed: Optional[int] = None
    temperature: float = 0.7

    # Detection
    detector: str = "substring"
    judge_model: str = "qwen2.5:3b"
    judge_temperature: float = 0.1
    allow_judge_fallback: bool = False

    # Filtering
    categories: Optional[list] = None

    # Output
    verbose: bool = False
    output_file: Optional[str] = None
    store_responses: str = "truncated"  # none|truncated|full
    redact: bool = True

    # System prompt
    system_prompt: Optional[str] = "You are a helpful assistant."
