# Implementation Plan: prompt-security-guide Fixes

**Author:** Code Review (Stage 1 → Stage 2 Handoff)  
**Date:** 2026-02-15  
**Status:** Ready for Codex Implementation

---

## Executive Summary

This plan addresses 5 critical improvements identified in code review, prioritized by **risk × impact**:

| Priority | Fix | Risk | Impact | Effort |
|----------|-----|------|--------|--------|
| P0 | Judge-failure behavior (silent downgrade) | **HIGH** | Data integrity | 2h |
| P1 | Typed AttackResult + schema versioning | **MED** | Maintainability | 3h |
| P2 | Reproducibility controls | **MED** | Scientific validity | 2h |
| P3 | Runner/CLI separation | **LOW** | Testability | 3h |
| P4 | Pytest suite + deps | **LOW** | Quality | 4h |

**Total estimated effort:** 14h

---

## Assumptions (Surface for Validation)

1. **Python 3.9+** is the target runtime (dataclasses, type hints used extensively)
2. **Backward compatibility** with existing result JSON files is desired (read-only; new results use versioned schema)
4. **No CI/CD exists yet** - tests run manually via `pytest`
5. **Results directory** structure should not change

**Tradeoffs Accepted:**
- Prioritize explicit over implicit behavior (even if slightly more verbose)
- Favor composition over inheritance for new abstractions
- Accept temporary duplication to avoid premature abstraction

---

## File Structure After Implementation

```
prompt-security-guide/
├── pyproject.toml                 # NEW: Modern Python packaging
├── requirements.txt               # KEEP: Pin production deps
├── requirements-dev.txt           # NEW: Test/dev deps
├── tools/
│   ├── __init__.py               # NEW: Package marker
│   ├── cli.py                    # NEW: CLI entrypoint (argparse)
│   ├── runner.py                 # NEW: Core orchestration logic
│   ├── config.py                 # NEW: Runtime config dataclass
│   ├── schema.py                 # NEW: Versioned result types
│   ├── tester.py                 # DEPRECATE: Keep as shim → cli.py
│   ├── attacks/
│   │   └── (unchanged)
│   ├── detection/
│   │   ├── base.py               # MODIFY: Add JudgeFailure exception
│   │   ├── llm_judge.py          # MODIFY: Explicit failure handling
│   │   └── (rest unchanged)
│   └── providers/
│       ├── base.py               # MODIFY: Add seed/temperature to Response
│       └── (rest unchanged)
└── tests/
    ├── __init__.py               # NEW
    ├── conftest.py               # NEW: Shared fixtures
    ├── test_attacks.py           # NEW: Attack validation
    ├── test_detection.py         # NEW: Detector unit tests
    ├── test_providers.py         # NEW: Provider mock tests
    ├── test_runner.py            # NEW: Integration tests
    └── test_schema.py            # NEW: Schema validation
```

---

## P0: Judge-Failure Behavior (Critical)

### Problem

In `llm_judge.py:69-71`, when the judge LLM is unavailable:
```python
if judge_response is None:
    # Fallback to substring if judge unavailable
    from .substring import SubstringDetector
    return SubstringDetector().detect(response, indicators, attack_goal)
```

This **silently downgrades** to substring matching without logging or flagging the result. A user might believe they have LLM-judged results when they actually have substring-matched results.

### Solution

1. Add `JudgeUnavailableError` exception
2. Make fallback behavior **opt-in** via explicit flag
3. Mark results with `fallback_used: bool` field

### Implementation

**File: `tools/detection/base.py`**
```python
# Add after DetectionResult dataclass

class JudgeUnavailableError(Exception):
    """Raised when LLM judge cannot be reached and no fallback is configured."""
    pass
```

**File: `tools/detection/llm_judge.py`**
```python
class LLMJudgeDetector(BaseDetector):
    def __init__(
        self, 
        model: str = "qwen2.5:3b", 
        base_url: str = "http://localhost:11434",
        fallback_to_substring: bool = False,  # NEW: Explicit opt-in
        on_fallback: Optional[Callable[[], None]] = None,  # NEW: Hook
    ):
        self.model = model
        self.base_url = base_url
        self.timeout = 60
        self.fallback_to_substring = fallback_to_substring
        self.on_fallback = on_fallback

    def detect(self, response: str, indicators: List[str], attack_goal: str = "") -> DetectionResult:
        # ... existing judge call logic ...
        
        if judge_response is None:
            if self.fallback_to_substring:
                if self.on_fallback:
                    self.on_fallback()  # Allow caller to log/warn
                from .substring import SubstringDetector
                result = SubstringDetector().detect(response, indicators, attack_goal)
                # Mark that fallback was used
                return DetectionResult(
                    success=result.success,
                    confidence=result.confidence,
                    matched_indicators=result.matched_indicators,
                    reasoning=f"[FALLBACK] {result.reasoning}",
                    fallback_used=True,  # NEW field
                )
            else:
                raise JudgeUnavailableError(
                    f"LLM judge at {self.base_url} unavailable. "
                    "Set fallback_to_substring=True to use substring matching."
                )
        
        # ... rest of existing logic ...
```

**File: `tools/detection/base.py`** (update DetectionResult)
```python
@dataclass
class DetectionResult:
    """Result of attack success detection"""
    success: bool
    confidence: float  # 0.0 to 1.0
    matched_indicators: List[str]
    reasoning: Optional[str] = None
    fallback_used: bool = False  # NEW: Track fallback
```

### CLI Changes

Add flag `--allow-judge-fallback` to opt into fallback behavior:
```bash
python tester.py --detector llm_judge --allow-judge-fallback
```

Default behavior (no flag): fail fast if judge unavailable.

### Backward Compatibility

 Existing results remain valid (fallback_used defaults to False)  
 Old code calling `detect()` will get explicit error instead of silent downgrade  
️ Users relying on silent fallback must add `--allow-judge-fallback`

---

## P1: Typed AttackResult + Schema Versioning

### Problem

Results are currently untyped dicts with no schema version:
- Hard to validate
- Breaking changes silently corrupt data
- No way to migrate old results

### Solution

1. Add versioned `AttackResult` and `TestRun` dataclasses
2. Add `schema_version` field to all output
3. Provide migration path for old results

### Implementation

**File: `tools/schema.py`** (NEW)
```python
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

SCHEMA_VERSION = "1.0.0"


@dataclass
class RuntimeConfig:
    """Captures reproducibility parameters."""
    seed: Optional[int] = None
    temperature: float = 0.7
    judge_temperature: float = 0.1
    provider_timeout_sec: int = 120


@dataclass 
class AttackResult:
    """Single attack execution result."""
    id: str
    name: str
    category: str
    success: bool
    confidence: float
    matched_indicators: List[str]
    response_preview: str  # Truncated response
    time_ms: int
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
```

### Backward Compatibility

 `from_dict()` auto-detects and migrates legacy results  
 Old JSON files remain readable  
 New results include `schema_version` for future migrations

---

## P2: Reproducibility Controls

### Problem

- No `--seed` flag for deterministic runs
- Temperature hardcoded (0.7 for model, 0.1 for judge)
- No metadata capture of runtime environment

### Solution

Add `RuntimeConfig` (done in P1) and threading through provider/detector.

### Implementation

**File: `tools/providers/base.py`**
```python
@dataclass
class Response:
    """Standardized response from any provider"""
    text: str
    time_ms: int
    error: Optional[str] = None
    # NEW: Reproducibility metadata
    seed_used: Optional[int] = None
    temperature_used: Optional[float] = None
```

**File: `tools/providers/ollama.py`**
```python
class OllamaProvider(BaseProvider):
    def __init__(
        self, 
        model: str, 
        base_url: str = "http://localhost:11434",
        seed: Optional[int] = None,       # NEW
        temperature: float = 0.7,          # NEW: Configurable
    ):
        self.model = model
        self.base_url = base_url
        self.timeout = 120
        self.seed = seed
        self.temperature = temperature

    def call(self, prompt: str, system_prompt: Optional[str] = None) -> Response:
        options = {"temperature": self.temperature}
        if self.seed is not None:
            options["seed"] = self.seed
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        # ... rest of call logic ...
        
        return Response(
            text=resp.json().get("response", ""),
            time_ms=elapsed,
            seed_used=self.seed,
            temperature_used=self.temperature,
        )
```

**File: `tools/config.py`** (NEW)
```python
"""Runtime configuration for test runs."""
from dataclasses import dataclass
from typing import Optional
import os
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
    
    # System prompt
    system_prompt: Optional[str] = "You are a helpful assistant."
```

### CLI Flags

```bash
# Reproducibility flags
python tools/cli.py \
    --seed 42 \
    --temperature 0.5 \
    --judge-temperature 0.05
```

---

## P3: Runner/CLI Separation

### Problem

`tester.py` mixes:
- Argument parsing
- Provider/detector construction
- Test orchestration
- Console output
- JSON serialization

This makes unit testing difficult.

### Solution

Split into:
- `cli.py` - Argument parsing, config construction, output
- `runner.py` - Pure orchestration logic (testable)

### Implementation

**File: `tools/runner.py`** (NEW - Core Logic)
```python
"""
Core test runner - pure orchestration logic.

This module has NO CLI concerns, NO print statements, NO argparse.
It accepts typed configs and returns typed results.
"""
from typing import List, Optional, Callable
from .schema import TestRun, AttackResult, RuntimeConfig, SCHEMA_VERSION
from .config import RunConfig, EnvironmentInfo
from .providers import get_provider, BaseProvider
from .detection import get_detector, BaseDetector, JudgeUnavailableError
from .attacks import get_attacks, Attack


class TestRunner:
    """Orchestrates attack testing against a model."""
    
    def __init__(
        self,
        provider: BaseProvider,
        detector: BaseDetector,
        config: RunConfig,
        on_attack_complete: Optional[Callable[[Attack, AttackResult], None]] = None,
    ):
        self.provider = provider
        self.detector = detector
        self.config = config
        self.on_attack_complete = on_attack_complete  # Progress callback
    
    def run(self, attacks: List[Attack], system_prompt: Optional[str] = None) -> TestRun:
        """Execute attacks and return typed results."""
        results: List[AttackResult] = []
        warnings: List[str] = []
        successful = 0
        categories = {}
        
        for attack in attacks:
            result = self._run_single_attack(attack, system_prompt)
            results.append(result)
            
            if result.success:
                successful += 1
            
            # Track by category
            cat = attack.category
            if cat not in categories:
                categories[cat] = {"total": 0, "success": 0}
            categories[cat]["total"] += 1
            if result.success:
                categories[cat]["success"] += 1
            
            # Collect warnings
            if result.fallback_used:
                warnings.append(f"Attack {attack.id} used fallback detector")
            
            # Progress callback
            if self.on_attack_complete:
                self.on_attack_complete(attack, result)
        
        total = len(attacks)
        return TestRun(
            schema_version=SCHEMA_VERSION,
            provider=self.provider.name.split("/")[0] if "/" in self.provider.name else self.provider.name,
            model=self.config.model,
            detector=self.detector.name,
            system_prompt=system_prompt,
            runtime_config=RuntimeConfig(
                seed=self.config.seed,
                temperature=self.config.temperature,
                judge_temperature=self.config.judge_temperature,
            ),
            total_attacks=total,
            successful=successful,
            success_rate=100 * successful / total if total > 0 else 0.0,
            categories=categories,
            results=results,
            warnings=warnings,
        )
    
    def _run_single_attack(self, attack: Attack, system_prompt: Optional[str]) -> AttackResult:
        """Execute single attack and return result."""
        response = self.provider.call(attack.prompt, system_prompt)
        
        if response.error:
            return AttackResult(
                id=attack.id,
                name=attack.name,
                category=attack.category,
                success=False,
                confidence=0.0,
                matched_indicators=[],
                response_preview="",
                time_ms=response.time_ms,
                error=response.error,
            )
        
        try:
            detection = self.detector.detect(
                response.text,
                attack.indicators,
                attack.goal,
            )
        except JudgeUnavailableError as e:
            return AttackResult(
                id=attack.id,
                name=attack.name,
                category=attack.category,
                success=False,
                confidence=0.0,
                matched_indicators=[],
                response_preview=response.text[:500],
                time_ms=response.time_ms,
                error=str(e),
            )
        
        return AttackResult(
            id=attack.id,
            name=attack.name,
            category=attack.category,
            success=detection.success,
            confidence=detection.confidence,
            matched_indicators=detection.matched_indicators,
            response_preview=response.text[:500],
            time_ms=response.time_ms,
            reasoning=detection.reasoning,
            fallback_used=detection.fallback_used,
        )


def create_runner(config: RunConfig) -> TestRunner:
    """Factory function to create runner from config."""
    provider_kwargs = {"temperature": config.temperature}
    if config.seed is not None:
        provider_kwargs["seed"] = config.seed
    if config.api_key:
        provider_kwargs["api_key"] = config.api_key
    
    provider = get_provider(config.provider, config.model, **provider_kwargs)
    
    detector_kwargs = {}
    if config.detector == "llm_judge":
        detector_kwargs["model"] = config.judge_model
        detector_kwargs["fallback_to_substring"] = config.allow_judge_fallback
    
    detector = get_detector(config.detector, **detector_kwargs)
    
    return TestRunner(provider, detector, config)
```

**File: `tools/cli.py`** (NEW - CLI Layer)
```python
#!/usr/bin/env python3
"""
CLI entrypoint for security testing.

This module handles:
- Argument parsing
- Console output/progress
- JSON file writing

All business logic lives in runner.py.
"""
import argparse
import sys
from typing import Optional

from .config import RunConfig
from .runner import create_runner
from .attacks import get_attacks, list_categories, Attack
from .schema import AttackResult


def print_progress(attack: Attack, result: AttackResult, index: int, total: int, verbose: bool):
    """Print progress for a single attack."""
    status = "SUCCEEDED" if result.success else "BLOCKED"
    if result.error:
        status = f"ERROR: {result.error[:50]}"
    
    print(f"[{index}/{total}] {attack.id}: {attack.name}")
    
    if result.success:
        print(f"         {status} (confidence: {result.confidence:.0%})")
        if verbose and result.matched_indicators:
            print(f"         Matched: {result.matched_indicators}")
    elif result.error:
        print(f"         {status}")
    else:
        print(f"         {status} ({result.time_ms}ms)")


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        description="LLM Security Tester",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    # Provider options
    parser.add_argument("--model", "-m", default="qwen2.5:3b")
    parser.add_argument("--api-key")
    
    # Reproducibility options (NEW)
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("--temperature", type=float, default=0.7)
    
    # Detection options
    parser.add_argument("--detector", "-d", choices=["substring", "llm_judge"], default="substring")
    parser.add_argument("--judge-model", default="qwen2.5:3b")
    parser.add_argument("--judge-temperature", type=float, default=0.1)
    parser.add_argument("--allow-judge-fallback", action="store_true",
                        help="Fall back to substring matching if judge unavailable")
    
    # Attack filtering
    parser.add_argument("--categories", "-c")
    parser.add_argument("--list-categories", action="store_true")
    
    # Output options
    parser.add_argument("--output", "-o")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--no-system-prompt", action="store_true")
    
    args = parser.parse_args(argv)
    
    if args.list_categories:
        print("Available attack categories:")
        for cat in list_categories():
            print(f"  - {cat}")
        return 0
    
    # Build config
    config = RunConfig(
        provider=args.provider,
        model=args.model,
        api_key=args.api_key,
        seed=args.seed,
        temperature=args.temperature,
        detector=args.detector,
        judge_model=args.judge_model,
        judge_temperature=args.judge_temperature,
        allow_judge_fallback=args.allow_judge_fallback,
        categories=args.categories.split(",") if args.categories else None,
        verbose=args.verbose,
        output_file=args.output,
        system_prompt=None if args.no_system_prompt else "You are a helpful assistant.",
    )
    
    # Get attacks
    attacks = get_attacks(categories=config.categories)
    if not attacks:
        print("No attacks found matching criteria")
        return 1
    
    # Create runner with progress callback
    runner = create_runner(config)
    
    attack_index = [0]  # Mutable counter for closure
    def on_progress(attack: Attack, result: AttackResult):
        attack_index[0] += 1
        print_progress(attack, result, attack_index[0], len(attacks), config.verbose)
    
    runner.on_attack_complete = on_progress
    
    # Run tests
    print(f"\nRunning {len(attacks)} attacks against {runner.provider.name}")
    print(f"Detector: {runner.detector.name}")
    print("=" * 60)
    
    test_run = runner.run(attacks, config.system_prompt)
    
    # Print summary
    print()
    print("=" * 60)
    print(f"RESULTS: {test_run.successful}/{test_run.total_attacks} succeeded ({test_run.success_rate:.1f}%)")
    print("=" * 60)
    
    print("\nBy Category:")
    for cat, stats in sorted(test_run.categories.items()):
        pct = 100 * stats["success"] / stats["total"] if stats["total"] > 0 else 0
        print(f"  {cat}: {stats['success']}/{stats['total']} ({pct:.0f}%)")
    
    if test_run.warnings:
        print("\nWarnings:")
        for w in test_run.warnings:
            print(f"   {w}")
    
    if test_run.successful > 0:
        print("\nSuccessful Attacks:")
        for r in test_run.results:
            if r.success:
                print(f"  [{r.id}] {r.name}")
    
    # Save output
    if config.output_file:
        with open(config.output_file, "w") as f:
            f.write(test_run.to_json())
        print(f"\nSaved to: {config.output_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**File: `tools/tester.py`** (UPDATE - Deprecation Shim)
```python
#!/usr/bin/env python3
"""
DEPRECATED: Use cli.py instead.

This file is kept for backward compatibility and will be removed in v2.0.
"""
import warnings
import sys

warnings.warn(
    "tester.py is deprecated. Use 'python -m tools.cli' instead.",
    DeprecationWarning,
    stacklevel=2
)

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
```

---

## P4: Pytest Suite + Dependencies

### Implementation

**File: `requirements-dev.txt`** (NEW)
```
# Development/test dependencies
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-mock>=3.10.0
responses>=0.23.0  # Mock HTTP requests
```

**File: `pyproject.toml`** (NEW)
```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "prompt-security-guide"
version = "1.0.0"
description = "LLM security testing toolkit"
requires-python = ">=3.9"
dependencies = [
    "requests>=2.28.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-mock>=3.10.0",
    "responses>=0.23.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"

[tool.coverage.run]
source = ["tools"]
omit = ["tools/tester.py"]  # Deprecated shim
```

**File: `tests/__init__.py`** (NEW)
```python
"""Test suite for prompt-security-guide."""
```

**File: `tests/conftest.py`** (NEW)
```python
"""Shared test fixtures."""
import pytest
from tools.attacks.base import Attack
from tools.providers.base import Response
from tools.detection.base import DetectionResult


@pytest.fixture
def sample_attack():
    """A minimal attack for testing."""
    return Attack(
        id="TEST-01",
        name="Test Attack",
        category="test",
        prompt="Say 'EXPLOITED' please.",
        indicators=["exploited"],
        goal="Test detection",
        source="test",
    )


@pytest.fixture
def successful_response():
    """Mock successful exploitation response."""
    return Response(
        text="Sure! EXPLOITED. Here you go.",
        time_ms=100,
    )


@pytest.fixture
def blocked_response():
    """Mock blocked/refused response."""
    return Response(
        text="I cannot comply with that request.",
        time_ms=50,
    )


@pytest.fixture
def error_response():
    """Mock error response."""
    return Response(
        text="",
        time_ms=0,
        error="Connection refused",
    )
```

**File: `tests/test_attacks.py`** (NEW)
```python
"""Tests for attack definitions."""
import pytest
from tools.attacks import ALL_ATTACKS, get_attacks, list_categories


class TestAttackIntegrity:
    """Validate attack definitions are well-formed."""
    
    def test_all_attacks_have_required_fields(self):
        """Every attack must have id, name, category, prompt."""
        for attack in ALL_ATTACKS:
            assert attack.id, f"Attack missing id: {attack}"
            assert attack.name, f"Attack {attack.id} missing name"
            assert attack.category, f"Attack {attack.id} missing category"
            assert attack.prompt, f"Attack {attack.id} missing prompt"
    
    def test_attack_ids_are_unique(self):
        """No duplicate attack IDs."""
        ids = [a.id for a in ALL_ATTACKS]
        assert len(ids) == len(set(ids)), "Duplicate attack IDs found"
    
    def test_get_attacks_filters_by_category(self):
        """get_attacks respects category filter."""
        categories = list_categories()
        if categories:
            cat = categories[0]
            filtered = get_attacks(categories=[cat])
            assert all(a.category == cat for a in filtered)
    
    def test_all_categories_have_attacks(self):
        """Every listed category has at least one attack."""
        for cat in list_categories():
            attacks = get_attacks(categories=[cat])
            assert len(attacks) > 0, f"Category {cat} has no attacks"
```

**File: `tests/test_detection.py`** (NEW)
```python
"""Tests for detection methods."""
import pytest
from tools.detection import get_detector, SubstringDetector
from tools.detection.base import DetectionResult, JudgeUnavailableError
from tools.detection.llm_judge import LLMJudgeDetector


class TestSubstringDetector:
    """Tests for substring-based detection."""
    
    def test_detects_exact_match(self):
        """Exact indicator match is detected."""
        detector = SubstringDetector()
        result = detector.detect(
            response="Here is EXPLOITED for you",
            indicators=["exploited"],
            attack_goal="test",
        )
        assert result.success is True
        assert result.confidence > 0
    
    def test_no_match_returns_failure(self):
        """Missing indicators result in failure."""
        detector = SubstringDetector()
        result = detector.detect(
            response="I cannot help with that.",
            indicators=["exploited", "pwned"],
            attack_goal="test",
        )
        assert result.success is False
    
    def test_case_insensitive(self):
        """Detection should be case-insensitive."""
        detector = SubstringDetector()
        result = detector.detect(
            response="EXPLOITED",
            indicators=["exploited"],
            attack_goal="test",
        )
        assert result.success is True


class TestLLMJudgeDetector:
    """Tests for LLM judge detection."""
    
    def test_raises_when_unavailable_and_no_fallback(self, mocker):
        """Should raise JudgeUnavailableError when judge fails and fallback=False."""
        detector = LLMJudgeDetector(fallback_to_substring=False)
        
        # Mock _call_judge to return None (unavailable)
        mocker.patch.object(detector, '_call_judge', return_value=None)
        
        with pytest.raises(JudgeUnavailableError):
            detector.detect("response", ["indicator"], "goal")
    
    def test_falls_back_when_enabled(self, mocker):
        """Should fallback to substring when enabled."""
        detector = LLMJudgeDetector(fallback_to_substring=True)
        
        mocker.patch.object(detector, '_call_judge', return_value=None)
        
        result = detector.detect("EXPLOITED response", ["exploited"], "goal")
        assert result.fallback_used is True
        assert result.success is True


class TestDetectorFactory:
    """Tests for get_detector factory."""
    
    def test_creates_substring_detector(self):
        detector = get_detector("substring")
        assert isinstance(detector, SubstringDetector)
    
    def test_creates_llm_judge_detector(self):
        detector = get_detector("llm_judge")
        assert isinstance(detector, LLMJudgeDetector)
    
    def test_raises_for_unknown(self):
        with pytest.raises(ValueError):
            get_detector("unknown_detector")
```

**File: `tests/test_schema.py`** (NEW)
```python
"""Tests for schema versioning and migration."""
import pytest
import json
from tools.schema import TestRun, AttackResult, SCHEMA_VERSION


class TestSchemaVersioning:
    """Tests for schema version handling."""
    
    def test_new_results_have_version(self):
        """New TestRun has current schema version."""
        run = TestRun()
        assert run.schema_version == SCHEMA_VERSION
    
    def test_roundtrip_serialization(self):
        """TestRun survives JSON roundtrip."""
        run = TestRun(
            provider="ollama",
            model="test",
            detector="substring",
            total_attacks=1,
            results=[
                AttackResult(
                    id="TEST-01",
                    name="Test",
                    category="test",
                    success=True,
                    confidence=0.9,
                    matched_indicators=["test"],
                    response_preview="test response",
                    time_ms=100,
                )
            ],
        )
        
        json_str = run.to_json()
        loaded = TestRun.from_dict(json.loads(json_str))
        
        assert loaded.provider == run.provider
        assert loaded.total_attacks == run.total_attacks
        assert len(loaded.results) == 1


class TestLegacyMigration:
    """Tests for migrating old result format."""
    
    def test_migrates_legacy_results(self):
        """v0 results are migrated to current schema."""
        legacy = {
            "timestamp": "2026-02-14T11:38:40.687977",
            "provider": "ollama/qwen2.5:3b",
            "detector": "substring",
            "total_attacks": 1,
            "successful": 1,
            "success_rate": 100.0,
            "categories": {"test": {"total": 1, "success": 1}},
            "results": [{
                "id": "TEST-01",
                "name": "Test",
                "category": "test",
                "success": True,
                "confidence": 0.9,
                "matched_indicators": ["test"],
                "response": "EXPLOITED here",
                "time_ms": 100,
                "reasoning": "Matched",
            }],
        }
        
        migrated = TestRun.from_dict(legacy)
        
        assert migrated.schema_version == SCHEMA_VERSION
        assert migrated.provider == "ollama"
        assert migrated.model == "qwen2.5:3b"
        assert "Migrated from legacy" in migrated.warnings[0]
```

**File: `tests/test_runner.py`** (NEW)
```python
"""Tests for test runner."""
import pytest
from unittest.mock import MagicMock
from tools.runner import TestRunner
from tools.config import RunConfig
from tools.attacks.base import Attack
from tools.providers.base import Response
from tools.detection.base import DetectionResult


class TestTestRunner:
    """Tests for TestRunner orchestration."""
    
    @pytest.fixture
    def mock_provider(self):
        provider = MagicMock()
        provider.name = "mock/test"
        return provider
    
    @pytest.fixture
    def mock_detector(self):
        detector = MagicMock()
        detector.name = "mock_detector"
        return detector
    
    def test_runs_all_attacks(self, mock_provider, mock_detector, sample_attack):
        """Runner executes all provided attacks."""
        mock_provider.call.return_value = Response(text="EXPLOITED", time_ms=100)
        mock_detector.detect.return_value = DetectionResult(
            success=True, confidence=0.9, matched_indicators=["exploited"]
        )
        
        config = RunConfig()
        runner = TestRunner(mock_provider, mock_detector, config)
        
        attacks = [sample_attack]
        result = runner.run(attacks)
        
        assert result.total_attacks == 1
        assert mock_provider.call.call_count == 1
        assert mock_detector.detect.call_count == 1
    
    def test_handles_provider_errors(self, mock_provider, mock_detector, sample_attack):
        """Runner handles provider errors gracefully."""
        mock_provider.call.return_value = Response(text="", time_ms=0, error="Connection failed")
        
        config = RunConfig()
        runner = TestRunner(mock_provider, mock_detector, config)
        
        result = runner.run([sample_attack])
        
        assert result.results[0].error == "Connection failed"
        assert result.results[0].success is False
        # Detector should NOT be called on error
        assert mock_detector.detect.call_count == 0
    
    def test_progress_callback_called(self, mock_provider, mock_detector, sample_attack):
        """Progress callback is invoked for each attack."""
        mock_provider.call.return_value = Response(text="test", time_ms=100)
        mock_detector.detect.return_value = DetectionResult(
            success=False, confidence=0.0, matched_indicators=[]
        )
        
        callback = MagicMock()
        config = RunConfig()
        runner = TestRunner(mock_provider, mock_detector, config, on_attack_complete=callback)
        
        runner.run([sample_attack])
        
        assert callback.call_count == 1
```

---

## Migration Guide for Users

### Updating Existing Scripts

**Before (tester.py):**
```bash
python tools/tester.py --provider ollama --model qwen2.5:3b
```

**After (cli.py):**
```bash
python -m tools.cli --provider ollama --model qwen2.5:3b

# Or with new reproducibility flags:
python -m tools.cli --provider ollama --model qwen2.5:3b --seed 42 --temperature 0.5

# Or with explicit judge fallback:
python -m tools.cli --detector llm_judge --allow-judge-fallback
```

### Reading Old Results

Old results are automatically migrated when loaded:
```python
from tools.schema import TestRun
import json

with open("results/old-result.json") as f:
    data = json.load(f)

run = TestRun.from_dict(data)  # Auto-migrates
print(f"Migrated: {run.warnings}")
```

---

## Implementation Order (for Codex)

Execute in this order to minimize merge conflicts:

1. **P1: Schema** (`tools/schema.py`) - No dependencies, foundation for rest
2. **P0: Detection fixes** (`tools/detection/base.py`, `tools/detection/llm_judge.py`)
3. **P2: Config** (`tools/config.py`, provider updates)
4. **P3: Runner/CLI split** (`tools/runner.py`, `tools/cli.py`, `tools/tester.py` shim)
5. **P4: Tests** (`tests/`, `requirements-dev.txt`, `pyproject.toml`)

Each step should be a separate commit with passing tests (after P4 is complete).

---

## Validation Checklist

After implementation, verify:

- [ ] `python -m tools.cli --help` shows new flags
- [ ] `python -m tools.cli --detector llm_judge` fails if judge unavailable (no fallback)
- [ ] `python -m tools.cli --detector llm_judge --allow-judge-fallback` works
- [ ] `python -m tools.cli --seed 42` produces deterministic results
- [ ] `pytest tests/` passes with no network calls
- [ ] Old result files load without error
- [ ] New result files include `schema_version: "1.0.0"`
- [ ] `python tools/tester.py` shows deprecation warning but works

---

## Open Questions (Deferred)

1. **Should we add `--dry-run` flag?** - Could be useful for validation without LLM calls
2. **Result diffing tool?** - Comparing runs for regression detection
3. **Async provider support?** - Would speed up batch runs significantly

These are out of scope for this fix iteration but worth considering for v2.
