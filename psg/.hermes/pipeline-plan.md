# PSG Auto Vector Pipeline — Implementation Plan

## Status: Complete assessment of existing code + concrete task list

---

## 1. Module Assessment

### config.py — WORKS, mostly complete
- `PipelineConfig` dataclass: all fields present, defaults sensible
- `load_config()`: loads from YAML or returns defaults — works
- `validate_environment()`: checks scrapling venv — works but only validates scrapling, not Ollama
- `__post_init__`: creates dirs — works
- **Issues:**
  - `load_config()` crashes on unknown YAML keys (TypeError from dataclass) — no validation/filtering of input keys
  - `validate_environment()` is never called from the pipeline except in `main.py` for non-skip-discovery, and it only checks scrapling (should also check Ollama reachability as a soft check)
  - No `config.yaml` file exists — pipeline has never been configured via YAML
- **Test coverage:** 2 tests (empty YAML, None path) — insufficient

### dedup.py — WORKS, complete
- `DeduplicationStore`: SHA256 hashing, batch writes, flush, persistence — all functional
- `hash_text()`: normalization (strip, lower, truncate to 16 chars) — works
- `add_many()`: bulk add — works
- **Issues:**
  - `hash_text` truncates to 16 hex chars — acceptable but collision risk for large stores (not a bug, just a limit)
  - No method to remove hashes (not needed per spec)
- **Test coverage:** 2 tests (batch threshold, flush) — missing: persistence round-trip, `add_many`, `is_known`, duplicate detection, `hash_text` determinism, empty file load

### discovery.py — WORKS, mostly complete
- `Source` dataclass + `to_dict()` — works
- `DiscoveryEngine.discover()` — works with mocked search_func
- `retry` decorator — works
- `create_search_func()` — works (calls external scrapling script)
- `fetch_page_content()` — works (openclaw + requests fallback)
- `save_sources()` — works
- **Issues:**
  - `fetch_page_content()` is never called by `discover()` — the engine discovers URLs but never fetches page content. The generator only gets `title` + `snippet` from search results, not full page content. This is a design gap — the spec says the generator should analyze sources, but only snippets are available.
  - `default_search_func` creates a new config on every call — wasteful but not broken
  - The `retry` decorator swallows the type signature of the wrapped function (no `functools.wraps`)
  - `discover()` hardcodes `max_sources=10` instead of using `max_sources_per_query` properly (it limits total sources to 10, not per-query to the config value)
- **Test coverage:** 0 tests — critical gap

### generator.py — WORKS, mostly complete
- `AttackVector` dataclass + `to_dict()` — works
- `VectorGenerator` — functional with mock generate_func
- `_extract_json()` — robust extraction from LLM responses
- `_normalize_vectors()` — handles various JSON shapes
- `save_vectors()` — writes compatible JSON
- **Issues:**
  - `default_generate_func` hardcodes model `"dolphin-llama3:8b"` instead of using `config.generator_model`
  - `default_generate_func` hardcodes Ollama URL instead of using `config.ollama_base_url`
  - No tier assignment logic — all vectors get `tier="standard"` regardless of content
  - No validation that generated prompts aren't empty/garbage
- **Test coverage:** 0 tests — critical gap

### tester.py — WORKS, mostly complete
- `TestResult` dataclass + `to_dict()` — works
- `TestRunner.check_ollama()` — works (uses curl)
- `TestRunner.get_available_models()` — works
- `TestRunner.run_test()` — works (calls `psg` CLI)
- `TestRunner.run_all_tests()` — works
- `TestRunner.run_in_tmux()` — works (writes shell script + tmux session)
- **Issues:**
  - `run_test()` parses output by grepping `total=/succeeded=/failed=/flagged=` lines — brittle, depends on psg CLI output format
  - `run_test()` timeout is `test_timeout * 100` — arbitrary multiplier, should be configurable
  - `run_all_tests()` uses `print()` instead of `logger`
  - `check_ollama()` depends on `curl` being installed — should use `urllib` as fallback
  - `run_in_tmux()` writes a shell script to `base_dir/run_auto_test.sh` — leftover file, not cleaned up
- **Test coverage:** 0 tests — critical gap

### reporter.py — WORKS, mostly complete
- `PipelineReport` dataclass + `to_dict()` — works
- `Reporter.create_report()` — works
- `Reporter.generate_markdown()` — works
- `Reporter.generate_discord_message()` — works
- `Reporter.save_report()` — works
- **Issues:**
  - `top_findings` only summarizes by model, not by technique — spec says "top findings: [technique] flagged on [models]" but current impl just lists models by flag count
  - No actual Discord webhook sending — just generates the message, never sends it
  - `notify_discord` config flag exists but is never read
  - `generate_markdown()` doesn't include source URLs or technique breakdown
- **Test coverage:** 0 tests — critical gap

### main.py — WORKS, mostly complete
- `Pipeline` class: orchestrates all 4 phases — works
- CLI (`main()`) with `--tmux`, `--skip-discovery`, `--skip-generation`, `--vectors`, `--report-only`, `--verbose` — works
- Error handling: catches RuntimeError, KeyboardInterrupt, generic Exception — works
- **Issues:**
  - `run_full()` returns `None` when no vectors generated or when using tmux — caller can't distinguish these cases
  - `validate_environment()` only called when NOT skipping discovery — should always validate what's needed
  - No `--dry-run` option
  - No notification on failure (spec says "send failure notifications if needed")
  - `--report-only` creates empty sources/vectors/results — generates a meaningless report
- **Test coverage:** 0 tests — critical gap

### validation.py — COMPLETE, works well
- `validate_query()`, `validate_url()`, `sanitize_filename()` — all solid
- SSRF protection with blocked hosts/networks + DNS resolution check — works
- **Test coverage:** 3 tests — decent, could use more edge cases

### logging_config.py — COMPLETE, works
- `setup_logging()` with console + optional file handler — works
- Module-level `logger` instance — works
- No issues

### daily_check.py — COMPLETE, works
- Simple marker file check/mark — works
- Not integrated into pipeline (should be called by cron wrapper before running pipeline)
- **Test coverage:** 0 tests

---

## 2. Test Gap Analysis

### Existing automation tests (7 total):
| File | Tests | Status |
|------|-------|--------|
| `test_psg_automation_config.py` | 2 | Pass — insufficient coverage |
| `test_psg_automation_dedup.py` | 2 | Pass — insufficient coverage |
| `test_psg_automation_validation.py` | 3 | Pass — OK for validation.py |

### Modules with ZERO tests:
| Module | Priority | Risk |
|--------|----------|------|
| discovery.py | **CRITICAL** | Core pipeline phase, complex logic |
| generator.py | **CRITICAL** | Core pipeline phase, LLM interaction |
| tester.py | **HIGH** | Core pipeline phase, subprocess mgmt |
| reporter.py | **HIGH** | Core pipeline phase, output generation |
| main.py | **HIGH** | Orchestrator, integration point |
| daily_check.py | **LOW** | Simple utility |
| logging_config.py | **LOW** | Simple utility |

### Test approach:
- All external dependencies (Ollama, scrapling, tmux, curl, Discord) must be mocked
- Use `tmp_path` fixture for file I/O
- Use `monkeypatch` for env vars and external calls
- Tests must run without any external service running

---

## 3. Task List

### Phase 0: Foundation (dedup + validation — build confidence first)

#### Task 0.1: Expand dedup.py tests
- **Depends on:** None
- **Estimated time:** 5 min
- **Steps:**
  1. Write tests in `tests/test_psg_automation_dedup.py`:
     - `test_hash_text_is_deterministic` — same input → same hash
     - `test_hash_text_normalizes_case_and_whitespace` — `"Foo "` and `"foo"` same hash
     - `test_add_returns_true_for_new_item` — new text added
     - `test_add_returns_false_for_duplicate` — duplicate rejected
     - `test_is_known_returns_true_for_added_item` — round-trip check
     - `test_persistence_round_trip` — add, flush, reload from file → same hashes
     - `test_add_many_returns_count_of_new_items` — 3 new + 1 dup → count 3
     - `test_len_returns_hash_count` — after adding 5 unique items
     - `test_flush_noop_when_no_pending` — flush on clean store doesn't write
  2. Run tests — all should pass (dedup is already working)
- **Acceptance:** 9+ dedup tests all green

#### Task 0.2: Expand config.py tests
- **Depends on:** None
- **Estimated time:** 5 min
- **Steps:**
  1. Write tests in `tests/test_psg_automation_config.py`:
     - `test_default_config_has_search_queries` — default list non-empty
     - `test_default_config_has_test_models` — default list non-empty
     - `test_default_config_paths_are_path_objects` — all Path fields
     - `test_post_init_creates_directories` — uses tmp_path, checks dirs created
     - `test_load_config_from_yaml_file` — write a yaml with `max_vectors_per_run: 5`, load it, assert value
     - `test_load_config_unknown_keys_raises_typerror` — yaml with `bogus: true` raises TypeError (current behavior)
  2. Run tests
- **Acceptance:** 6+ config tests all green

#### Task 0.3: Expand validation.py tests
- **Depends on:** None
- **Estimated time:** 5 min
- **Steps:**
  1. Write tests in `tests/test_psg_automation_validation.py`:
     - `test_validate_query_rejects_empty` — ValueError
     - `test_validate_query_rejects_too_long` — ValueError for 201+ chars
     - `test_validate_query_strips_whitespace` — `" foo "` → `"foo"`
     - `test_validate_url_rejects_empty` — False
     - `test_validate_url_rejects_javascript_scheme` — False
     - `test_validate_url_accepts_https` — True (mock DNS to public IP)
     - `test_sanitize_filename_removes_special_chars` — `"a/b:c" → "a_b_c"`
     - `test_sanitize_filename_limits_length` — 101+ char name truncated
  2. Run tests
- **Acceptance:** 8+ validation tests all green

---

### Phase 1: Discovery tests + fixes

#### Task 1.1: Write discovery.py tests (mock search_func)
- **Depends on:** Task 0.1 (dedup is used by discovery)
- **Estimated time:** 10 min
- **Steps:**
  1. Create `tests/test_psg_automation_discovery.py`
  2. Write tests with a mock `search_func`:
     - `test_discover_returns_sources_from_search` — mock returns 2 results, expect 2 Source objects
     - `test_discover_skips_invalid_urls` — mock returns URL with `javascript:` scheme, expect 0 from that result
     - `test_discover_deduplicates_known_urls` — add URL to known_sources, mock returns same URL, expect 0 new
     - `test_discover_limits_total_sources` — mock returns 20 results, expect max 10 sources
     - `test_discover_uses_config_search_queries` — verify mock called once per query in config
     - `test_source_to_dict_roundtrip` — Source → dict → has all keys
     - `test_save_sources_writes_json` — save sources, read file back, verify structure
     - `test_discover_continues_on_search_failure` — mock raises Exception for first query, returns results for second
     - `test_discover_flushes_source_store` — verify source_store.flush() called
  3. Run tests — some may fail due to bugs found below
- **Acceptance:** 9 discovery tests written, may need fixes from 1.2

#### Task 1.2: Fix discovery.py bugs
- **Depends on:** Task 1.1
- **Estimated time:** 5 min
- **Steps:**
  1. Fix `discover()` to use `config.max_sources_per_query` per query, not hardcoded 10 total
     - Change the total limit to a separate `max_total_sources` (default 15) or just use `max_sources_per_query * len(queries)` as total cap
     - Actually simpler: keep the 10 hardcap but make it configurable via config
  2. Add `functools.wraps` to the `retry` decorator
  3. Keep `fetch_page_content` as-is (it's available but not used in discover — that's a design choice, not a bug)
  4. Re-run tests from 1.1
- **Acceptance:** All discovery tests pass

---

### Phase 2: Generator tests + fixes

#### Task 2.1: Write generator.py tests (mock generate_func)
- **Depends on:** Task 1.1 (uses Source dataclass)
- **Estimated time:** 12 min
- **Steps:**
  1. Create `tests/test_psg_automation_generator.py`
  2. Write tests with mock `generate_func`:
     - `test_generate_from_source_returns_vectors` — mock returns JSON array, expect AttackVector list
     - `test_generate_from_source_empty_response` — mock returns "", expect []
     - `test_generate_from_source_bad_json` — mock returns "not json", expect []
     - `test_generate_from_source_deduplicates_prompts` — same prompt in response → only one vector
     - `test_generate_from_source_respects_max_vectors` — mock returns 20 items, config max=3, expect 3
     - `test_generate_from_sources_processes_multiple` — 3 sources, vectors from each
     - `test_extract_json_from_code_block` — ````json\n[{"prompt":"x"}]\n``` ``
     - `test_extract_json_from_raw_array` — `[{"prompt":"x"}]`
     - `test_normalize_vectors_from_dict` — `{"vectors": [...]}` → list
     - `test_save_vectors_writes_json` — save, read back, verify structure
     - `test_vector_ids_are_sequential` — auto_YYYYMMDD_001, auto_YYYYMMDD_002
     - `test_generate_from_source_skips_empty_prompts` — mock returns `[{"prompt":"","technique":"x"}]`, expect 0 vectors
  3. Run tests
- **Acceptance:** 12 generator tests written

#### Task 2.2: Fix generator.py bugs
- **Depends on:** Task 2.1
- **Estimated time:** 8 min
- **Steps:**
  1. Fix `default_generate_func` to use `config.generator_model` and `config.ollama_base_url`
     - Change signature to accept config parameter or make it a method
     - Simplest fix: make `default_generate_func` read from env or make `VectorGenerator.__init__` pass config to the default func
     - Actually, the current design uses `GenerateFunc = Callable[[str], str]` which can't take config. Better approach: create the func from config in `__init__` if no func provided, similar to `create_search_func` in discovery
  2. Add validation: skip vectors with empty or whitespace-only prompts
  3. Re-run tests
- **Acceptance:** All generator tests pass, `default_generate_func` uses config settings

---

### Phase 3: Reporter tests + fixes

#### Task 3.1: Write reporter.py tests
- **Depends on:** Task 2.1 (uses AttackVector dataclass)
- **Estimated time:** 10 min
- **Steps:**
  1. Create `tests/test_psg_automation_reporter.py`
  2. Write tests:
     - `test_create_report_counts_sources_and_vectors` — pass 3 sources, 5 vectors, 2 results
     - `test_create_report_totals_flagged` — TestResult with flagged=3, expect total_flagged=3
     - `test_create_report_top_findings_sorted_by_flagged` — 3 results with different flagged counts
     - `test_create_report_empty_results` — 0 results → empty top_findings
     - `test_generate_markdown_contains_summary` — check key headings and numbers
     - `test_generate_markdown_contains_model_table` — check table rows
     - `test_generate_discord_message_format` — check emoji, key fields
     - `test_generate_discord_message_high_flagged_uses_warning_emoji` — 15 flagged → `[!]`
     - `test_save_report_creates_file` — save, check file exists with correct name
     - `test_pipeline_report_to_dict` — round-trip check
  3. Run tests
- **Acceptance:** 10 reporter tests written

#### Task 3.2: Fix reporter.py — top_findings by technique
- **Depends on:** Task 3.1
- **Estimated time:** 10 min
- **Steps:**
  1. Modify `create_report()` to extract technique-level findings from test result data
     - Current: only summarizes "model X flagged N" — no technique-level detail
     - Problem: `TestResult` doesn't carry per-vector results, only aggregate counts
     - Need to either: (a) parse the JSON report file from tester output, or (b) add per-vector data to `TestResult`
     - Pragmatic fix: parse the JSON report file from `TestResult.output_path` if it exists
     - Alternative: accept the limitation and document it — technique-level findings require parsing individual test results which isn't available in current TestResult structure
  2. For now, document this as a known limitation and skip the technique-level test
  3. Add Discord webhook sending stub (actual send requires webhook URL in config)
     - Add `send_discord_notification()` method
     - Reads `PSG_DISCORD_WEBHOOK` env var
     - POSTs the message if webhook URL is set and `notify_discord` is True
     - No-op if no webhook configured
  4. Fix `generate_discord_message` to match SPEC format more closely
  5. Re-run tests
- **Acceptance:** All reporter tests pass, Discord send is optional/best-effort

---

### Phase 4: Tester tests + fixes

#### Task 4.1: Write tester.py tests (heavy mocking)
- **Depends on:** Task 0.2 (uses PipelineConfig)
- **Estimated time:** 12 min
- **Steps:**
  1. Create `tests/test_psg_automation_tester.py`
  2. Write tests with mocked subprocess:
     - `test_check_ollama_returns_true_when_healthy` — mock subprocess.run → stdout="200"
     - `test_check_ollama_returns_false_when_down` — mock subprocess.run → raises
     - `test_get_available_models_parses_response` — mock curl response with model list
     - `test_get_available_models_returns_empty_on_error` — mock fails
     - `test_run_test_parses_output` — mock subprocess returning "total=5 succeeded=2 failed=1 flagged=2"
     - `test_run_test_returns_none_on_timeout` — mock TimeoutExpired
     - `test_run_all_tests_skips_unavailable_models` — mock available models ≠ config models
     - `test_run_all_tests_returns_empty_if_ollama_down` — mock check_ollama → False
     - `test_result_to_dict` — round-trip
  3. Run tests
- **Acceptance:** 9 tester tests written

#### Task 4.2: Fix tester.py issues
- **Depends on:** Task 4.1
- **Estimated time:** 8 min
- **Steps:**
  1. Replace `print()` calls with `logger` calls in `run_all_tests()`
  2. Add `urllib` fallback for `check_ollama()` (don't depend on curl)
  3. Clean up `run_auto_test.sh` after tmux session (or write to results_dir instead of base_dir)
  4. Make the output parsing more robust (handle missing fields gracefully)
  5. Re-run tests
- **Acceptance:** All tester tests pass, no print() in production code

---

### Phase 5: Main orchestrator tests + fixes

#### Task 5.1: Write main.py integration tests
- **Depends on:** Tasks 1.2, 2.2, 3.2, 4.2 (all module tests pass)
- **Estimated time:** 12 min
- **Steps:**
  1. Create `tests/test_psg_automation_main.py`
  2. Write tests with all external deps mocked:
     - `test_pipeline_run_full_with_mock_search` — mock search returns sources, mock generate returns vectors, mock tester returns results → full pipeline runs
     - `test_pipeline_run_discovery_saves_sources` — mock search, verify file written
     - `test_pipeline_run_generation_no_sources` — empty sources → empty vectors
     - `test_pipeline_run_testing_ollama_down` — mock check_ollama → False, returns []
     - `test_pipeline_run_reporting_saves_report` — verify report file created
     - `test_cli_skip_discovery` — `main(["--skip-discovery"])` with mock generate
     - `test_cli_verbose_flag` — `main(["-v"])` sets logger to DEBUG
     - `test_pipeline_run_full_no_vectors_returns_none` — no vectors from generation → None
     - `test_main_catches_runtime_error` — validate_environment raises → return 2
  3. Run tests
- **Acceptance:** 9 main tests written

#### Task 5.2: Fix main.py issues
- **Depends on:** Task 5.1
- **Estimated time:** 8 min
- **Steps:**
  1. Add failure notification — when pipeline fails, log error and optionally send Discord
  2. Add `--dry-run` flag — runs discovery + generation but skips testing
     - Actually, `--skip-discovery --skip-generation` already exist. Add `--dry-run` as alias for both
  3. Make `run_testing()` return meaningful result when using tmux (session name, not empty list)
  4. Re-run all tests
- **Acceptance:** All main tests pass

---

### Phase 6: Daily check + logging tests

#### Task 6.1: Write daily_check.py tests
- **Depends on:** None
- **Estimated time:** 5 min
- **Steps:**
  1. Create `tests/test_psg_automation_daily_check.py`
  2. Write tests:
     - `test_check_returns_run_needed_when_no_marker` — no file → "RUN_NEEDED"
     - `test_check_returns_already_run_when_today` — write today's date → "ALREADY_RUN"
     - `test_check_returns_run_needed_when_stale` — write yesterday's date → "RUN_NEEDED"
     - `test_mark_writes_today` — mark(), read file, verify today's date
     - `test_main_check_returns_0_if_already_run` — sys.exit 0
     - `test_main_check_returns_1_if_needed` — sys.exit 1
  3. Run tests
- **Acceptance:** 6 daily_check tests pass

#### Task 6.2: Write logging_config.py tests
- **Depends on:** None
- **Estimated time:** 3 min
- **Steps:**
  1. Create `tests/test_psg_automation_logging.py`
  2. Write tests:
     - `test_setup_logging_returns_logger` — check type
     - `test_setup_logging_with_file_handler` — tmp_path, check handler added
     - `test_setup_logging_idempotent` — call twice, same logger, no duplicate handlers
  3. Run tests
- **Acceptance:** 3 logging tests pass

---

### Phase 7: End-to-end validation

#### Task 7.1: Full test suite run
- **Depends on:** All prior tasks
- **Estimated time:** 3 min
- **Steps:**
  1. Run `python -m pytest tests/test_psg_automation*.py -v --tb=short`
  2. Verify all tests pass
  3. Run `python -m pytest tests/test_psg_automation*.py --cov=psg.automation --cov-report=term-missing`
  4. Target: >80% coverage on all automation modules
- **Acceptance:** All tests green, coverage >80%

#### Task 7.2: Smoke test pipeline import and CLI
- **Depends on:** Task 7.1
- **Estimated time:** 3 min
- **Steps:**
  1. `python -c "from psg.automation import Pipeline, PipelineConfig"` — verify import
  2. `python -m psg.automation --help` — verify CLI
  3. `python -m psg.automation --skip-discovery --skip-generation --report-only` — dry run
- **Acceptance:** No import errors, CLI help works, dry run completes

---

## 4. Dependency Graph

```
Task 0.1 (dedup tests)     ──┐
Task 0.2 (config tests)    ──┤
Task 0.3 (valid. tests)    ──┤
                             ├──→ Task 1.1 (discovery tests) ──→ Task 1.2 (discovery fixes)
                             │         │
                             │         ├──→ Task 2.1 (generator tests) ──→ Task 2.2 (generator fixes)
                             │         │         │
                             │         │         ├──→ Task 3.1 (reporter tests) ──→ Task 3.2 (reporter fixes)
                             │         │
                             ├──→ Task 4.1 (tester tests) ──→ Task 4.2 (tester fixes)
                             │
Task 6.1 (daily_check tests) ─┤
Task 6.2 (logging tests)   ──┤
                             │
                             └──→ Task 5.1 (main tests) ──→ Task 5.2 (main fixes)
                                    │
                                    └──→ Task 7.1 (full suite) ──→ Task 7.2 (smoke test)
```

Parallelizable groups:
- **Group A (no deps):** 0.1, 0.2, 0.3, 6.1, 6.2
- **Group B (after Group A):** 1.1, 4.1
- **Group C (after 1.1):** 1.2, 2.1
- **Group D (after 1.2, 2.1):** 2.2, 3.1
- **Group E (after 3.1):** 3.2
- **Group F (after all modules):** 4.2, 5.1
- **Group G (after 5.1):** 5.2
- **Group H (after all):** 7.1, 7.2

---

## 5. Summary of Bugs to Fix

| # | Module | Bug | Severity |
|---|--------|-----|----------|
| 1 | discovery.py | `retry` decorator missing `functools.wraps` | Low |
|  2 | discovery.py | Hardcoded total cap at 10, not configurable. `max_sources_per_query` used per-query but total cap not in config | Medium |
| 3 | generator.py | `default_generate_func` ignores `config.generator_model` and `config.ollama_base_url` | High |
| 4 | generator.py | No validation for empty/whitespace prompts in generated vectors | Medium |
| 5 | reporter.py | `top_findings` only by model, not by technique (spec mismatch) | Medium |
| 6 | reporter.py | No Discord webhook sending (just generates message) | Medium |
| 7 | reporter.py | `notify_discord` config flag never read | Low |
|  8 | tester.py | Uses `print()` instead of `logger` in `run_all_tests()` AND `run_test()` (5 print calls total) | Low |
|  9 | tester.py | Depends on `curl` binary for both `check_ollama()` AND `get_available_models()` | Medium |
| 10 | tester.py | Writes `run_auto_test.sh` to base_dir, never cleaned up | Low |
| 11 | main.py | No failure notification (spec: "send failure notifications if needed") | Medium |
| 12 | main.py | `run_full()` returns None for both "no vectors" and "tmux" — ambiguous | Low |
| 13 | generator.py | `generate_from_source()` uses `max_vectors_per_run` as per-source cap; single source can consume entire run budget | Medium |
| 14 | tester.py | Timeout multiplier 100x is dangerous (default 120s → 12000s = 3.3h per test if model hangs) | Medium |
| 15 | main.py | `run_full()` reconstructs `vectors_path` with `datetime.now()` — date rollover at midnight causes path mismatch with `run_generation()` | High |

---

## 6. Test Count Target

| Module | Current Tests | Target Tests | Delta |
|--------|---------------|--------------|-------|
| config.py | 2 | 8 | +6 |
| dedup.py | 2 | 11 | +9 |
| validation.py | 3 | 11 | +8 |
| discovery.py | 0 | 9 | +9 |
| generator.py | 0 | 12 | +12 |
| reporter.py | 0 | 10 | +10 |
| tester.py | 0 | 9 | +9 |
| main.py | 0 | 9 | +9 |
| daily_check.py | 0 | 6 | +6 |
| logging_config.py | 0 | 3 | +3 |
| **TOTAL** | **7** | **88** | **+81** |

---

## 7. Estimated Total Time

| Phase | Time |
|-------|------|
| Phase 0: Foundation tests | 15 min |
| Phase 1: Discovery | 15 min |
| Phase 2: Generator | 20 min |
| Phase 3: Reporter | 20 min |
| Phase 4: Tester | 20 min |
| Phase 5: Main | 20 min |
| Phase 6: Util tests | 8 min |
| Phase 7: E2E validation | 6 min |
| **TOTAL** | **~124 min (~2 hrs)** |

Each task is 2-15 minutes as required. All follow TDD: write failing test first, then implement/fix.