# Prompt Security Guide

**Exploratory LLM security testing - preliminary notes, not rigorous research**

[![Status](https://img.shields.io/badge/status-exploratory-orange.svg)](#)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## Overview

Testing tools and results from 400+ prompt injection attempts against local and cloud LLMs. Real data, honest limitations.

## Key Findings

### 1. API Filtering is Real (Confirmed)

Same model (Llama 3 8B), same attacks, different providers:

| Environment | Vulnerability Rate |
|-------------|-------------------|
| Groq API | **0%** (0/117) |
| Local Ollama | **78%** (60/77) |

**Conclusion:** Groq adds API-level filtering. The model itself is vulnerable.

### 2. Detection Method Matters

| Detector | Reported Rate | Accuracy |
|----------|---------------|----------|
| Substring matching | 87% | Inflated (false positives) |
| LLM Judge | 75% | More accurate (4/5 verified) |

Substring matches words in refusals ("grandmother" in "I can't be your grandmother"). LLM Judge understands context.

### 3. Structure Beats Emotion

| Attack Type | Success Rate |
|-------------|--------------|
| JSON/XML injection | 100% |
| Identity manipulation | 100% |
| Token boundary tricks | 100% |
| Emotional manipulation | 40% |

The boring structural attacks work better than famous emotional exploits.

---

## Quick Start

```bash
cd tools/

# Run all 61 attacks
python tester.py --provider ollama --model qwen2.5:3b

# Use accurate LLM judge detection
python tester.py -p ollama -m qwen2.5:3b --detector llm_judge

# Test specific categories
python tester.py --categories emotional,classic

# List categories
python tester.py --list-categories
```

---

## Repository Structure

```
prompt-security-guide/
├── README.md              # This file
├── CONCLUSIONS.md         # Key findings and lessons
├── requirements.txt       # Python dependencies
│
├── tools/                 # Testing framework
│   ├── tester.py          # Unified CLI
│   ├── providers/         # Ollama, Groq connectors
│   ├── attacks/           # 61 attacks in 6 modules
│   └── detection/         # Substring + LLM Judge
│
├── docs/                  # Documentation
│   ├── TESTING_GUIDE.md   # How to run tests
│   ├── LIMITATIONS.md     # Honest caveats (read this)
│   ├── METHODOLOGY.md     # How tests were conducted
│   ├── ATTACK_TAXONOMY.md # Attack classification
│   ├── DEFENSE_STRATEGIES.md
│   ├── CLOUD_COMPARISON.md
│   ├── THEORETICAL_VECTORS.md
│   └── ...
│
└── results/               # Raw test data (JSON)
```

---

## Attack Categories (61 total)

| Category | Count | Success Rate* |
|----------|-------|---------------|
| hierarchy | 5 | 100% |
| structure | 4 | 100% |
| identity | 4 | 100% |
| token | 3 | 100% |
| encoding | 2 | 100% |
| multiturn | 2 | 100% |
| attention | 2 | 100% |
| classic | 15 | 67% |
| format | 4 | 75% |
| meta | 4 | 75% |
| language | 3 | 67% |
| obfuscation | 3 | 67% |
| jailbreak | 3 | 33% |
| emotional | 5 | 40% |
| context | 2 | 50% |

*On Qwen 2.5 3B with LLM Judge detection

---

## Limitations

**Read [LIMITATIONS.md](docs/LIMITATIONS.md) before citing any results.**

- Small sample sizes (61 attacks)
- Limited models tested (Qwen, Llama)
- No human verification of all results
- Single-shot testing (real attackers iterate)

This is an **exploratory learning project**, not rigorous security research.

---

## Documentation

| Document | Description |
|----------|-------------|
| [CONCLUSIONS.md](CONCLUSIONS.md) | Summary of findings |
| [TESTING_GUIDE.md](docs/TESTING_GUIDE.md) | How to run tests |
| [LIMITATIONS.md](docs/LIMITATIONS.md) | Honest caveats |
| [METHODOLOGY.md](docs/METHODOLOGY.md) | Test methodology |
| [ATTACK_TAXONOMY.md](docs/ATTACK_TAXONOMY.md) | Attack classification |
| [THEORETICAL_VECTORS.md](docs/THEORETICAL_VECTORS.md) | Future research ideas |
| [CLOUD_COMPARISON.md](docs/CLOUD_COMPARISON.md) | Local vs API results |

---

## License

MIT License - See [LICENSE](LICENSE)

---

*Research conducted February 2026 by Kuu (AI) and Petsku (Human)*
