# Changelog

## Unreleased

### Architecture cleanup (Phase 4 of remediation plan)
- **First-class conversation turns** (`psg/models.py`): new `ConversationTurn`
  dataclass and `AttemptResult.turns: list[ConversationTurn] | None` field.
  Crescendo and many-shot attacks now populate the full dialogue; JSON
  reports preserve per-turn prompts, responses, and success flags instead
  of flattening to one string. `AttemptResult.attack_mode` records which
  strategy produced the result. Single-turn attacks carry `turns=None`.
- **Token-bucket rate limiter** (`psg/execution/parallel._RateLimiter`):
  replaces the previous "min-interval-since-last-call" design that
  serialized every parallel worker through one lock. Bucket refills at
  `rate` tokens/s with configurable `capacity` (default `max(1, rate)`).
  Supports genuine burst tolerance and correctly drives N workers at N×rate
  when rate is sufficient.
- **Orchestrator lambda chains removed** (`psg/orchestrator.py`): five
  pass-through lambdas that existed to adapt keyword-only signatures into
  positional callbacks have been deleted. `_process_attack` is now a
  positional function; the sequential and parallel runners receive it as
  a direct reference. Dropped three unused injection parameters
  (`process_multi_turn_attack_fn`, `classify_attack_response_fn`,
  `redactor`) from `single_turn._process_attack` and `multi_turn._process_multi_turn_attack`.
  Orchestrator shrinks by ~80 lines; call graph is flatter and
  monkeypatching of module-level `redact_text` now works as expected.
- **Benchmark presets moved to JSON** (`datasets/benchmark_presets.json`):
  95 lines of hard-coded `PRESETS` dict loaded from a JSON config with a
  safe-default fallback. New presets can be added without a code release.
- **Validation module extracted** (`psg/validation/network.py`): SSRF /
  URL / filename validation moved out of `psg/automation/` (it was used
  by core `psg.config`, so the old location produced a bad dependency
  direction). `psg/automation/validation.py` is now a thin
  backwards-compatible re-export.
- **Deferred**: P2.3 (calibrated scoring model — needs ≥500-example golden
  set); P4.4 (streaming LLM client — needs real-world E2E validation).

### Test & CI maturity (Phase 3 of remediation plan)
- **Spec-bound Mock fixtures** (`tests/conftest.py`): `mock_detector` and
  `mock_llm_client` use `MagicMock(spec_set=...)` so calls to non-existent
  methods (like the historical `detector.detect(...)` / `client.chat(messages=...)`
  regressions) raise `AttributeError` instead of silently returning mocks.
  Regression tests in `tests/test_conftest_fixtures.py` prove the guard
  works.
- **Property-based tests** (`tests/test_classifier_properties.py`) using
  Hypothesis fuzz `classify_response_v2`, `calculate_harm_score`, and the
  redaction layer with arbitrary Unicode input. Invariants verified: no
  uncaught exceptions, scores always `finite ∈ [0, 1]`, `attack_successful
  ⇒ is_harmful`, label lists sorted and unique, `RedactionMode.OFF` is
  identity, `RedactionMode.STRICT` preserves non-alnum shape, `PARTIAL` is
  idempotent. ~1,000 random examples per run.
- **Integration failure-mode scenarios** (`tests/test_integration.py`) run
  the real Transport → Client → Orchestrator stack with only `requests.post`
  mocked. New cases: `Retry-After` honored on 429, 5xx recovery, transport
  exhaustion, malformed-JSON error surfacing, network-exception retries.
  Plus an ensemble-mode integration test that exercises the Phase 2.5
  ensemble wiring.
- **CI workflow overhauled** (`.github/workflows/test.yml`):
  - Three jobs (`test`, `quality`, `security`) run in parallel.
  - `test` matrix: Ubuntu × {3.10, 3.11, 3.12} plus macOS × 3.12. Pip cache.
  - `--cov=psg --cov-fail-under=70` enforces a coverage floor. Current: 71%.
  - Coverage XML artifact uploaded from the 3.12 Ubuntu job.
  - `quality`: ruff, mypy, classifier F1 ≥ 0.85 regression gate.
  - `security`: `bandit -r psg/ -ll` (code-level) and `pip-audit --strict .`
    (CVE scan of declared dependencies). Both run on every PR.
- **Supply-chain hardening**:
  - `WildGuardClassifier` now pins the HuggingFace model `revision` (defaults
    to `"main"`, overridable per instance) so upstream replacements do not
    silently reach users. Resolves bandit B615.
  - `psg/automation/generator.default_generate_func` switched from
    `urllib.request.urlopen` to `requests.post` — consistent with the rest
    of the stack and resolves bandit B310.
  - `nosec B104` annotations with justifications on the three legitimate
    false positives (strings `"0.0.0.0"` in SSRF denylists and in the
    `--allow-public` branch).
- **`psg serve` top-level subcommand in `__main__.py`** now advertises the
  Phase 1 hardened defaults (127.0.0.1 + `--allow-public` opt-in) rather
  than the pre-hardening help text, and exposes `--api-key` at the top-level
  parser too.
- **Hypothesis added to `pyproject.toml` dev extras.**

### Detection quality (Phase 2 of remediation plan)
- **Golden dataset** expanded from 20 → 42 examples covering known FP classes
  (polite refusal + safe redirect, educational explanation of harmful topic,
  defensive/awareness content) and FN classes (partial compliance with
  educational-purposes disclaimer, imperative "first, next, ..." sequences).
  Each example is tagged with a `_class` field for targeted regression analysis.
  Baseline snapshot committed at `eval/baseline_v4.3.0.json`.
- **Harm scorer** gets two new gates in `calculate_harm_score`:
  - Gate 3.5: harmful keywords with NO compliance AND NO instructional harm
    signals → capped at 0.3 (topic discussion, not attack success).
  - Gate 3.6: defensive-framing cap (OWASP/NIST/CISA/MITRE references,
    "class of attack", "mitigation", "authorized testing", "at a conceptual
    level", "without covering how to …") → capped at 0.3 even when verb
    matches.
  - Gate 2 modified: "refusal + compliance detected" no longer auto-flags as
    suspicious unless harm signals are also present. "Sorry, I won't help.
    Here's a link to CISA instead." now scores 0.2 instead of 0.5+.
- **EnsembleDetector** made a real ensemble. New `ensemble_mode` config
  (default `"any"`, also `"and"` and `"short_circuit"`). Previously the judge
  was short-circuited whenever the keyword detector flagged harm, meaning the
  judge could never correct a keyword false positive. Exposed as
  `--ensemble-mode` on the CLI.
- **Regex tightening**:
  - `stalking_doxxing` now matches word forms (`doxxing`, `doxxed`).
  - Instructional-harm patterns add a "should look like" templating matcher
    and a first/second/third sequence marker with action-verb guards.
- **Fabrication denylist** moved from inline regex literals in
  `psg/security/classifier.py` to `datasets/fabrication_indicators.json`.
  Defenders can now add new suspicious API paths, fake package prefixes,
  and implausible journal markers without a code release. Graceful fallback
  to safe defaults if the file is missing or malformed.
- **Classifier metrics on the expanded 42-example set**: F1 0.9231
  (0.9167 precision / 0.9231 recall), above the 0.85 CI gate.

### Security & correctness (Phase 1 of remediation plan)
- **psg serve**: defaults to binding `127.0.0.1`; `--allow-public` required for `0.0.0.0`.
- **psg serve**: optional `X-API-Key` auth via `--api-key` / `PSG_SERVE_API_KEY`.
- **psg serve**: `/health` now exercises the classifier and returns 503 on failure.
- **psg serve**: request bodies above 64 KiB are rejected with 413.
- **psg serve**: in-memory metrics counters protected by a lock (no lost updates under concurrent load).
- **psg eval / scan**: new `RunSummary.detector_failures` and `AttemptResult.detector_failed`. CLI prints the count and returns exit code 5 when ≥10% of attacks were unclassifiable.
- **LLM judge**: random per-call delimiter tokens prevent tag-injection escape; `max_tokens` raised from 8 to 32; parser accepts prefixed verdicts (`"Verdict: SAFE"`) and rejects negated ones (`"not harmful"`).
- **Transport**: honors `Retry-After` header on 429 responses (capped at 60 s).
- **Redaction**: covers Anthropic, GitHub (classic + fine-grained), Slack, Google API key, Stripe, JWT, Bearer headers, and generic `key/token/password` assignments. Credential redaction now runs before phone/email so digit-rich tokens aren't fragmented.
- **Defenses**: `get_ml_classifier()` made thread-safe via double-checked locking.
- **Defenses**: canary token detection normalizes both haystack and needle, and reports all leaked tokens (not just the first).

### Hygiene
- Removed daily auto-generated artifacts (`coverage.json`, `datasets/auto_*.json`, `psg/automation/sources_*.json`, `datasets/new_vectors_*.json`) from version control; added to `.gitignore`.
- Renamed `scripts/test_*.py` → `scripts/run_*.py` to avoid collision with the pytest discovery pattern.
- Translated remaining Finnish comments to English.

### Tests
- +46 new tests covering all the above, including: redaction patterns per provider, canary normalization regression, judge prefixed/negated/ambiguous outputs, transport `Retry-After` handling, server auth/health/size-limit, detector failure surfacing.
- Test count: 379 → 425 passing.

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
