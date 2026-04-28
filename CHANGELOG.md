# Changelog

## 4.4.0 - 2026-04-28

### Security Fixes
- **Judge prompt injection protection**: Random delimiter (`secrets.token_hex(8)`) per call prevents `</response>` injection attacks in LLM Judge (improvement plan 1.2)
- **Ensemble short-circuit confidence threshold**: Keyword detector now only short-circuits the LLM judge when `harm_score >= 0.8`. Low-confidence keyword hits are forwarded to the judge for correction, preventing false positives from blocking remediation (improvement plan 1.3)
- **Judge max_tokens**: Increased from 8 to 16 — truncated judge responses were parsed as UNKNOWN (code review M8)
- **Canary token collection**: All leaked canary tokens are now collected, not just the first. Multiple tokens can now be detected in a single response (code review M18)
- **custom_detectors semantics**: Empty list `[]` no longer silently replaced with `None`. `custom_input_detectors=[]` is now preserved (code review H8)

### New Features
- **needs_review field**: `ClassificationResult` includes `needs_review: bool` — true when `0.3 < harm_score < 0.7`, flagging uncertain classifications for human review (improvement plan 2.2)

### Code Quality
- **ruff format**: All 52 source files reformatted to project style
- **ruff lint**: Removed 5 extraneous f-string prefixes in execution modules; cleaned 22 unused imports/variables in tests
- **mypy**: Fixed `binascii` import reference in `normalize.py`; installed `types-requests` stubs for transport/validation/discovery modules
- **test coverage**: Added test for ensemble low-confidence behavior (keyword FP → judge still runs)
- **audit iteration 2**: canary token normalization (case-insensitive), catalog validator alias support (`ID_ALIASES`/`PROMPT_ALIASES`), dead guard removal → assert, silent except → `logging.warning` (ML load/inference), `defend.py` msg-is-dict guard, `_as_labels()` dedup helper, orchestrator lambda dedup, stale `results` alias removed

### Already Implemented (verified)
- LangChain middleware: `fail_open=False` by default (code review H1) — was already correct
- WildGuard singleton: thread-safe with `_classifier_lock` double-check (code review H2) — was already correct
- Canary normalization: `normalize_text()` applied before comparison (code review H9) — was already correct
- FP-reduction: GATE 1 logic in `calculate_harm_score()` handles refusal + no compliance = low score regardless of keywords (improvement plan 2.3) — already implemented

## 4.3.0 - 2026-03-27

### Hallucination & Data Leakage Detection
- Added hallucination detection probes (56 attacks):
  - Fake citations, invented facts, false URLs
  - Non-existent APIs, package hallucination, code hallucination
- Added data leakage probes (54 attacks):
  - Memorization attacks, PII extraction, system prompt leaks
  - Training membership inference, indirect leakage, model inversion

### Hybrid Validation System
- Offline heuristics (always on):
  - Future DOI detection, ArXiv date validation
  - Fake domain detection (fake-nature.com, etc.)
  - Domain/content mismatch (cdc.gov/bitcoin)
  - Implausible journal markers
- Online validation (opt-in):
  - `--validate-urls` - HTTP HEAD validation
  - `--validate-dois` - CrossRef API validation
  - `--validation-timeout` - configurable timeout (default 5s)

### New Classifier Labels
- `fabricated_url_unverified` - suspicious URL detected
- `fabricated_doi_unverified` - suspicious DOI detected

### Test Coverage
- Added tests for evaluate.py (0% → 77%)
- Added tests for wildguard_classifier.py (0% → 68%)
- Total tests: 161 → 178

## 4.2.0 - 2026-03-26

### Multi-turn Attack Support
- Added `--multi-turn` flag for executing attacks with followup prompts
- New `followups` field in attack catalog schema
- Conversation history maintained across turns
- Attack flagged if any turn produces harmful content

### Dataset Expansion
- Expanded attack datasets to 1381+ prompts
- Added HarmBench behaviors (391)
- Added community jailbreaks (564)
- Added L1B3RT4S commands (35)
- Added prompt injection techniques (25)

### Dataset Quality
- Fixed missing `tier` and `source` fields across all datasets
- Moved eval data to separate `eval/` directory
- Validation now PASSED (was FAILED)

### PyPI Preparation
- Added classifiers, keywords, and URLs to pyproject.toml
- Added README badges (License, Python, CI)
- Version bump to 4.2.0

## 4.1.0 - 2026-03-25

### API Server
- Added FastAPI server: `psg serve --port 8000`
- Endpoints: `/screen`, `/screen/bulk`, `/health`, `/metrics`
- Optional dependencies: `pip install -e ".[serve]"`

### Plugin System
- Added plugin architecture with entry points
- Detector plugins: `psg.detectors`
- Classifier plugins: `psg.classifiers`
- Reporter plugins: `psg.reporters`
- CLI: `psg plugins` to list installed plugins

### HTML Dashboard
- Added HTML report generation: `psg scan --html-report report.html`
- Dark theme dashboard with statistics, defense rate, and results table
- XSS-safe template with proper escaping

### Integrations
- Added LangChain middleware integration in `psg/integrations/langchain.py`:
  - `PSGGuardMiddleware`
  - `AsyncPSGGuardMiddleware`
- Added input and output screening support in LangChain callback flow.

### Evaluation and CI
- Added classifier evaluation CLI: `psg eval`.
- Added golden-dataset evaluation flow with regression gating:
  - `psg eval --golden datasets/classifier_golden.json --fail-on-macro-f1-below 0.85`

### Scan performance
- Added parallel scan execution with `--workers`.
- Added rate control for scans with `--rate-limit`.

### Benchmarking
- Added preset benchmark runner: `psg benchmark`.
- Added benchmark presets: `jbb`, `owasp`, `obliteratus`, `full`.
- Example: `psg benchmark --preset jbb --model llama3:8b`

### Repository cleanup
- Removed deprecated files (tester.py, tools symlink, requirements.txt)
- Renamed attacks/ → generators/
- Moved research/ → docs/research/
- Fixed CI workflow to use pyproject.toml

## 4.0.0 - 2026-03-23

### Major updates
- Refactored runtime around the `psg/` package as the primary execution path for scanning and tooling.
- Improved security classifier behavior with intent-aware policy-evasion detection and new regression tests.
- Integrated JailbreakBench behavior coverage in repository datasets and evaluation flow.

### Security hardening
- Hardened URL validation in automation with DNS resolution checks and blocking for all resolved private/local IPv4 and IPv6 addresses.
- Applied redaction to prompts before checkpoint/report persistence so sensitive prompts are not stored in clear text when redaction is enabled.

### CLI and UX
- Added unified CLI subcommands with discoverable help: `scan` and `catalog validate`.
- Added graceful runtime error handling for configuration, catalog, and LLM failures with user-facing stderr messages and non-zero exit codes.
- Added API key support via `--api-key` and `PSG_API_KEY` for hosted OpenAI-compatible endpoints (Authorization bearer header).
- Propagated report write failures to runtime status so failed report outputs cause non-zero CLI exits.

### Automation and CI
- Reduced dedup I/O amplification with batched persistence and explicit flush behavior.
- Consolidated CI to a single workflow (`test.yml`) and removed duplicate workflow configuration.
- Expanded PSG-focused test coverage for SSRF validation, CLI dispatch/error paths, dedup batching, auth headers, and classifier regressions.

## 3.0.0 - 2026-03-05

### Breaking / structural changes
- Canonicalized runtime to `psg/`.
- Moved legacy entrypoint `tester.py` to `legacy/tester_v2.py`.
- Moved `tools/` implementation to `legacy/tools/` and left temporary compatibility symlink.

### Repository hygiene
- Replaced `.gitignore` with a safe default (ignore env/cache/logs/results, keep source+datasets+tests+docs).
- Added `requirements-dev.txt` and aligned runtime dependencies.
- Updated `pyproject.toml` metadata and version alignment to `3.0.0`.

### Artifact cleanup
- Moved `OBLITERATUS/`, `overnight-rebuild/`, and `examples/production-prompts/` to `archive/deprecated/`.
- Pruned `results/` to curated sample outputs.
- Removed committed virtual environment/cache artifacts.

### Documentation
- Rewrote `README.md` to a single happy path.
- Added `MIGRATION.md` and `ARCHITECTURE.md`.
- Repaired doc index links in `docs/README.md`.
