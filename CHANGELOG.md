# Changelog

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
