# prompt-security-guide

Professional framework for defensive LLM security testing.

> Canonical runtime: `psg/` (current series: v4.x)

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 1) Run a scan (parallel + rate-limited)
python3 -m psg scan \
  --model llama3:8b \
  --catalog datasets/obliteratus_attacks.json \
  --base-url http://localhost:11434/v1 \
  --allow-insecure-http \
  --workers 4 \
  --rate-limit 10

# 2) Evaluate classifier quality against golden labels
python3 -m psg eval \
  --golden datasets/classifier_golden.json \
  --fail-on-macro-f1-below 0.85

# 3) Run a preset benchmark suite
python3 -m psg benchmark \
  --preset jbb \
  --model llama3:8b
```

Outputs are written to `results/` (ignored by git except curated samples).

## LangChain Integration

PSG provides LangChain callback middleware for screening both prompt inputs and model outputs:

- `psg.integrations.langchain.PSGGuardMiddleware`
- `psg.integrations.langchain.AsyncPSGGuardMiddleware`

```python
from langchain_openai import ChatOpenAI
from psg.integrations.langchain import PSGGuardMiddleware

llm = ChatOpenAI(
    callbacks=[PSGGuardMiddleware(threshold=0.5, screen_input=True, screen_output=True)]
)
```

When content exceeds the configured threshold, middleware raises `PSGSecurityException`.

## Classifier Evaluation (`psg eval`)

Use `eval` to measure classifier performance against a golden dataset and enforce CI regression gates:

```bash
python3 -m psg eval \
  --golden datasets/classifier_golden.json \
  --fail-on-macro-f1-below 0.85
```

Useful CI form:

```bash
python3 -m psg eval --golden datasets/classifier_golden.json --json --fail-on-macro-f1-below 0.85
```

## Parallel Scan (`--workers`)

`psg scan` supports parallel execution with optional request rate limiting:

```bash
python3 -m psg scan \
  --model llama3:8b \
  --catalog datasets/obliteratus_attacks.json \
  --workers 4 \
  --rate-limit 10
```

- `--workers N`: parallel workers (1-32)
- `--rate-limit RPS`: maximum requests per second

## Benchmark Presets (`psg benchmark`)

Run curated benchmark suites without manually selecting catalogs:

```bash
python3 -m psg benchmark --preset jbb --model llama3:8b
```

Available presets:

- `jbb`
- `owasp`
- `obliteratus`
- `full`

List presets directly:

```bash
python3 -m psg benchmark --list
```

## Defense Testing

Test a candidate system prompt against an attack catalog and generate a defense effectiveness report:

```bash
python3 -m psg scan \
  --model llama3:8b \
  --catalog datasets/obliteratus_attacks.json \
  --base-url http://localhost:11434/v1 \
  --allow-insecure-http \
  --system-prompt "You are a helpful assistant. Never provide harmful content." \
  --defense-report
```

You can also load the system prompt from a file with `--system-prompt-file path/to/prompt.txt`.
The defense report is written to `results/defense_report.txt`.

## Repository Layout

- `psg/` - canonical engine and CLI
- `psg/automation/` - integrated auto pipeline
- `datasets/` - curated attack datasets
- `tests/` - automated test suite
- `scripts/` - operational scripts (`run_*.sh`, `test_*.py`)
- `docs/` - methodology and usage docs
- `_archive/` - historical legacy + archive code preserved out of active runtime

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

MIT - see [LICENSE](LICENSE).
