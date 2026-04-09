# Senior Code Review - Prompt Security Guide

**Date:** 2026-04-09  
**Reviewer:** Claude (Automated Senior Review)  
**Scope:** Full codebase review - architecture, security, bugs, code quality  
**Version reviewed:** v4.3.0 (commit 5828784)

---

## Executive Summary

Prompt Security Guide (PSG) is a well-structured, mature LLM security testing framework with ~105 Python modules, 349+ tests, and a clean CI/CD pipeline. The architecture shows good separation of concerns across CLI, orchestration, LLM transport, classification, and reporting layers.

However, this review identified **several critical runtime bugs** that will cause crashes in the crescendo and many-shot attack modules, a **logic error in benchmark reporting**, a **fail-open security design** in the LangChain integration, and numerous medium-severity issues around error handling, type safety, and thread safety.

### Issue Summary

| Severity | Count | Description |
|----------|-------|-------------|
| **CRITICAL** | 5 | Runtime crashes, logic bugs in core features |
| **HIGH** | 10 | Security design flaws, thread safety, data correctness |
| **MEDIUM** | 20 | Code smells, missing validation, inconsistencies |
| **LOW** | 8 | Style, naming, minor improvements |

---

## CRITICAL Issues

### C1. API Mismatch in Crescendo & Many-Shot Attacks (Will Crash at Runtime)

**Files:** `psg/execution/crescendo.py:96`, `psg/execution/many_shot.py:108`

Both modules call `detector.detect(response)`, but the `Detector` protocol (`psg/security/detectors.py:19-20`) only defines `classify()`:

```python
class Detector(Protocol):
    def classify(self, prompt: str, response: str) -> ClassificationResult: ...
```

The `detect()` method does not exist on any detector implementation (`KeywordDetector`, `LLMJudgeDetector`, `EnsembleDetector`). This will raise `AttributeError` at runtime every time crescendo or many-shot attacks are used.

**Fix:** Change `detector.detect(response)` to `detector.classify(prompt, response)` in both files.

---

### C2. Wrong Client Method in Crescendo & Many-Shot (Will Crash at Runtime)

**Files:** `psg/execution/crescendo.py:156-159`, `psg/execution/many_shot.py:147-150`

Both modules call:
```python
response_data = self.client.chat(
    messages=messages,
    temperature=self.temperature,
)
```

But `OpenAICompatibleClient.chat()` (`psg/llm/client.py:16-24`) has this signature:
```python
def chat(self, *, model: str, prompt: str, system_prompt: str | None = None, ...) -> LLMResponse:
```

Two problems:
1. `messages` is not a valid parameter for `chat()` — they should be calling `chat_multi_turn()`
2. The required `model` keyword argument is missing entirely

This will raise `TypeError` at runtime.

**Fix:** Use `self.client.chat_multi_turn(model=self.model, messages=messages, temperature=self.temperature)` or pass the model from config.

---

### C3. Incorrect Blocked-Attacks Calculation in Benchmarks

**File:** `psg/benchmark.py:223`

```python
blocked = total_succeeded - total_flagged
```

Context from lines 213-217:
- `total_succeeded += summary.succeeded` — this counts attacks where LLM responded (not errored)
- `total_flagged += summary.flagged` — this counts attacks flagged as harmful

The comment on line 222 says "blocked = attacks that were handled safely (refused)". The correct formula should be:

```python
blocked = total_succeeded - total_flagged  # only correct if succeeded means "got a response"
```

This depends on the semantics of `succeeded` vs `flagged`. If `succeeded` means the attack got through (harmful response), then `blocked` would be negative. The naming is ambiguous and the logic needs to be verified against `RunSummary` field definitions. At minimum, the field names are misleading.

---

### C4. Hardcoded Version in Text Report

**File:** `psg/reporting/text_report.py:13`

```python
lines = ["PSG v4.0.0 Report", ...]
```

Hardcoded as v4.0.0 while the project is at v4.3.0. This will perpetually be wrong. Should read from `pyproject.toml` or a version constant.

---

### C5. IndexError Risk in Crescendo Attack

**File:** `psg/execution/crescendo.py:200`

If the crescendo loop never executes (e.g., `max_turns=0`), accessing `turns[-1]` will raise `IndexError`.

---

## HIGH Severity Issues

### H1. Fail-Open Security in LangChain Integration

**File:** `psg/integrations/langchain.py:75-77`

```python
except Exception as exc:
    logger.warning("PSG classification failed for %s: %s", direction, exc)
    return  # Fail open - don't block on classifier errors
```

For a **security middleware**, failing open defeats its purpose. If the classifier crashes (OOM, import error, model corruption), all traffic passes through unscreened. A security tool should **fail closed** by default, with an explicit opt-in for fail-open behavior.

**Fix:** Default to raising (fail-closed), with a configurable `fail_open: bool = False` parameter.

---

### H2. Thread-Unsafe Singleton in WildGuard Classifier

**File:** `psg/security/wildguard_classifier.py:222-231`

```python
_classifier: Optional[WildGuardClassifier] = None

def get_wildguard_classifier() -> WildGuardClassifier:
    global _classifier
    if _classifier is None:
        _classifier = WildGuardClassifier()
    return _classifier
```

Classic check-then-act race condition. Two threads can both see `_classifier is None` and both construct a new instance. With GPU model loading, this could cause OOM or double model allocation.

**Fix:** Use `threading.Lock()` or `functools.lru_cache(maxsize=1)`.

---

### H3. ClassifierDetectorPlugin Ignores Threshold Parameter

**File:** `psg/plugins/builtin.py:32-39`

```python
def __init__(self, threshold: float = 0.5) -> None:
    self.threshold = threshold

def detect(self, prompt: str, response: str) -> DetectionResult:
    result = classify_response_v2(response)
    return DetectionResult(
        attack_successful=result.attack_successful,  # ignores self.threshold
```

The `threshold` parameter is accepted and stored but never used. The detection result uses `result.attack_successful` which has its own internal threshold. Users configuring a custom threshold get silently ignored.

---

### H4. Race Condition in Parallel Execution Counter

**File:** `psg/execution/parallel.py:76`

The `completed` counter is incremented inside a lock but checked outside it (`if completed % 10 == 0`), creating a data race. While CPython's GIL makes this unlikely to cause visible corruption, it's still incorrect and non-portable.

---

### H5. Bare `except Exception` Catches Too Broadly

**Files:** `psg/__main__.py:127-128, 140-141`, `psg/execution/crescendo.py:98`, `psg/execution/many_shot.py:110`

Multiple places use `except Exception:` to catch all errors and silently continue. This masks real bugs (e.g., `TypeError` from the API mismatch bugs above). Should catch specific exceptions.

---

### H6. No Exception Handling for uvicorn.run()

**File:** `psg/serve.py:269-274`

If the port is in use or permissions are denied, `uvicorn.run()` will crash with an unhandled `OSError`. Should wrap in try/except for a graceful error message.

---

### H7. Dummy Type Stubs Bypass Type Checking

**File:** `psg/serve.py:28-31`

```python
except ImportError:
    FASTAPI_AVAILABLE = False
    class BaseModel:  # type: ignore
        pass
```

Creates fake classes at runtime that bypass mypy. Should use `TYPE_CHECKING` blocks instead.

---

### H8. `custom_detectors or None` Semantic Bug

**File:** `psg/defenses/__init__.py:138`

```python
custom_detectors=self.custom_input_detectors or None,
```

An empty list `[]` is falsy in Python, so it gets replaced with `None`. This means "I explicitly configured zero custom detectors" is treated the same as "I didn't configure custom detectors at all". Semantically wrong.

---

### H9. Canary Token Not Normalized Before Comparison

**File:** `psg/defenses/input_validators.py:263`

Input text is normalized (homoglyphs, encoding, etc.) before checking for canary tokens, but the canary tokens themselves are not normalized. If a canary contains characters affected by normalization, it will never be found.

---

### H10. Benchmark Hardcodes `allow_insecure_http=True`

**File:** `psg/benchmark.py:203`

All benchmarks force `allow_insecure_http=True`, bypassing SSRF protection. This should at minimum log a warning, and ideally be configurable.

---

## MEDIUM Severity Issues

### M1. Code Duplication Between `chat()` and `chat_multi_turn()`

**File:** `psg/llm/client.py:16-67`

These two methods are nearly identical (endpoint construction, headers, payload building). Should extract shared logic into a private method.

### M2. Silent Skip of Invalid Catalog Items

**File:** `psg/catalog.py:35-36`

Non-dict, non-string items in catalogs are silently skipped with `continue`. Should log a warning.

### M3. Silent JSON Parse Errors in Checkpoints

**File:** `psg/checkpoint.py:28-31`

Corrupted checkpoint lines are silently skipped. Should log count of skipped records.

### M4. Precision/Recall Return 0.0 for Undefined Cases

**File:** `psg/eval.py:50-60`

When TP=0 and FP=0, precision returns 0.0 instead of `float('nan')`. Mathematically undefined. Same for recall.

### M5. Fragile Refusal Pattern Detection

**File:** `psg/security/classifier.py:18`

The refusal regex is extremely broad — `\b(cannot|can't) (help|assist|provide)\b` matches legitimate partial refusals like "I cannot provide medical advice, but here's a link..." producing false positives.

### M6. PII Regex Patterns Have High False Positive Rate

**File:** `psg/security/classifier.py:144-148`

- SSN pattern `\d{3}-\d{2}-\d{4}` matches product codes, dates
- Phone pattern only matches US numbers
- Email pattern is overly permissive

### M7. Magic Numbers in Harm Score Calculation

**File:** `psg/security/classifier.py:488-558`

Multiple hardcoded thresholds (0.5, 0.2, 0.05, 0.25) with no documentation or configuration. The scoring logic has arbitrary caps (`min(0.2, len(harmful_labels) * 0.05)`) that are non-intuitive.

### M8. `max_tokens=8` Too Small for LLM Judge

**File:** `psg/security/llm_judge.py:82`

Judge only gets 8 tokens to output "SAFE" or "HARMFUL". If the model outputs extra text like "The response is SAFE", it gets truncated and parsed as "UNKNOWN".

### M9. Print Statements Instead of Logging

**Files:** `psg/security/wildguard_classifier.py:63`, `psg/plugins/base.py:112`, `psg/automation/tester.py:144,154,165`

Library code should use the `logging` module, not `print()`. Print statements can't be suppressed, filtered, or routed to log aggregators.

### M10. Incomplete Secret Detection in Redaction

**File:** `psg/security/redaction.py:10`

Only detects OpenAI (`sk-`) and AWS (`AKIA`) key formats. Missing Anthropic, GCP, Azure, GitHub tokens, and other common formats.

### M11. Unnecessary List Unpacking

**File:** `psg/cli.py:75-76`

```python
scan_args = [*args[1:]]
```

`args[1:]` is already a list; unpacking and re-wrapping is redundant.

### M12. Large Hardcoded PRESETS Dictionary

**File:** `psg/benchmark.py:28-122`

95 lines of hardcoded preset config. Should be loaded from a YAML/JSON file for maintainability.

### M13. Redundant Type Coercion

**File:** `psg/config.py:49-51`

The type hint says `RedactionMode` but then checks `isinstance` and coerces from string. This masks a design issue — either the type hint is wrong or validation should happen earlier.

### M14. Defense Report Code Duplication

**File:** `psg/cli.py:200-240`

Defense-only validation logic duplicates code from `psg/defend.py`. Should import and reuse.

### M15. HTML Report Code Duplication

**File:** `psg/reporting/html_report.py:299-315`

Duplicates lines 261-277 exactly. Should be extracted into a helper.

### M16. Score Weighting Doesn't Sum to 1.0

**File:** `psg/defenses/input_validators.py:330`

```python
combined = (ml_score * 0.6) + (pattern_score * 0.3) + canary_score
```

Weights sum to 0.9 before canary_score. If canary_score is 0.5, total can exceed 1.0.

### M17. Emoji in CLI Output

**File:** `psg/benchmark.py:335-339`

Emojis may not render on all terminals (especially CI/CD). Should detect capabilities or provide ASCII fallback.

### M18. Canary Token Leakage Detection Breaks After First Token

**File:** `psg/defenses/__init__.py:154-161`

The loop breaks after finding the first leaked canary token. Multiple tokens could be leaked simultaneously but only the first is reported.

### M19. Fragile Code Block Extraction Regex

**File:** `psg/defenses/templates.py:72`

```python
r'```\n?(.*?)```'
```

Fails on code blocks with language identifiers like ` ```python`.

### M20. Hash Truncation Increases Collision Risk

**File:** `psg/automation/dedup.py:11`

Uses first 16 chars of SHA256 (`hexdigest()[:16]`), reducing collision space from 2^256 to 2^64.

---

## LOW Severity Issues

### L1. Finnish Comments in English Codebase

**File:** `psg/security/classifier.py:25,30,35`

Comments like "Politiikkaviittaukset", "Haitallisuusviittaukset" mixed with English code. Should be consistent.

### L2. Inconsistent `Optional[]` vs `| None` Style

**File:** `psg/security/wildguard_classifier.py:18,223`

Uses `Optional[WildGuardClassifier]` while the rest of the codebase uses `X | None`.

### L3. IMPROVEMENT_PLAN.md Written in Finnish

**File:** `IMPROVEMENT_PLAN.md`

The improvement plan is in Finnish while all other documentation is in English.

### L4. CI Only Tests `test_psg_*.py` Pattern

**File:** `.github/workflows/test.yml:30`

Tests matching `test_psg_*.py` skip files like `test_crescendo.py`, `test_many_shot.py`, `test_benchmark.py`, etc. This means the crescendo/many-shot bugs above are not caught by CI.

### L5. Dockerfile Layer Caching Suboptimal

**File:** `Dockerfile:19-22`

Full COPY before pip install invalidates the cache on any file change. Should copy only `pyproject.toml` first, install deps, then copy source.

### L6. `--ignore-missing-imports` in mypy CI Step

**File:** `.github/workflows/test.yml:45`

Suppresses real type errors from third-party packages. Should allowlist specific packages instead.

### L7. No Coverage Reporting in CI

**File:** `.github/workflows/test.yml`

`pytest-cov` is in dev dependencies but CI doesn't use `--cov` or upload coverage reports.

### L8. Missing `@functools.wraps` on Retry Decorator

**File:** `psg/automation/discovery.py:40-57`

The `retry()` decorator doesn't preserve the wrapped function's metadata.

---

## Architectural Observations

### What's Done Well

1. **Clean module boundaries** - CLI, orchestration, transport, classification, and reporting are well-separated
2. **Protocol-based detector abstraction** - Good use of `typing.Protocol` for detector interface
3. **SSRF protection** - URL validation is in place for config-level URLs
4. **Path traversal protection** - `..` in paths is properly rejected
5. **Comprehensive test coverage** - 349+ tests across 32 files
6. **CI pipeline** - Multi-version Python testing, linting, type checking, regression gates
7. **Defense-in-depth** - Input validation, output validation, canary tokens, multiple detector types

### Areas for Improvement

1. **Error handling philosophy** - Too many silent `except Exception: continue` patterns. A security tool should be noisy about failures, not silent.
2. **Configuration over hardcoding** - Magic numbers in scoring, thresholds, and retry logic should be configurable.
3. **Logging discipline** - Mix of `print()` and `logging`. Should standardize on `logging` throughout.
4. **Test coverage of newer modules** - CI test glob misses crescendo, many-shot, and benchmark test files. These modules have critical bugs that would be caught by CI if the tests ran.
5. **Thread safety** - Several global singletons and shared state without synchronization.

---

## Recommended Priority for Fixes

### Immediate (P0) - Will cause runtime crashes
1. Fix `detector.detect()` -> `detector.classify()` in crescendo.py and many_shot.py
2. Fix `client.chat()` -> `client.chat_multi_turn()` with `model` parameter in both files
3. Expand CI test glob to include all test files

### This Week (P1) - Security and correctness
4. Change LangChain middleware from fail-open to fail-closed
5. Add thread safety to WildGuard singleton
6. Fix benchmark blocked-attacks calculation
7. Fix ClassifierDetectorPlugin to use its threshold parameter

### This Sprint (P2) - Code quality
8. Replace `except Exception` with specific exception types
9. Add logging instead of print statements
10. Fix score weighting to sum to 1.0
11. Normalize canary tokens before comparison
12. Extract duplicated code in client.py and html_report.py

---

*Review generated from full codebase analysis of 105 Python modules, 32 test files, CI/CD configuration, Dockerfile, and project configuration.*
