# Changelog

## 2026-02-15

### Added

- `results/ANALYSIS_SUMMARY.md` consolidating six February 2026 model/detector runs.
- `results/README.md` documenting naming conventions, latest run matrix, and legacy file note.
- `CHANGELOG.md` for repository-level change tracking.
  

### Updated

- `docs/MODEL_COMPARISON.md`
  - Added three-model + two-detector comparison section.
  - Added detector-effect deltas and substring category snapshot.
  - Added direct data source references.
- `docs/METHODOLOGY.md`
  - Added detector comparison protocol.
  - Added reproducibility controls (`schema_version`, seed, temperatures).
  - Documented 2026-02-15 test procedure and fallback tracking.
- `CONCLUSIONS.md`
  - Added February 2026 findings on detector effect, structural attack dominance, and multi-turn+structure behavior.
- `README.md`
  - Promoted key research findings and clarified scope/results/docs navigation.

### Verification Notes

- Static scans completed for legacy provider references and obvious secret patterns.
- Runtime test execution blocked in current environment (`python3` lacks `pip` and `pytest`).
