# PSG Pipeline Run — Plan v1

**Date:** 2026-05-07
**Branch:** (to be created from main)
**Scope:** Fix remaining SENIOR_CODE_REVIEW issues + improve codebase health

## Current State

- 502 tests passing, 1 skipped
- 1 ruff error: `logger` undefined in `psg/automation/daily_check.py:210`
- 7 pytest warnings (6x canary test, 1x torch deprecation)
- SENIOR_CODE_REVIEW: 12 MEDIUM + 2 LOW remaining

## Issues to Fix (Priority Order)

### Tier 1: Bugs & Correctness (must fix)
1. **M3. Silent JSON Parse Errors in Checkpoints** — `psg/checkpoint.py:28-31`
   - Bare except swallows errors silently → add logging + raise or return None explicitly
   - Test: malformed JSON raises/returns gracefully

2. **M4. Precision/Recall Return 0.0 for Undefined Cases** — `psg/eval.py:50-60`
   - Division by zero returns 0.0 silently → should log warning or return NaN/None
   - Test: zero denominator case

3. **Ruff F821: Undefined `logger` in daily_check.py** — `psg/automation/daily_check.py:210`
   - Missing logger definition → add module-level logger
   - Test: import works

### Tier 2: Security & Robustness (should fix)
4. **M2. Silent Skip of Invalid Catalog Items** — `psg/catalog.py:35-36`
   - Invalid items silently ignored → log warning with item details
   - Test: invalid item triggers warning, valid items pass

5. **M5. Fragile Refusal Pattern Detection** — `psg/security/classifier.py:18`
   - Hardcoded short refusal phrases → expand coverage + normalize
   - Test: non-English refusals, partial matches

6. **M10. Incomplete Secret Detection in Redaction**
   - Missing key formats → add Anthropic/GitHub/Google patterns (partially done per audit)
   - Test: new key formats detected

7. **M19. Fragile Code Block Extraction Regex** — 
   - Regex breaks on nested backticks/tilde → use ast or robust parser
   - Test: nested backticks, unclosed blocks

### Tier 3: Code Quality (nice to fix)
8. **M1. Code Duplication chat() / chat_multi_turn()** — `psg/llm/client.py:16-67`
   - Extract shared logic to private method, both call it
   - Test: both interfaces work identically

9. **M9. Print Statements Instead of Logging** — multiple files
   - Replace print() with logger calls
   - Test: no print() in non-CLI modules

10. **M12. Large Hardcoded PRESETS Dictionary** — 
    - Move to YAML/config file
    - Test: presets load from file, override works

11. **M14. Defense Report Code Duplication** —
    - Extract shared report generation
    - Test: report output unchanged

12. **L1. Finnish Comments in English Codebase** —
    - Translate or remove Finnish comments
    - No test needed (comments only)

## Acceptance Criteria

- [ ] All 502+ tests still pass
- [ ] 0 ruff errors
- [ ] No new warnings
- [ ] Each fix has corresponding test
- [ ] Tier 1 items all resolved
- [ ] Tier 2 items resolved where feasible
- [ ] Tier 3 items as time allows