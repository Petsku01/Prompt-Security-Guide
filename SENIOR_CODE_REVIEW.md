# Senior Code Review - Prompt Security Guide

**Date:** 2026-04-09  
**Reviewer:** Claude (Automated Senior Review)  
**Scope:** Full codebase review - architecture, security, bugs, code quality  
**Version reviewed:** v4.3.0 (commit 5828784)

---

## Executive Summary

Prompt Security Guide (PSG) is a well-structured, mature LLM security testing framework with ~105 Python modules, 349+ tests, and a clean CI/CD pipeline. The architecture shows good separation of concerns across CLI, orchestration, LLM transport, classification, and reporting layers.

However, this review identified **two interface bugs** in the crescendo and many-shot attack modules that cause silent degradation (not crashes — broad `except` handlers mask them), a **fail-open security design** in the LangChain integration, and several medium-severity issues around test quality, thread safety, and code consistency.

**Self-critique note:** The original version of this review contained false positives and overstated severities. It has been revised after verification against the actual code and test suite.

### Issue Summary

| Severity | Count | Description |
|----------|-------|-------------|
| **CRITICAL** | 2 | Interface bugs causing silent degradation |
| **HIGH** | 5 | Security design, thread safety, test quality |
| **MEDIUM** | 18 | Code smells, missing validation, inconsistencies |
| **LOW** | 7 | Style, naming, minor improvements |

---

## CRITICAL Issues

### C1. API Mismatch in Crescendo & Many-Shot — Silent Degradation **(FIXED)**

**Files:** `psg/execution/crescendo.py:96`, `psg/execution/many_shot.py:108`

Both modules called `detector.detect(response)`, but the `Detector` protocol (`psg/security/detectors.py:19-20`) only defines `classify()`. The `detect()` method does not exist on any real detector.

**Actual impact:** These do NOT crash the program. The calls are wrapped in `try: ... except Exception:` (crescendo line 95-104, many_shot line 107-116), so the `AttributeError` is silently caught and the code falls back to a weak refusal-phrase heuristic. This means **the security detector was never actually used** in these modules — every classification was done by simple string matching against 7 refusal phrases.

**Why tests didn't catch it:** Tests use `Mock()` objects which accept any method name. The mocks were set up as `detector.detect.return_value = ...`, matching the buggy code rather than the real `Detector` protocol.

**Fix applied:** Changed to `detector.classify(prompt, response)`, updated tests to mock `classify`.

---

### C2. Wrong Client Method in Crescendo & Many-Shot **(FIXED)**

**Files:** `psg/execution/crescendo.py:156-159`, `psg/execution/many_shot.py:147-150`

Both modules called `self.client.chat(messages=..., temperature=...)` but `OpenAICompatibleClient.chat()` takes `(model, prompt)` — not `messages`. They should use `chat_multi_turn(model, messages)`.

**Actual impact:** The `TypeError` from the wrong method signature is caught by the outer `except Exception as e:` handler (crescendo line 203, many_shot line 171), returning a failed result with the error message. The feature silently fails every time.

**Why tests didn't catch it:** Same Mock() issue — `Mock.chat()` accepts any kwargs.

**Fix applied:** Changed to `client.chat_multi_turn(model=self.cfg.model, messages=..., temperature=...)`, updated tests.

---

### ~~C3. Incorrect Blocked-Attacks Calculation~~ RETRACTED

**Original claim:** `blocked = total_succeeded - total_flagged` was wrong.

**Correction:** After verifying `RunSummary` construction in `orchestrator.py:68-74`:
- `succeeded` = attacks that got a response (no error)
- `flagged` = attacks where harmful content was detected
- `blocked = succeeded - flagged` = attacks with safe responses

This is **correct logic**. The original review was wrong.

---

### ~~C5. IndexError Risk in Crescendo~~ RETRACTED

**Original claim:** `turns[-1]` would crash if loop never executes.

**Correction:** Line 200 actually reads `turns[-1].assistant_response if turns else ""`. The ternary guard handles the empty case. No bug.

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

### H3. ClassifierDetectorPlugin Ignores Threshold Parameter **(FIXED)**

**File:** `psg/plugins/builtin.py:32-39`

The `threshold` parameter was accepted and stored but never used. Detection used `result.attack_successful` (which has its own internal threshold) instead of comparing `result.harm_score >= self.threshold`.

**Fix applied:** Changed to `attack_successful=result.harm_score >= self.threshold`.

---

### ~~H4. Race Condition in Parallel Execution Counter~~ RETRACTED

**Original claim:** Counter checked outside lock.

**Correction:** Both `completed += 1` and the `if completed % 10 == 0` check happen inside the `with checkpoint_lock:` block. No race condition exists.

---

### H5. Bare `except Exception` Catches Too Broadly

**Files:** `psg/__main__.py:127-128, 140-141`

Multiple places use `except Exception:` to catch all errors and silently continue. This masked the C1/C2 interface bugs for the entire life of the crescendo and many-shot modules. Should catch specific exceptions (`json.JSONDecodeError`, `ValueError`, `OSError`, etc.).

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

### NEW: H-CI. CI Test Glob Misses Test Files **(FIXED)**

**File:** `.github/workflows/test.yml:30`

CI ran `python -m pytest tests/test_psg_*.py`, which excluded `test_crescendo.py`, `test_many_shot.py`, `test_benchmark.py`, `test_normalize.py`, `test_eval.py`, `test_serve.py`, `test_langchain.py`, `test_plugins.py`, and `test_html_report.py`. This is why the C1/C2 bugs were never caught — those tests literally never ran in CI.

**Fix applied:** Changed to `python -m pytest tests/`.

---

### NEW: H-TEST. Tests Use Mocks That Hide Interface Bugs

**Files:** `tests/test_crescendo.py`, `tests/test_many_shot.py`

Both test suites used `Mock()` objects for the detector and client. `Mock()` accepts any method call — so `detector.detect()` worked in tests even though the real `Detector` protocol only has `classify()`. The tests validated internal orchestrator logic but never verified integration with real interfaces.

**Lesson:** At least one test per module should use a real (or `spec=`-constrained) object instead of bare `Mock()`.

---

### NEW: H-STATE. Crescendo Orchestrator Not Reusable **(FIXED)**

**File:** `psg/execution/crescendo.py:64`

`self.history` was initialized in `__init__` but never reset in `execute()`. Calling `execute()` twice would carry conversation history from the first attack into the second.

**Fix applied:** Added `self.history = []` at the start of `execute()`.

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

### ~~M16. Score Weighting Doesn't Sum to 1.0~~ RETRACTED

**Original claim:** Combined score can exceed 1.0.

**Correction:** The actual code is `min(1.0, (ml_score * 0.6) + (pattern_score * 0.3) + canary_score)`. The `min(1.0, ...)` explicitly caps the result. Not a bug.

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

### L4. CI Only Tests `test_psg_*.py` Pattern **(FIXED)**

Moved to HIGH severity as H-CI. Fixed by changing glob to `tests/`.

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

### DONE in this review cycle
1. ~~Fix `detector.detect()` -> `detector.classify()` in crescendo.py and many_shot.py~~ DONE
2. ~~Fix `client.chat()` -> `client.chat_multi_turn()` with `model` parameter~~ DONE
3. ~~Expand CI test glob to include all test files~~ DONE
4. ~~Fix ClassifierDetectorPlugin to use its threshold~~ DONE
5. ~~Fix hardcoded version in text_report.py~~ DONE
6. ~~Fix crescendo state leakage (history not reset)~~ DONE
7. ~~Update tests to use correct interfaces~~ DONE

### Remaining (P1) - Security and correctness
8. Change LangChain middleware from fail-open to fail-closed (or make configurable)
9. Add thread safety to WildGuard singleton
10. Wire crescendo/many_shot into the main pipeline or document as standalone tools
11. Add `spec=` constraints to test Mocks to catch future interface mismatches

### Remaining (P2) - Code quality
12. Replace bare `except Exception` with specific exception types
13. Add logging instead of print statements
14. Extract duplicated code in client.py and html_report.py

---

## Self-Critique of This Review

This review was revised after critical self-examination. The original version contained:

**False positives retracted:**
- C3 (benchmark calculation) — was correct logic, not a bug
- C5 (IndexError risk) — ternary guard existed, missed on first read
- H4 (parallel race condition) — counter was inside the lock
- M16 (score weighting) — `min(1.0, ...)` caps the result

**Severity overstatements corrected:**
- C1/C2 described as "will crash at runtime" — actually caught by `except Exception` handlers, causing silent degradation (arguably worse, but different impact)
- C4 (hardcoded version) downgraded from CRITICAL to LOW — cosmetic issue

**Important findings added after self-review:**
- H-CI: CI test glob was the root cause of C1/C2 going undetected
- H-TEST: Mock-based tests masked interface bugs
- H-STATE: Crescendo orchestrator had state leakage between runs
- Crescendo/many_shot modules are not wired into the main pipeline at all

**Meta-lesson:** Delegating review to sub-agents without independent verification led to false positives. Running the test suite — something a senior reviewer should always do — would have revealed the Mock masking pattern immediately.

---

*Review generated from full codebase analysis of 105 Python modules, 32 test files, CI/CD configuration, Dockerfile, and project configuration. Revised after self-critique and verification.*
