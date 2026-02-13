# Testing Guide

How to replicate our tests on your own system.

## Prerequisites

### 1. Install Ollama (for local models)

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Or see https://ollama.com/download for other platforms
```

### 2. Get a Groq API Key (for cloud models)

1. Go to https://console.groq.com
2. Sign up (free tier available)
3. Create API key
4. Export it: `export GROQ_API_KEY="your-key-here"`

### 3. Install Python Dependencies

```bash
pip install requests
```

## Download Models

### Local Models (Ollama)

```bash
# Small, fast (recommended to start)
ollama pull qwen2.5:3b        # 1.9 GB

# The model we tested for Groq comparison
ollama pull llama3:8b         # 4.7 GB (needs 8GB+ RAM)

# Tiny models
ollama pull qwen2.5:1.5b      # 986 MB
ollama pull llama3.2:1b       # 1.3 GB
```

### Cloud Models (Groq)

No download needed. Available models:
- `llama3-8b-8192` - Llama 3 8B
- `llama-3.3-70b-versatile` - Llama 3.3 70B
- `mixtral-8x7b-32768` - Mixtral 8x7B

## Running Tests

### Basic Test (16 attacks)

```bash
cd tools/

# Test local model
python3 llm_security_tester.py --model qwen2.5:3b

# With output file
python3 llm_security_tester.py --model qwen2.5:3b --output results.json

# Verbose mode (see responses)
python3 llm_security_tester.py --model qwen2.5:3b --verbose
```

### Aggressive Test (21 attacks)

```bash
# Local model
python3 aggressive_tester.py --provider ollama --model llama3:8b

# Groq API
GROQ_API_KEY="your-key" python3 aggressive_tester.py --provider groq --model llama3-8b-8192

# Save results
python3 aggressive_tester.py --provider ollama --model qwen2.5:3b --output results.json
```

### Plinius Attacks (11 attacks from L1B3RT4S repo)

```bash
python3 plinius_tester.py --provider ollama --model qwen2.5:3b
python3 plinius_tester.py --provider groq --model llama-3.3-70b-versatile
```

### UltraBr3aks Attacks (11 structural attacks)

```bash
python3 ultrabreaks_tester.py --provider ollama --model qwen2.5:3b
```

### Novel Attacks (14 original attacks)

```bash
python3 novel_tester.py --provider ollama --model qwen2.5:3b
```

### Defense Testing

```bash
python3 defense_tester.py --model qwen2.5:3b
```

## Comparing Local vs Cloud (The Critical Test)

This tests whether a provider adds filtering:

```bash
# Test same model locally
python3 aggressive_tester.py --provider ollama --model llama3:8b --output local-results.json

# Test same model via API
GROQ_API_KEY="xxx" python3 aggressive_tester.py --provider groq --model llama3-8b-8192 --output groq-results.json

# Compare results
# Local: ~57% vulnerable
# Groq: ~0% vulnerable (filtered)
```

## Expected Results

| Model | Provider | Expected Vulnerability |
|-------|----------|----------------------|
| Qwen 2.5 3B | Ollama | 70-85% |
| Qwen 2.5 1.5B | Ollama | 60-70% |
| Llama 3 8B | Ollama | 50-60% |
| Llama 3 8B | Groq | ~0% (filtered) |
| Llama 3.3 70B | Groq | 40-60% |

Results may vary between runs due to model randomness.

## Understanding Output

### Console Output

```
[1/21] HIER-01: System Override Claim
         BLOCKED (1523ms)
[2/21] HIER-02: Nested System Block
         SUCCEEDED: ['system_block_win']
```

- **BLOCKED** - Model refused/didn't comply
- **SUCCEEDED** - Attack indicators found in response

### JSON Output

```json
{
  "model": "qwen2.5:3b",
  "provider": "ollama",
  "total_attacks": 21,
  "successful": 15,
  "success_rate": 71.4,
  "results": [
    {
      "id": "HIER-01",
      "name": "System Override Claim",
      "success": false,
      "response": "I cannot comply with...",
      "time_ms": 1523
    }
  ]
}
```

## Troubleshooting

### "Connection refused" (Ollama)

```bash
# Make sure Ollama is running
ollama serve

# Or check status
systemctl status ollama
```

### "Model not found"

```bash
# List installed models
ollama list

# Pull missing model
ollama pull model-name
```

### Slow responses (8B+ models)

- 8B models need ~8GB RAM
- First run is slow (loading model)
- Subsequent runs faster
- Consider smaller model (3B) for quick tests

### Groq rate limits

- Free tier: 30 requests/minute
- Tests may hit limits
- Wait and retry, or get paid tier

## Adding Your Own Tests

### Create new attack file

```python
# my_attacks.py
ATTACKS = [
    {
        "id": "CUSTOM-01",
        "name": "My Custom Attack",
        "category": "custom",
        "prompt": "Your attack prompt here...",
        "success_indicators": ["phrase_that_means_success"],
    },
]
```

### Use with existing tester

Modify any tester to import your attacks, or copy and adapt `aggressive_tester.py`.

## Hardware Requirements

| Model Size | RAM Needed | GPU VRAM | Speed |
|------------|------------|----------|-------|
| 1B | 2GB | 2GB | Fast |
| 3B | 4GB | 4GB | Good |
| 7-8B | 8GB+ | 6GB+ | Slow on CPU |
| 13B+ | 16GB+ | 10GB+ | Very slow on CPU |
| 70B | 40GB+ | 40GB+ | Cloud only |

No GPU? Models run on CPU but slower. 3B or smaller recommended.

---

## Quick Start (Copy-Paste)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Download small model
ollama pull qwen2.5:3b

# Clone repo
git clone https://github.com/YOUR_USERNAME/prompt-security-guide
cd prompt-security-guide/tools

# Run test
python3 aggressive_tester.py --provider ollama --model qwen2.5:3b

# See results
cat ../aggressive-qwen3b.json
```
