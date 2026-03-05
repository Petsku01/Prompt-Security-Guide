# prompt-security-guide

Defensive toolkit for evaluating LLM jailbreak resistance.

> Canonical runtime as of v3.0.0: `jailbreak_tester/`

## Quick Start (single happy path)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run test suite against local model endpoint
python -m jailbreak_tester \
  --model llama3:8b \
  --catalog datasets/obliteratus_attacks.json \
  --base-url http://localhost:11434/v1
```

Outputs are written to `results/` (ignored by git except curated samples).

## Repository Layout

- `jailbreak_tester/` — canonical engine and CLI
- `datasets/` — curated attack datasets
- `attacks/` — attack definitions used by tests and experiments
- `tests/` — automated test suite
- `docs/` — methodology and usage docs
- `legacy/` — deprecated v2 runtime and migrated tooling
- `archive/deprecated/` — historical large artifacts removed from active runtime

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
