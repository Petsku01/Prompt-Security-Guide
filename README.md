<p align="center">
  <h1 align="center">Prompt Security Guide</h1>
</p>

<p align="center">
  <strong>Educational resource for understanding LLM prompt security</strong>
</p>

<p align="center">
  <a href="#overview">Overview</a> •
  <a href="#what-this-is">What This Is</a> •
  <a href="#what-this-is-not">What This Is Not</a> •
  <a href="#documentation">Documentation</a> •
  <a href="#contributing">Contributing</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/status-educational-blue.svg" alt="Status"/>
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"/>
  <img src="https://img.shields.io/badge/evidence-conceptual-orange.svg" alt="Evidence Level"/>
</p>

---

## Overview

This repository contains educational documentation about security considerations for Large Language Model (LLM) deployments. It synthesizes publicly available knowledge about prompt injection, jailbreaking, and defensive techniques.

## What This Is

- **Educational resource** for learning about LLM security concepts
- **Conceptual framework** for thinking about prompt-based vulnerabilities
- **Starting point** for security practitioners new to AI systems
- **Discussion material** for teams deploying LLMs

## What This Is Not

- **Original research** - This synthesizes existing public knowledge
- **Validated framework** - Defense strategies are theoretical, not empirically tested
- **Production-ready tools** - Code examples are conceptual illustrations
- **Authoritative source** - No formal security audit or peer review

## Actual Test Results

This repository includes **real security testing** performed against local LLM deployments.

### Test Results Summary (February 2026)

| Model | Extraction | Injection | Jailbreak | Total |
|-------|------------|-----------|-----------|-------|
| Qwen 2.5 3B | 4/5 (80%) | 4/5 (80%) | 1/4 (25%) | 11/16 (68.8%) |
| Qwen 2.5 1.5B | 3/5 (60%) | 4/5 (80%) | 1/4 (25%) | 10/16 (62.5%) |

**Key findings:**
- Basic prompt injection ("ignore previous instructions") succeeds on both models
- Fake [SYSTEM] tags are accepted as authoritative
- Smaller model (1.5B) leaked entire system prompt when asked to repeat it
- Larger model (3B) better at rejecting fake authority claims
- Model size does not reliably predict security

See [TEST_RESULTS.md](docs/TEST_RESULTS.md) and [MODEL_COMPARISON.md](docs/MODEL_COMPARISON.md) for full analysis.

### Defense Effectiveness (February 2026)

| Defense Strategy | Vulnerability Rate | Improvement |
|-----------------|-------------------|-------------|
| No defense (baseline) | 87.5% | - |
| "Don't reveal instructions" | 87.5% | 0% |
| Threat enumeration | 62.5% | 25% |
| Combined defenses | 50.0% | 37.5% |

**Key finding:** Simply telling the model "don't reveal your instructions" provides **zero improvement**. Explicit threat enumeration and defense stacking help significantly, but even the best prompt-only defense still fails half the attacks.

See [DEFENSE_EFFECTIVENESS.md](docs/DEFENSE_EFFECTIVENESS.md) for full methodology and recommendations.

### Limitations of Testing

- Results are specific to tested model and configuration
- 16 tests do not cover all possible attack variations
- Other models may show different vulnerability patterns
- Tests were single-shot, not adversarially optimized

---

## Documentation

| Document | Description |
|----------|-------------|
| [Security Guide](docs/SECURITY_GUIDE.md) | Overview of LLM security concepts and attack patterns |
| [Attack Taxonomy](docs/ATTACK_TAXONOMY.md) | Classification of prompt-based attack techniques |
| [Defense Strategies](docs/DEFENSE_STRATEGIES.md) | Conceptual defensive architectures |
| [Testing Framework](docs/TESTING_FRAMEWORK.md) | Methodology for security assessment |
| [Test Results](docs/TEST_RESULTS.md) | Actual test results against Qwen 2.5 3B |
| [Model Comparison](docs/MODEL_COMPARISON.md) | Security comparison: 3B vs 1.5B models |
| [Defense Effectiveness](docs/DEFENSE_EFFECTIVENESS.md) | Which defenses actually work (with data) |

---

## Attack Categories (Conceptual)

### Vulnerability Classes

```
Prompt-Based Vulnerabilities
├── System Prompt Extraction
│   ├── Direct requests for instructions
│   ├── Indirect behavioral probing
│   └── Context reconstruction techniques
├── Instruction Override (Jailbreaking)
│   ├── Authority manipulation
│   ├── Context framing
│   └── Semantic evasion
├── Prompt Injection
│   ├── Direct instruction embedding
│   ├── Indirect injection via external content
│   └── Delimiter confusion
└── Context Manipulation
    ├── Memory pressure attacks
    ├── Attention manipulation
    └── History exploitation
```

### General Observations

Based on public reports and community experience:

- **Undefended systems** are generally vulnerable to basic extraction and injection
- **Keyword filtering** is easily bypassed through semantic variation
- **Constitutional training** reduces but does not eliminate jailbreaking
- **Defense in depth** is more effective than single-layer protection

*Note: These are general observations, not measured statistics.*

---

## Defensive Principles

### Recommended Approach

```
Input Validation
    │
    ▼
Instruction Isolation
    │
    ▼
Capability Restriction
    │
    ▼
Output Validation
    │
    ▼
Monitoring
```

### Key Concepts

1. **Assume compromise** - Design assuming attacks will sometimes succeed
2. **Defense in depth** - Multiple overlapping security layers
3. **Least privilege** - Minimize model capabilities to what's needed
4. **Monitor and respond** - Detect and react to anomalies

---

## Tools

### LLM Security Tester (Functional)

The `tools/llm_security_tester.py` is a **working security testing tool** for Ollama models.

```bash
# Run full test suite against a local model
python tools/llm_security_tester.py --model qwen2.5:3b --output results.json

# Run specific test categories
python tools/llm_security_tester.py --model qwen2.5:3b --categories extraction,injection

# Verbose output
python tools/llm_security_tester.py --model qwen2.5:3b --verbose
```

**Features:**
- 16 test cases across 4 categories (extraction, injection, jailbreak, baseline)
- Configurable system prompt for defense testing
- JSON report output with full responses
- Works with any Ollama-compatible model

### Security Scanner (Conceptual Framework)

The `tools/security_scanner.py` provides a framework structure for testing against remote APIs. Requires implementation for your specific target.

---

## References and Further Reading

This guide draws on publicly available knowledge from:

- OWASP guidance on LLM security
- Academic papers on prompt injection (search: "prompt injection attacks")
- Community research shared on security forums
- Vendor documentation on AI safety

### Recommended Academic Reading

- "Ignore This Title and HackAPrompt" (2023) - Prompt injection competition findings
- "Not What You've Signed Up For" (2023) - Indirect prompt injection research
- OWASP Top 10 for LLM Applications

---

## Contributing

Contributions welcome, especially:

- **Citations** - Adding references to peer-reviewed research
- **Validation** - Testing claims against real systems (with permission)
- **Corrections** - Fixing inaccuracies or unsupported claims
- **Tools** - Developing functional testing implementations

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## Ethical Use

This content is for **educational and authorized defensive purposes**.

**Acceptable:**
- Learning about AI security concepts
- Testing systems you own or have written permission to test
- Developing defenses for your own deployments
- Academic research with proper ethics approval

**Not acceptable:**
- Attacking systems without authorization
- Using techniques to cause harm
- Violating terms of service

---

## License

MIT License - See [LICENSE](LICENSE)

---

## Acknowledgments

This guide synthesizes knowledge from the AI security research community. It does not represent original research and should not be cited as a primary source.

---

<p align="center">
  <em>Educational resource - Use responsibly and verify claims independently</em>
</p>