# PSG Audit Run 8 Re-verify — Plan

**Pipeline ID**: psg-audit-run8-reverify-2026-05-10
**Date**: 2026-05-10
**Path**: Heavy (24 files, 296 insertions, security-relevant changes)
**Reason for Heavy**: >3 files, security fixes (PII logging, URL sanitization), assert tautology fixes

## Scope

Audit and verify the Run 8 P2+P3 commits before pushing to origin/main:
- `67c6b3c` — P1 audit plan + acceptance tests
- `6515778` — P2: swallowed exceptions + logging + assertions + type annotations
- `8affd3d` — P3: cross-model review fixes

## P1 Quality Audit Findings

| # | Finding | Severity | Location |
|---|---------|----------|----------|
| QA1 | assert True tautology | HIGH | test_psg_automation_config.py:170 |
| QA2 | assert True tautology (in skipped test) | LOW | test_psg_defend.py:214 |
| QA3 | print() in eval.py (CLI, acceptable) | LOW | psg/eval.py |
| QA4 | print() in benchmark.py (CLI, acceptable) | LOW | psg/benchmark.py |
| QA5 | TODO(security): IP pinning | LOW | psg/automation/validation.py:58 |
| QA6 | Credential logging verified — counts not values | CONFIRMED FIXED | psg/defenses/output_validators.py |
| QA7 | URL sanitization verified — _sanitize_url strips userinfo | CONFIRMED FIXED | psg/validation/online.py |

## Actions

### P2: Fix remaining issues
1. Replace `assert True` in test_psg_automation_config.py:170 with actual result assertion
2. test_psg_defend.py:214 — skipped test, mark with `pytest.mark.skip` only (assert True is unreachable, LOW priority)
3. Run quality audit scan (ruff + py_compile + import) on all changed files

### P3: Cross-model ensemble review
- Reviewers: kimi-k2.6 (Security), deepseek-v4-pro (Architect)
- Focus: verify P3 fixes are correct, no new regressions, no missed PII leaks

### P4: Full test suite + regression comparison
- Verify 580 pass, 0 fail, 0 ruff errors
- Compare with last-test-results.json

### P5: Adversarial review
- Reviewer: qwen3.5 (different model family)
- Focus: edge cases in logging, URL sanitization bypasses, assertion completeness