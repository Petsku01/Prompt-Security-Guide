# prompt-security-guide

Professional framework for defensive LLM security testing.

> Canonical runtime as of v4.0.0: `psg/`

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run test suite against local model endpoint
python -m psg \
  --model llama3:8b \
  --catalog datasets/obliteratus_attacks.json \
  --base-url http://localhost:11434/v1

# Daily discovery + generation + testing pipeline
bash scripts/run_daily_pipeline.sh
```

Outputs are written to `results/` (ignored by git except curated samples).

## Repository Layout

- `psg/` — canonical engine and CLI
- `psg/automation/` — integrated auto pipeline
- `datasets/` — curated attack datasets
- `tests/` — automated test suite
- `scripts/` — operational scripts (`run_*.sh`, `test_*.py`)
- `docs/` — methodology and usage docs
- `_archive/` — historical legacy + archive code preserved out of active runtime

## Migration

If you were using `tester.py` or `tools/`, see [MIGRATION.md](MIGRATION.md).

## Documentation

- [docs/README.md](docs/README.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [SECURITY.md](SECURITY.md)
- [CHANGELOG.md](CHANGELOG.md)

## Safety + Scope

This project is for defensive security testing only.
Do not use it to generate or deploy harmful content.

## License

MIT — see [LICENSE](LICENSE).
