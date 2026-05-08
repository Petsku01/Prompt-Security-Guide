# PSG Pipeline Run 6 — Plan (P1)

**Branch:** fix/pipeline-run6-may2026
**Date:** 2026-05-08
**Baseline:** 576 tests passing, 1 skipped, ruff clean on psg/

## Identified Issues

### Tier 1 — Cleanup & Quality (should fix)

1. **13 ruff errors in tests/** — 11 unused imports (F401), 2 unused variables (F841)
   - Files: test_psg_automation_config.py, test_psg_automation_discovery.py,
     test_psg_automation_generator.py, test_psg_automation_main.py,
     test_psg_automation_reporter.py, test_psg_automation_tester.py,
     test_psg_automation_validation.py, test_psg_catalog_validator.py

2. **print→logger in automation** — 7 print() calls in non-CLI modules:
   - psg/automation/dedup.py:96 `print("Dedup tests passed!")`
   - psg/automation/reporter.py:282 `print(reporter.generate_markdown(report))`
   - psg/automation/discovery.py:234 `print(f"Discovered {len(sources)} new sources")`
   - psg/automation/generator.py:255 `print(...)`
   - psg/automation/tester.py:259,261 (ollama check)
   - psg/automation/daily_check.py:218,225,231 (CLI-like but in automation)

3. **1 TODO in source** — psg/automation/validation.py:69:
   "TODO: Pass resolved IPs to the HTTP client and enforce pinning"
   - This is an architectural note, not a bug. Convert to a tracked comment.

4. **eval.py print** — psg/eval.py:166 `print(f"Error loading golden dataset: {exc}", file=sys.stderr)`
   - Should use logger

### Tier 2 — Hardening (nice to have)

5. **serve.py prints** — 6 print() calls in psg/serve.py (lines 254-276)
   - These serve CLI output when FastAPI isn't installed. Acceptable as-is.

6. **cli.py prints** — Many print() calls in psg/cli.py
   - CLI module — print() is the correct output mechanism. Leave as-is.

## Plan

| # | Task | Files | Tests |
|---|------|-------|-------|
| 1 | Fix 13 ruff errors in test files | 8 test files | Existing (576) |
| 2 | print→logger in automation | dedup, reporter, discovery, generator, tester, daily_check, eval | New tests for logging |
| 3 | TODO→docstring note | validation.py | N/A |

## Acceptance Criteria

- All 576+ tests pass
- 0 ruff errors (psg/ AND tests/)
- No print() in non-CLI/serve psg modules
- Cross-model review before commit