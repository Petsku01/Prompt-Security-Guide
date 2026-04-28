# PSG Codebase Audit — Status

**Updated:** 2026-04-28

## Audit Complete

All audit iterations completed. Codebase is clean:

- **380 tests** passing (1 skipped)
- **ruff check** — All checks passed
- **ruff format** — 99 files formatted
- **mypy** — 0 errors in 63 source files
- **No AI slop**, no silent excepts, no bare excepts, no star imports, no hardcoded secrets

## Fixes Applied (Iteration 2)

| # | File | Fix |
|---|------|-----|
| 1 | `defend.py:250` | `msg.get()` crash when msg is str not dict → isinstance guard |
| 2 | `defenses/input_validators.py` | Canary token normalization: case-insensitive comparison |
| 3 | `defenses/__init__.py` | Dead guard `if result.secrets_found is None` → assert + proper check |
| 4 | `catalog_validator.py` | `REQUIRED_FIELDS` → `ID_ALIASES`/`PROMPT_ALIASES` alias support |
| 5 | `defenses/input_validators.py` | Silent except → `logging.warning` (ML load/inference) |
| 6 | `defenses/input_validators.py` | Dead leetspeak comment removed |
| 7 | `orchestrator.py` | Empty wrapper functions → direct aliases |
| 8 | `orchestrator.py` | Stale `results = defended_results` alias removed |
| 9 | `orchestrator.py` | Duplicate lambdas → shared `_process_attack_fn` |
| 10 | `strategies.py` + `defend.py` | `SCENARIOS` dict deduplicated |
| 11 | `defend.py` | Duplicate list/tuple pattern → `_as_labels()` helper |

## CI Commands

```bash
.venv/bin/python -m ruff format psg/ tests/
.venv/bin/python -m ruff check psg/ tests/ --fix
.venv/bin/python -m mypy psg/
.venv/bin/python -m pytest tests/ -x -q
```