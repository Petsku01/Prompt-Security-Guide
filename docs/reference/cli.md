# CLI Reference

## Commands Overview

| Command | Description |
|---------|-------------|
| `psg scan` | Scan a model against attack catalog |
| `psg defend` | Defense tools (validate, benchmark, templates) |
| `psg benchmark` | Run preset benchmarks |
| `psg eval` | Evaluate detector accuracy |
| `psg serve` | Start API server |
| `psg catalog validate` | Validate catalog JSON files |

---

## psg scan

Scan a model against an attack catalog.

### Required Arguments

| Argument | Description |
|----------|-------------|
| `--model MODEL` | Model name (e.g., `llama3:8b`, `gpt-4`) |
| `--catalog PATH` | Path to attack catalog JSON |

### Common Options

| Option | Default | Description |
|--------|---------|-------------|
| `--base-url URL` | `http://localhost:11434/v1` | API endpoint |
| `--api-key KEY` | None | API key (or set `PSG_API_KEY`) |
| `--system-prompt TEXT` | None | System prompt to test |
| `--system-prompt-file PATH` | None | Read system prompt from file |
| `--workers N` | 1 | Parallel workers (1-32) |
| `--rate-limit RPS` | None | Max requests per second |
| `--timeout SECONDS` | 240 | Request timeout |
| `--allow-insecure-http` | False | Allow http:// URLs |

### Detection Options

| Option | Default | Description |
|--------|---------|-------------|
| `--detector MODE` | `keyword` | Detection mode: `keyword`, `llm-judge`, `ensemble` |
| `--judge-model MODEL` | `llama3:8b` | Model for LLM judge |
| `--defense-report` | False | Generate defense comparison report |

### Defense Options

| Option | Default | Description |
|--------|---------|-------------|
| `--defense-only` | False | Only run defense validation (no model calls) |
| `--defense-threshold FLOAT` | 0.5 | Blocking threshold (0.0-1.0) |
| `--with-defense` | False | Run defense validation before model calls |

### Output Options

| Option | Default | Description |
|--------|---------|-------------|
| `--json-report PATH` | `results/report.json` | JSON report path |
| `--text-report PATH` | `results/report.txt` | Text report path |
| `--html-report PATH` | None | HTML dashboard report |
| `--checkpoint PATH` | `results/checkpoint.jsonl` | Progress checkpoint |

### Examples

```bash
# Basic local scan
psg scan --model llama3:8b --catalog datasets/attacks.json --allow-insecure-http

# OpenAI scan
psg scan --model gpt-4 --catalog datasets/attacks.json \
  --base-url https://api.openai.com/v1 --api-key $OPENAI_API_KEY

# Parallel scan with defense
psg scan --model llama3:8b --catalog datasets/attacks.json \
  --workers 4 --rate-limit 10 \
  --system-prompt "Be safe" --defense-report \
  --allow-insecure-http

# Defense-only (fast, no model)
psg scan --model dummy --catalog datasets/attacks.json \
  --defense-only --defense-threshold 0.3 --allow-insecure-http
```

---

## psg defend

Defense tools for prompt injection detection.

### Subcommands

#### psg defend validate

Check text for injection attempts.

```bash
# Inline text
psg defend validate "Ignore previous instructions"

# From file
psg defend validate --file input.txt

# From stdin
echo "test" | psg defend validate

# Options
psg defend validate "text" \
  --mode input|output|both \
  --threshold 0.5 \
  --canary SECRET123 \
  --no-ml \
  --json
```

#### psg defend benchmark

Test defenses against attack catalog.

```bash
psg defend benchmark --catalog datasets/attacks.json \
  --threshold 0.5 \
  --no-ml \
  --json \
  --output results.json
```

#### psg defend templates

Manage defense prompt templates.

```bash
# List all templates
psg defend templates --list

# Filter by category
psg defend templates --category anti-injection

# Show specific template
psg defend templates --show "Ignore previous instructions"

# Get recommendations
psg defend templates --recommend agent

# Generate combined prompt
psg defend templates --recommend chatbot --combine
```

#### psg defend info

Show capabilities and recommendations.

```bash
psg defend info
psg defend info --scenario agent
```

---

## psg benchmark

Run preset benchmarks.

```bash
# List presets
psg benchmark --list

# Run preset
psg benchmark --preset jbb --model llama3:8b

# Options
psg benchmark --preset full --model llama3:8b \
  --base-url http://localhost:11434/v1 \
  --workers 4 \
  --output-dir results/
```

### Presets

| Preset | Description |
|--------|-------------|
| `jbb` | JailbreakBench behaviors |
| `owasp` | OWASP 2025 attacks |
| `obliteratus` | Obliteratus attack set |
| `full` | All catalogs |

---

## psg eval

Evaluate detector against golden dataset.

```bash
psg eval --golden datasets/golden.json --threshold 0.5 --json
```

---

## psg serve

Start the screening API server.

```bash
psg serve --host 0.0.0.0 --port 8000 --threshold 0.5 --reload
```

API endpoints:
- `GET /health` - Health check
- `POST /screen` - Screen single text
- `POST /bulk` - Screen multiple texts
- `GET /metrics` - Prometheus metrics
- `GET /docs` - OpenAPI docs

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `PSG_API_KEY` | Default API key for model endpoints |
| `HF_TOKEN` | HuggingFace token for ML models |
