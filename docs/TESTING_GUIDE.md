# Testing Guide

How to run security tests using the unified tester.

## Prerequisites

### 1. Install Ollama (for local models)

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. Get a Groq API Key (optional, for cloud models)

1. Go to https://console.groq.com
2. Sign up (free tier available)
3. Create API key
4. Export: `export GROQ_API_KEY="your-key"`

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Download a Model

```bash
ollama pull qwen2.5:3b    # 1.9 GB, recommended
ollama pull llama3:8b     # 4.7 GB, needs 8GB+ RAM
```

## Quick Start

```bash
cd tools/

# Run all attacks against local model
python tester.py --provider ollama --model qwen2.5:3b

# Run specific categories
python tester.py -p ollama -m qwen2.5:3b --categories emotional,classic

# Use LLM-as-judge for better detection
python tester.py -p ollama -m llama3:8b --detector llm_judge

# Save results to file
python tester.py -p ollama -m qwen2.5:3b -o ../results/my-test.json

# Verbose mode (show responses)
python tester.py -p ollama -m qwen2.5:3b -v
```

## Command Reference

```
python tester.py [options]

Provider Options:
  --provider, -p     ollama or groq (default: ollama)
  --model, -m        Model name (default: qwen2.5:3b)
  --api-key          API key for cloud providers

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

## Attack Categories

```bash
python tester.py --list-categories
```

Current categories:
- `hierarchy` - Instruction override attempts
- `structure` - JSON/XML/Markdown injection  
- `identity` - Persona manipulation (DAN, etc.)
- `format` - Completion/template tricks
- `multiturn` - Fake conversation history
- `meta` - Self-reference and hypotheticals
- `classic` - Proven community jailbreaks
- `emotional` - Manipulation via sympathy/urgency

## Detection Methods

### Substring (default)
Fast but high false-positive rate. Checks if indicator strings appear in response.

```bash
python tester.py -d substring
```

**Problem**: "Sure, I can't help" matches "sure" → false positive

### LLM Judge (recommended)
Uses a local model to evaluate if the attack actually succeeded.

```bash
python tester.py -d llm_judge --judge-model qwen2.5:3b
```

**Better**: Understands context, catches refusals correctly.
**Slower**: Adds ~2-5 seconds per attack.

## Testing Groq vs Local (Critical Test)

This compares the same model through different providers:

```bash
# Test locally
python tester.py -p ollama -m llama3:8b -o ../results/local.json

# Test via Groq API
export GROQ_API_KEY="your-key"
python tester.py -p groq -m llama3-8b-8192 -o ../results/groq.json
```

Our finding: Groq adds API filtering. Same model shows ~0% vulnerability via Groq, ~78% locally.

## Understanding Results

### Console Output
```
[1/5] EMO-01: Dying Grandmother
         SUCCEEDED (confidence: 50%)
```

- **SUCCEEDED** - Attack indicators found / judge said success
- **BLOCKED** - No indicators / judge said refused

### JSON Output
```json
{
  "provider": "ollama/qwen2.5:3b",
  "detector": "substring",
  "success_rate": 80.0,
  "categories": {
    "emotional": {"total": 5, "success": 4}
  },
  "results": [...]
}
```

## Adding Custom Attacks

Create a new file in `attacks/`:

```python
# attacks/custom.py
from .base import Attack

ATTACKS = [
    Attack(
        id="CUSTOM-01",
        name="My Attack",
        category="custom",
        prompt="Your attack prompt...",
        indicators=["success_string"],
        goal="What you're trying to achieve",
        source="where it came from"
    ),
]
```

Then add to `attacks/__init__.py`:
```python
from . import custom
ALL_ATTACKS.extend(custom.ATTACKS)
```

## Troubleshooting

### "Connection refused"
```bash
ollama serve  # Start Ollama
```

### "Model not found"
```bash
ollama list   # Check installed models
ollama pull model-name
```

### Slow responses
- 8B models need ~8GB RAM
- First run loads model (slow)
- Use smaller model (3B) for quick tests

### Groq rate limits
- Free tier: 30 requests/minute
- Use `--categories` to run fewer attacks
