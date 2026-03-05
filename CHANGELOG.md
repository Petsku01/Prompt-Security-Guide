# Changelog

## 3.0.0 - 2026-03-05

### Breaking / structural changes
- Canonicalized runtime to `jailbreak_tester/`.
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
