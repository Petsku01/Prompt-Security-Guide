# prompt-security-guide

**Test how well your LLM resists jailbreaks, prompt injection, and other attacks.**

PSG scans language models against curated attack catalogs and reports which attacks succeeded. Use it to evaluate model safety, test defense prompts, and catch regressions in CI.

## Quick Start

```bash
pip install -e .
python3 -m psg scan --model llama3:8b --catalog datasets/obliteratus_attacks.json --allow-insecure-http
```

Output:
```
Done. total=50 succeeded=48 failed=2 flagged=12 duration=34.21s
```

- `flagged` = attacks that got harmful responses (lower is better)
- Reports written to `results/report.json` and `results/report.txt`

## Installation

```bash
git clone https://github.com/Petsku01/Prompt-Security-Guide.git
cd Prompt-Security-Guide
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"  # includes test dependencies
```

## Core Commands

### Scan a model

```bash
python3 -m psg scan \
  --model llama3:8b \
  --catalog datasets/obliteratus_attacks.json \
  --base-url http://localhost:11434/v1 \
  --allow-insecure-http
```

### Parallel scan (faster)

```bash
python3 -m psg scan \
  --model llama3:8b \
  --catalog datasets/obliteratus_attacks.json \
  --workers 4 \
  --rate-limit 10
```

- `--workers N` — parallel workers (1-32)
- `--rate-limit RPS` — max requests per second

### Test a defense prompt

```bash
python3 -m psg scan \
  --model llama3:8b \
  --catalog datasets/obliteratus_attacks.json \
  --system-prompt "You are a helpful assistant. Refuse harmful requests." \
  --defense-report
```

Compares attack success rate with and without the defense prompt.

## Benchmark Presets

Run standard benchmark suites without picking catalogs manually:

```bash
python3 -m psg benchmark --preset jbb --model llama3:8b
```

| Preset | Description |
|--------|-------------|
| `jbb` | JailbreakBench — 100 harmful behavior prompts |
| `owasp` | OWASP Top 10 LLM attacks (2025) |
| `obliteratus` | Curated multi-technique attack collection |
| `full` | All datasets combined |

List presets: `python3 -m psg benchmark --list`

## CI Integration

### Classifier regression gate

Ensure classifier quality doesn't degrade:

```bash
python3 -m psg eval \
  --golden datasets/classifier_golden.json \
  --fail-on-macro-f1-below 0.85
```

Exit code 1 if F1 score drops below threshold. Use `--json` for machine-readable output.

### GitHub Actions example

```yaml
- name: PSG Classifier Gate
  run: python3 -m psg eval --golden datasets/classifier_golden.json --fail-on-macro-f1-below 0.85
```

## API Server

Run PSG as a REST API for real-time screening:

```bash
pip install -e ".[serve]"
python3 -m psg serve --port 8000
```

Endpoints:
- `POST /screen` — screen single text
- `POST /screen/bulk` — screen multiple texts
- `GET /health` — health check
- `GET /metrics` — request metrics
- `GET /docs` — OpenAPI documentation

Example:
```bash
curl -X POST http://localhost:8000/screen \
  -H "Content-Type: application/json" \
  -d '{"text": "I cannot help with that request."}'
```

Response:
```json
{"harmful": false, "harm_score": 0.0, "is_refusal": true, "attack_successful": false, "latency_ms": 0.5}
```

## HTML Dashboard

Generate visual reports:

```bash
python3 -m psg scan \
  --model llama3:8b \
  --catalog datasets/obliteratus_attacks.json \
  --html-report results/report.html
```

Opens a dark-themed dashboard with:
- Summary statistics (total, defended, flagged, failed)
- Defense rate progress bar
- Clickable results table

## Plugins

List installed plugins:

```bash
python3 -m psg plugins
```

Built-in plugins:
- `keyword` — rule-based detector
- `classifier` — ML classifier detector
- `harm-classifier` — harm classification

Create custom plugins via entry points:

```toml
# pyproject.toml
[project.entry-points."psg.detectors"]
my_detector = "my_package:MyDetectorClass"
```

## LangChain Integration

Screen LLM inputs and outputs in your LangChain app:

```python
from langchain_openai import ChatOpenAI
from psg.integrations.langchain import PSGGuardMiddleware

llm = ChatOpenAI(
    callbacks=[PSGGuardMiddleware(threshold=0.5)]
)
```

Options:
- `threshold` — harm score threshold (0.0-1.0)
- `screen_input` — check prompts for injection (default: True)
- `screen_output` — check responses for harmful content (default: True)

Raises `PSGSecurityException` when threshold exceeded. Async version: `AsyncPSGGuardMiddleware`.

## Repository Layout

```
psg/                 — core library and CLI
psg/integrations/    — LangChain middleware
psg/automation/      — auto-discovery pipeline
datasets/            — attack catalogs (JSON)
generators/          — attack generation code (Python)
tests/               — test suite
scripts/             — operational scripts
docs/                — methodology and research docs
models/              — ML model files (not in git)
profiles/            — model behavior profiles
_archive/            — historical code (preserved for reference)
```

## Documentation

- [docs/README.md](docs/README.md) — documentation index
- [ARCHITECTURE.md](ARCHITECTURE.md) — system design
- [CHANGELOG.md](CHANGELOG.md) — version history
- [MIGRATION.md](MIGRATION.md) — upgrading from legacy `tools/`

## Safety

This project is for **defensive security testing only**. Do not use it to generate or deploy harmful content.

## License

MIT — see [LICENSE](LICENSE).
