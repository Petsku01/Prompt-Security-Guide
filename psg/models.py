from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class RedactionMode(str, Enum):
    PARTIAL = "partial"
    STRICT = "strict"
    OFF = "off"


class ClassificationInputMode(str, Enum):
    AUTO = "auto"
    RAW = "raw"
    REDACTED = "redacted"
    BOTH = "both"


@dataclass(slots=True)
class Attack:
    id: str
    prompt: str
    metadata: dict[str, Any] = field(default_factory=dict)
    followups: list[str] = field(default_factory=list)  # Multi-turn attack prompts


@dataclass(slots=True)
class LLMResponse:
    content: str
    raw: dict[str, Any]
    model: str | None = None
    finish_reason: str | None = None


@dataclass(slots=True)
class AttemptResult:
    attack_id: str
    prompt: str
    response_text: str
    flagged: bool  # Legacy alias for attack_successful
    labels: list[str]  # Legacy alias for harmful_labels
    harm_score: float = 0.0  # 0.0 - 1.0
    is_refusal: bool = False
    has_disclaimer: bool = False
    error: str | None = None
    # True when the detector could not produce a confident verdict for this
    # attack. Counted in RunSummary so a scan does not silently look "green"
    # when classification was unreliable.
    detector_failed: bool = False
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(slots=True)
class RunSummary:
    total: int
    succeeded: int
    failed: int
    flagged: int
    duration_seconds: float
    report_write_failed: bool = False
    # Number of attacks for which the detector could not classify confidently
    # (e.g. judge timeout, unparseable judge output). Surfaced loudly at end
    # of run so a scan that "looks green" because the detector died is caught.
    detector_failures: int = 0


@dataclass(slots=True)
class AppConfig:
    model: str
    catalog_path: str
    base_url: str = "http://localhost:11434/v1"
    timeout_seconds: float = 240.0
    max_retries: int = 4
    backoff_base_seconds: float = 0.6
    backoff_cap_seconds: float = 8.0
    checkpoint_path: str = "results/checkpoint.jsonl"
    report_json_path: str = "results/report.json"
    report_text_path: str = "results/report.txt"
    redaction_mode: RedactionMode = RedactionMode.PARTIAL
    allow_insecure_http: bool = False
    temperature: float = 0.0
    max_tokens: int = 512
    api_key: str | None = None
    system_prompt: str | None = None
    defense_report: bool = False
    defense_report_path: str = "results/defense_report.txt"
    detector: str = "keyword"
    judge_model: str = "llama3:8b"
    judge_url: str | None = None
    classification_input_mode: ClassificationInputMode = ClassificationInputMode.AUTO
    workers: int = 1  # Number of parallel workers (1 = sequential)
    rate_limit: float | None = None  # Max requests per second (None = unlimited)
    multi_turn: bool = False  # Enable multi-turn attack execution
    validate_urls: bool = False  # Enable online URL validation in classifier
    validate_dois: bool = False  # Enable online DOI validation in classifier
    validation_timeout_seconds: float = 5.0
    attack_mode: str = "single"  # single, crescendo, many-shot
    crescendo_turns: int = 7
    many_shot_examples: int = 10
    # How the ensemble detector combines keyword + judge verdicts:
    #   "any" (default)       — flag if either flags. True OR ensemble.
    #   "and"                 — flag only when both agree. Higher precision.
    #   "short_circuit"       — skip judge when keyword already flags. Cheapest.
    ensemble_mode: str = "any"
