# PSG Slop & Bloat Cleanup — Pipeline v3.1 Plan

## Scope Assessment
- **Files touched**: ~8-12 files in psg/
- **Estimated diff**: ~300-400 lines removed, ~0 added
- **Risk**: LOW (docstring/comment removal, no logic changes)
- **Path**: LIGHT (small change, low risk, ≤3 files with logic impact)

**BUT**: P5 will be requested because this touches classifier.py (security-critical).

## Findings

### 1. Redundant Docstrings (30+ functions)
Functions where the docstring just restates the function name:
- `create_app()` "Create FastAPI application"
- `health()` "Health check endpoint"
- `reset_metrics()` "Reset metrics (for testing)"
- `screen()` "Screen a single text for harmful content"
- `build_parser()` "Build argument parser for serve command"
- `load_golden()` "Load golden dataset from JSON file"
- `run_benchmark()` "Run a benchmark preset and return results"
- `_list_catalogs()` "List available attack catalogs with counts"
- `_list_plugins()` "List installed plugins"
- `add_defend_arguments()` "Add arguments for defend subcommand"
- ~20+ more in serve.py, defend.py, cli.py, execution/, benchmark.py

**Action**: Replace 1-line redundant docstrings with brief one-liners or remove where function name is self-documenting. Keep security-relevant docstrings (e.g., TOCTOU warning in validate_url).

### 2. Overly Long Docstrings
- `validate_url` (16L): Trim to ≤8L, keep TOCTOU warning
- `validate_cron_schedule` (11L): Trim to ≤5L
- `validate_input` (11L): Trim to ≤6L
- `detect_refusal` (11L): Trim to ≤6L (already has inline comments)
- `translate_leetspeak` (11L): Trim to ≤4L (self-explanatory)
- `translate_homoglyphs` (11L): Trim to ≤4L
- `decode_base64_segments` (11L): Trim to ≤4L
- `generate_summary_message` (10L): Trim to ≤5L
- `_extract_code_block` (10L): Keep (CommonMark spec reference, legitimately complex)

**Action**: Trim verbose docstrings. Remove arg/return documentation when type hints already convey meaning. Keep docstrings that document non-obvious behavior.

### 3. classifier.py at 905 Lines
- 121 blank lines, 105 comment lines, 679 code lines
- Pattern lists are inherently long but comments within them are sometimes redundant
- `# Redirect/offer patterns` comments useful (3 lines)
- Inline comments on patterns useful for maintenance
- Some pattern group comments are redundant restatements

**Action**: Condense by removing 3-4 redundant pattern group comments. Not a major reduction target. Target: ≤880 lines (realistic, still removing ~25 lines of fluff).

### 4. Non-Code Ratios
- defend.py: 558L total, 462 code, 96 non-code (17%) — acceptable
- input_validators.py: 386L, 271 code, 115 non-code (30%) — trimmable
- classifier.py: 905L, 679 code, 226 non-code (25%) — trimmable

### 5. AI Voice Patterns
SCAN RESULT: ZERO matches. No "It is important to note", "in order to", "Please note" patterns found. PSG codebase is already clean of AI filler phrases.

### 6. Test Integrity
- 581 tests collected, 580 passing, 1 skipped
- Test file docstrings should NOT be removed (they document test intent)
- Only psg/ source code docstrings are targets

## Plan

### Task 1: Trim redundant docstrings in serve.py, cli.py, benchmark.py
- Remove 1-line docstrings that just restate function name
- Keep Pydantic/FastAPI docstrings (they generate OpenAPI docs)

### Task 2: Trim redundant docstrings in defend.py, execution/*.py, catalog*.py
- Same pattern: remove obvious docstrings
- Keep `_extract_code_block` docstring (complex algorithm)

### Task 3: Trim verbose docstrings in validation.py, input_validators.py, classifier.py, normalize.py, reporter.py
- Trim each to essential information
- Keep TOCTOU warning, keep CommonMark reference
- Remove arg/return docs when type hints already document them

### Task 4: Light comment cleanup in classifier.py
- Remove 3-4 redundant pattern group comments
- Consolidate blank lines where excessive
- Target: ≤880 lines

### Task 5: Create git branch, commit changes
- Branch: fix/slop-cleanup-may2026
- Smoke test after each file change
- Full test suite at end

## Out of Scope (NOT doing)
- Removing modules (benchmark, catalog, integrations, checkpoint all have legitimate uses)
- Restructuring file organization
- Changing any function signatures or logic
- Removing __all__ exports
- Changing test files
- Removing any imports (they're all used per ruff check)