# Testing Guide

How to run local-only security tests with PSG.

## Prerequisites

### 1. Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. Install PSG

```bash
pip install -e .
```

### 3. Download a Model

```bash
ollama pull qwen2.5:3b
ollama pull llama3:8b
```

## Quick Start

```bash
psg scan --model qwen2.5:3b --catalog datasets/obliteratus_attacks.json --allow-insecure-http
psg scan --model qwen2.5:3b --catalog datasets/prompt_injection_techniques.json --detector llm-judge --allow-insecure-http
psg scan --model llama3:8b --catalog datasets/obliteratus_attacks.json --json-report results/my-test.json --allow-insecure-http
```

## Command Reference

```text
psg scan [options]

Required:
  --model              Model name, e.g. llama3:8b, qwen2.5:3b
  --catalog            Path to attacks catalog JSON

Connection:
  --base-url           OpenAI-compatible base URL (default: http://localhost:11434/v1)
  --allow-insecure-http  Allow http:// base URL
  --api-key            API key for hosted endpoints (or set PSG_API_KEY)

Detection:
  --detector           keyword | llm-judge | ensemble (default: keyword)
  --judge-model        Model used by LLM judge detector (default: llama3:8b)
  --judge-url          Base URL for judge (defaults to --base-url)
  --classification-input  auto | raw | redacted | both (default: auto)

System Prompt:
  --system-prompt      System prompt to test (inline)
  --system-prompt-file Path to file containing system prompt

Output:
  --json-report        Path for JSON report (default: results/report.json)
  --text-report        Path for text report (default: results/report.txt)
  --html-report        Path for HTML dashboard report
  --defense-report     Generate defense effectiveness report
  --checkpoint         Checkpoint path (default: results/checkpoint.jsonl)

Generation:
  --temperature        Generation temperature (default: 0.0)
  --max-tokens         Max tokens per response (default: 512)
  --timeout            Request timeout in seconds (default: 240)
  --max-retries        Max retries per request (default: 4)

Parallelism:
  --workers            Number of parallel workers 1-32 (default: 1)
  --rate-limit         Max requests per second (default: unlimited)

Attack Modes:
  --attack-mode        single | crescendo | many-shot (default: single)
  --crescendo-turns    Max turns per crescendo attack (default: 7)
  --many-shot-examples  Number of priming examples (default: 10)
  --multi-turn         Enable multi-turn attack execution

Defense:
  --with-defense       Run defense validation on attacks before sending
  --defense-threshold  Defense blocking threshold 0.0-1.0 (default: 0.5)
  --defense-only       Only run defense validation, don't call model

Redaction:
  --redaction          partial | strict | off (default: partial)

Validation (opt-in):
  --validate-urls      Validate discovered URLs via HTTP HEAD
  --validate-dois      Validate discovered DOIs via CrossRef API
  --validation-timeout Timeout for validation requests (default: 5)
```

## Security Defaults

- Stored responses are **redacted by default** (`--redaction partial`).
- Response storage defaults to **truncated** output.
- `--api-key` reads from `PSG_API_KEY` environment variable if not provided.

## Reproducible Example

```bash
psg scan \
  --model qwen2.5:3b \
  --catalog datasets/obliteratus_attacks.json \
  --detector llm-judge \
  --temperature 0.0 \
  --allow-insecure-http \
  --json-report results/repro-qwen3b-judge.json
```

## Troubleshooting

### Connection refused
```bash
ollama serve
```

### Model not found
```bash
ollama list
ollama pull model-name
```