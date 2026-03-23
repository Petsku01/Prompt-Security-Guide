# prompt-security-guide

Professional framework for defensive LLM security testing.

> Canonical runtime as of v4.0.0: `psg/`

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run security scan against local model endpoint
python -m psg \
  --model llama3:8b \
  --catalog datasets/obliteratus_attacks.json \
  --base-url http://localhost:11434/v1 \
  --allow-insecure-http

# Daily discovery + generation + testing pipeline
bash scripts/run_daily_pipeline.sh
```

Outputs are written to `results/` (ignored by git except curated samples).

## Defense Testing

Test a candidate system prompt against an attack catalog and generate a defense effectiveness report:

```bash
python -m psg scan \
  --model llama3:8b \
  --catalog datasets/obliteratus_attacks.json \
  --base-url http://localhost:11434/v1 \
  --allow-insecure-http \
  --system-prompt "You are a helpful assistant. Never provide harmful content." \
  --defense-report
```

You can also load the system prompt from a file with `--system-prompt-file path/to/prompt.txt`.
The defense report is written to `results/defense_report.txt`.

## LLM Judge Detector

PSG supports detector backends for response classification:
- `keyword` (default): regex/rule classifier
- `llm-judge`: local LLM judge via OpenAI-compatible API
- `ensemble`: run both and flag if either flags

Use LLM judge mode:

```bash
python -m psg scan \
  --model dolphin-llama3:8b \
  --catalog datasets/obliteratus_attacks.json \
  --base-url http://localhost:11434/v1 \
  --allow-insecure-http \
  --detector llm-judge \
  --judge-model llama3:8b
```

Use ensemble mode:

```bash
python -m psg scan \
  --model llama3:8b \
  --catalog datasets/obliteratus_attacks.json \
  --allow-insecure-http \
  --detector ensemble
```

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
