"""
Versioned result schema.

SCHEMA_VERSION history:
- "1.0.0": Initial typed schema (2026-02-15)
- "0.0.0": Legacy untyped dicts (implicit)
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Optional, Any
import json

SCHEMA_VERSION = "1.1.0"


@dataclass
class RuntimeConfig:
    """Captures reproducibility parameters."""
    seed: Optional[int] = None
    temperature: float = 0.7
    judge_temperature: float = 0.1
    provider_timeout_sec: int = 120
    store_responses: str = "truncated"
    redact: bool = True


@dataclass
class AttackResult:
    """Single attack execution result."""
    id: str
    name: str
    category: str
    success: bool
    confidence: float
    matched_indicators: List[str]
    response_preview: str  # Stored according to runtime policy
    time_ms: int
    detector_used: str = ""
    reasoning: Optional[str] = None
    error: Optional[str] = None
    fallback_used: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CategoryStats:
    """Aggregated stats per category."""
    total: int
    success: int

    @property
    def rate(self) -> float:
        return self.success / self.total if self.total > 0 else 0.0


@dataclass
class TestRun:
    """Complete test run with metadata."""
    # Schema metadata
    schema_version: str = field(default=SCHEMA_VERSION)

    # Run identification
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    run_id: Optional[str] = None  # Optional UUID for deduplication

    # Configuration
    provider: str = ""
    model: str = ""
    detector: str = ""
    system_prompt: Optional[str] = None
    runtime_config: RuntimeConfig = field(default_factory=RuntimeConfig)

    # Results
    total_attacks: int = 0
    successful: int = 0
    success_rate: float = 0.0
    categories: Dict[str, Dict[str, int]] = field(default_factory=dict)
    results: List[AttackResult] = field(default_factory=list)

    # Warnings/diagnostics
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        d = asdict(self)
        # Ensure nested dataclasses are dicts
        d["runtime_config"] = asdict(self.runtime_config)
        d["results"] = [r.to_dict() if isinstance(r, AttackResult) else r for r in self.results]
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestRun":
        """Deserialize from dict, handling legacy format."""
        version = data.get("schema_version", "0.0.0")

        if version == "0.0.0":
            # Legacy migration
            return cls._migrate_legacy(data)

        # Current version
        runtime_config = RuntimeConfig(**data.get("runtime_config", {}))
        results = [
            AttackResult(**r) if isinstance(r, dict) else r
            for r in data.get("results", [])
        ]

        return cls(
            schema_version=version,
            timestamp=data.get("timestamp", ""),
            run_id=data.get("run_id"),
            provider=data.get("provider", ""),
            model=data.get("model", ""),
            detector=data.get("detector", ""),
            system_prompt=data.get("system_prompt"),
            runtime_config=runtime_config,
            total_attacks=data.get("total_attacks", 0),
            successful=data.get("successful", 0),
            success_rate=data.get("success_rate", 0.0),
            categories=data.get("categories", {}),
            results=results,
            warnings=data.get("warnings", []),
        )

    @classmethod
    def _migrate_legacy(cls, data: Dict[str, Any]) -> "TestRun":
        """Migrate v0 (untyped) to v1 schema."""
        # Extract provider/model from combined string like "ollama/qwen2.5:3b"
        provider_str = data.get("provider", "unknown/unknown")
        if "/" in provider_str:
            provider, model = provider_str.split("/", 1)
        else:
            provider, model = provider_str, "unknown"

        # Migrate result dicts
        results = []
        for r in data.get("results", []):
            results.append(AttackResult(
                id=r.get("id", ""),
                name=r.get("name", ""),
                category=r.get("category", ""),
                success=r.get("success", False),
                confidence=r.get("confidence", 0.0),
                matched_indicators=r.get("matched_indicators", []),
                response_preview=r.get("response", "")[:500],
                time_ms=r.get("time_ms", 0),
                reasoning=r.get("reasoning"),
                error=r.get("error"),
                fallback_used=False,  # Can't know for legacy
            ))

        return cls(
            schema_version=SCHEMA_VERSION,  # Upgrade version
            timestamp=data.get("timestamp", ""),
            provider=provider,
            model=model,
            detector=data.get("detector", ""),
            runtime_config=RuntimeConfig(),  # Unknown for legacy
            total_attacks=data.get("total_attacks", 0),
            successful=data.get("successful", 0),
            success_rate=data.get("success_rate", 0.0),
            categories=data.get("categories", {}),
            results=results,
            warnings=["Migrated from legacy schema v0.0.0"],
        )
