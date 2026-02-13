# Prompt Security Guide

**Empirical LLM security testing with real attack data**

[![Status](https://img.shields.io/badge/status-research-blue.svg)](#)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-300%2B-brightgreen.svg)](#test-results-summary)
[![Models](https://img.shields.io/badge/models-7-orange.svg)](#models-tested)

---

## Overview

This repository contains **real security testing data** from 300+ prompt injection and jailbreak attempts against 7 different LLM deployments. Unlike theoretical guides, every claim here is backed by actual test results.

## Key Findings

### The Llama 3 8B Anomaly (Unresolved)

**Llama 3 8B (via Groq) blocked 100% of all attacks** across 117 different attack vectors.

**IMPORTANT CAVEAT**: We cannot determine if this is due to:
- Llama 3 8B's training (model-level security), or
- Groq's API filtering (provider-level security)

Until we test the same model locally, this finding reflects "Groq's Llama 3 8B endpoint" - not necessarily the model itself. See [GROQ_HYPOTHESIS.md](docs/GROQ_HYPOTHESIS.md).

| Attack Source | Attacks Tested | Llama 3 8B (Groq)* | Llama 3.3 70B (Groq) | Qwen 2.5 3B (local) |
|---------------|----------------|------------|---------------|-------------|
| Plinius/L1B3RT4S (17k stars) | 11 | 0% | 81.8% | 81.8% |
| UltraBr3aks | 11 | 0% | 100% | 72.7% |
| Novel attacks (original) | 14 | 0% | 0% | 92.9% |
| Aggressive (21 vectors) | 21 | 0% | 0% | 81.0% |
| Advanced 2025 research | 11 | 0% | 27.3% | 81.8% |
| Basic proven attacks | 16 | 0% | ~50% | 68.8% |
| **TOTAL** | **117+** | **0%*** | **~50%** | **~80%** |

*\*Llama 3 8B results may reflect Groq API filtering, not model behavior. Verification pending.*

### Counterintuitive Result: Smaller Model More Secure

The 8B parameter model outperformed the 70B model on security:

- **Llama 3 8B**: 0% vulnerability (blocked everything)
- **Llama 3.3 70B**: ~50% vulnerability (selectively vulnerable)
- **Qwen 2.5 3B**: ~80% vulnerability (highly vulnerable)

**Hypothesis**: This may be due to Groq's API-level filtering rather than model training alone. See [GROQ_HYPOTHESIS.md](docs/GROQ_HYPOTHESIS.md) for analysis.

---

## Models Tested

| Model | Provider | Parameters | Tests Run | Vulnerability Rate |
|-------|----------|------------|-----------|-------------------|
| Llama 3 8B | Groq API | 8B | 117 | 0% |
| Llama 3.3 70B | Groq API | 70B | ~90 | ~50% |
| Qwen 2.5 3B | Ollama (local) | 3B | ~90 | ~80% |
| Qwen 2.5 1.5B | Ollama (local) | 1.5B | 16 | 62.5% |

---

## Attack Categories Tested

### 1. Community Jailbreak Repositories

Attacks sourced from major public repositories:

- **elder-plinius/L1B3RT4S** (17k stars) - Plinius attack library
- **SlowLow999/UltraBr3aks** (210 stars) - Attention-breaking techniques
- **ChatGPT_DAN** - Classic DAN persona attacks

### 2. Academic Research Attacks

Based on published security research:

- Policy Puppetry (HiddenLayer 2025)
- Deceptive Delight (Palo Alto Unit 42)
- Crescendo Attack (multi-turn escalation)
- DAP - Disguise and Ambiguity Prompting
- Fallacy Failure exploitation

### 3. Original Novel Attacks

14 new attack vectors developed during this research:

- Language mixing (Finnish/English transitions)
- Token boundary exploitation
- Emotional manipulation (grandmother, urgency)
- Context exhaustion
- Nested encoding schemes

### 4. Aggressive Attack Suite

21 sophisticated vectors across 6 categories:

- Instruction hierarchy attacks
- Prompt structure injection (JSON/XML/Markdown)
- Identity confusion (DAN, roleplay)
- Format hijacking
- Multi-turn simulation
- Meta-instruction manipulation

---

## Test Results Summary

### What Works (on vulnerable models)

| Attack Type | Success Rate on Qwen | Notes |
|-------------|---------------------|-------|
| Emotional manipulation | 100% | Grandmother/urgency framing |
| Attention-Breaking | 100% | UltraBr3aks technique |
| Authority injection | 100% | Fake [SYSTEM] tags |
| Identity reset | 100% | "You are now..." prompts |
| Nested encoding | 92.9% | rot13 + base64 chains |
| DAN persona | 81% | Classic jailbreak |

### What Doesn't Work (on any model)

| Attack Type | Success Rate | Notes |
|-------------|-------------|-------|
| Direct harmful requests | 0% | All models refuse |
| Simple "ignore instructions" | ~25% | Usually detected |
| Obvious role-play ("pretend to be evil") | ~30% | Too transparent |

---

## Defense Effectiveness

Testing 6 defense strategies against 8 attacks:

| Defense | Vulnerability Rate | Improvement |
|---------|-------------------|-------------|
| No defense | 87.5% | baseline |
| "Don't reveal instructions" | 87.5% | 0% |
| Explicit threat enumeration | 62.5% | 25% |
| XML tag isolation | 50.0% | 37.5% |
| Combined defenses | 50.0% | 37.5% |

**Key finding**: Simple "don't reveal" instructions provide no measurable protection. Defense stacking helps but even best prompt-only defenses fail 50% of attacks.

---

## Tools

### Working Testers

```bash
# Test against local Ollama model
python tools/llm_security_tester.py --model qwen2.5:3b

# Test against Groq API
GROQ_API_KEY=xxx python tools/groq_tester.py --model llama3-8b-8192

# Run Plinius attack library
python tools/plinius_tester.py --provider groq --model llama-3.3-70b-versatile

# Run UltraBr3aks attacks
python tools/ultrabreaks_tester.py --provider ollama --model qwen2.5:3b

# Run aggressive attack suite
python tools/aggressive_tester.py --provider groq --model llama3-8b-8192
```

### Available Tools

| Tool | Description |
|------|-------------|
| `llm_security_tester.py` | Basic 16-attack test suite |
| `groq_tester.py` | Groq API testing |
| `plinius_tester.py` | L1B3RT4S attack library |
| `ultrabreaks_tester.py` | Attention-breaking attacks |
| `novel_tester.py` | Original novel attacks |
| `aggressive_tester.py` | 21-vector aggressive suite |
| `defense_tester.py` | Defense strategy comparison |

---

## Documentation

| Document | Description |
|----------|-------------|
| [TESTING_GUIDE.md](docs/TESTING_GUIDE.md) | How to run tests yourself |
| [METHODOLOGY.md](docs/METHODOLOGY.md) | How tests were conducted (READ FIRST) |
| [ATTACK_TAXONOMY.md](docs/ATTACK_TAXONOMY.md) | Classification of attack techniques |
| [COMMUNITY_RESOURCES.md](docs/COMMUNITY_RESOURCES.md) | Major jailbreak repositories analyzed |
| [DEFENSE_STRATEGIES.md](docs/DEFENSE_STRATEGIES.md) | Defensive approaches |
| [DEFENSE_EFFECTIVENESS.md](docs/DEFENSE_EFFECTIVENESS.md) | Which defenses actually work |
| [GROQ_MODEL_COMPARISON.md](docs/GROQ_MODEL_COMPARISON.md) | Llama 8B vs 70B analysis |
| [GROQ_HYPOTHESIS.md](docs/GROQ_HYPOTHESIS.md) | Why Llama 8B blocks everything |
| [LIMITATIONS.md](docs/LIMITATIONS.md) | Honest limitations of this research |
| [REFERENCES.md](docs/REFERENCES.md) | Academic citations |

---

## Limitations (Critical)

**Read [METHODOLOGY.md](docs/METHODOLOGY.md) and [LIMITATIONS.md](docs/LIMITATIONS.md) before citing this research.**

### Why You Should Be Skeptical

| Issue | Impact |
|-------|--------|
| Sample sizes (11-21 per test) | Cannot establish statistical significance |
| Substring detection | False positives/negatives unknown |
| Groq API confound | Llama 8B results may be provider filtering, not model |
| No human verification | Actual attack success not confirmed |
| Single-shot tests | Real attackers iterate and refine |

### What This Research Is

- **Exploratory** - surfaces interesting questions
- **Preliminary** - needs replication
- **Educational** - demonstrates testing methods

### What This Research Is NOT

- **Rigorous** - no statistical validation
- **Generalizable** - 4 configs tested
- **Definitive** - major confounds unresolved

---

## Ethical Use

This content is for **authorized defensive testing and education only**.

Acceptable uses:
- Testing systems you own
- Security research with permission
- Learning about AI security
- Developing defenses

Not acceptable:
- Attacking systems without authorization
- Causing harm
- Violating terms of service

---

## References

### Academic Papers

- Liu et al. (2024) - "Jailbreaking ChatGPT via Prompt Engineering"
- Greshake et al. (2023) - "Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection"
- Perez & Ribeiro (2022) - "Ignore This Title and HackAPrompt"
- OWASP Top 10 for LLM Applications (2023)

### Community Resources

- [elder-plinius/L1B3RT4S](https://github.com/elder-plinius/L1B3RT4S) - 17k stars
- [SlowLow999/UltraBr3aks](https://github.com/SlowLow999/UltraBr3aks) - 210 stars
- HiddenLayer Policy Puppetry (2025)
- Palo Alto Unit 42 Deceptive Delight

---

## License

MIT License - See [LICENSE](LICENSE)

---

*Research conducted February 2026. Results may not replicate on different models or API versions.*
