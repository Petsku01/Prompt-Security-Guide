# Testing Guide

How to run local-only security tests with the unified tester.

## Prerequisites

### 1. Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Download a Model

```bash
ollama pull qwen2.5:3b
ollama pull llama3:8b
```

## Quick Start

```bash
python3 -m tools.cli --provider ollama --model qwen2.5:3b
python3 -m tools.cli -p ollama -m qwen2.5:3b --categories emotional,classic
python3 -m tools.cli -p ollama -m qwen2.5:3b --detector llm_judge
python3 -m tools.cli -p ollama -m qwen2.5:3b -o results/my-test.json
```

## Command Reference

```text
python3 -m tools.cli [options]

Provider Options:
  --provider, -p     ollama (default: ollama)
  --model, -m        Model name (default: qwen2.5:3b)

Detection Options:
  --detector, -d     substring or llm_judge (default: substring)
  --judge-model      Model for LLM judge (default: qwen2.5:3b)

Attack Filtering:
  --categories, -c   Comma-separated categories to run
  --list-categories  Show available categories

Output:
  --output, -o       Save results to JSON file
  --verbose, -v      Show full responses
  --no-system-prompt Don't use system prompt
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
