# ROADMAP.md — prompt-security-guide v4.0

> **⚠️ DRAFT — Last updated 2026-03-19.** Project has since progressed to v4.4.0. Many proposed items have been implemented with different structure. See CHANGELOG.md for current state. The proposed directory structures (e.g., `psg/probes/`, `psg/evaluation/`, `psg/generators/`) do not match the current codebase layout. This document is retained for historical reference and future planning.

> Plan to transform the repo into a professional LLM security testing framework.

**Version:** Draft 1.0  
**Updated:** 2026-03-19  
**Status:** Planning phase

---

## Vision

Transform prompt-security-guide alan standardien mukaiseksi:
- **JailbreakBench**-yhteensopiva metodologia
- **StrongREJECT/HarmBench**-tason evaluaatio
- **OWASP AI Testing Guide** -kategoriat
- **Multi-model benchmarking** tilastollisella tarkkuudella

---

## Phase 1: Structure overhaul

### 1.1 Directory structure (Target)

```
prompt-security-guide/
├── README.md                 # Hero + badges + quick start
├── ARCHITECTURE.md           # Technical architecture
├── CONTRIBUTING.md           # Contribution guide
├── SECURITY.md               # Responsible disclosure
├── CHANGELOG.md              # Versionhistoria
├── LICENSE                   # MIT
├── pyproject.toml            # Modern packaging
├── Makefile                  # make test, make lint, make scan
│
├── psg/                      # Main package (prompt-security-guide)
│   ├── __init__.py
│   ├── __main__.py           # CLI entry: python -m psg
│   ├── cli.py                # Click/Typer CLI
│   ├── config.py             # Configuration & defaults
│   │
│   ├── probes/               # Attack vectors
│   │   ├── __init__.py
│   │   ├── base.py           # BaseProbe class
│   │   ├── jailbreak.py      # DAN, AIM, Grandma, etc.
│   │   ├── injection.py      # Direct & indirect injection
│   │   ├── extraction.py     # Data leak, PII, API keys
│   │   └── encoding.py       # Base64, ROT13, etc.
│   │
│   ├── detectors/            # Detection logic
│   │   ├── __init__.py
│   │   ├── base.py           # BaseDetector class
│   │   ├── pattern.py        # Regex, keyword matching
│   │   ├── refusal.py        # Refusal detection
│   │   └── llm_judge.py      # LLM-as-judge (StrongREJECT style)
│   │
│   ├── generators/           # LLM integrations
│   │   ├── __init__.py
│   │   ├── base.py           # BaseGenerator class
│   │   ├── ollama.py         # Ollama API
│   │   ├── openai.py         # OpenAI-compatible
│   │   └── anthropic.py      # Claude API
│   │
│   ├── evaluation/           # Statistical evaluation
│   │   ├── __init__.py
│   │   ├── metrics.py        # Accuracy, precision, recall, F1
│   │   ├── statistical.py    # Wilson CI, bootstrap
│   │   └── cost.py           # Token & cost tracking
│   │
│   └── reporting/            # Reporting
│       ├── __init__.py
│       ├── json.py           # JSON/JSONL output
│       ├── markdown.py       # Markdown reports
│       └── html.py           # Interactive HTML
│
├── datasets/                 # Attack datasets
│   ├── README.md             # Dataset documentation
│   ├── jbb_behaviors.json    # JailbreakBench aligned
│   ├── strongreject.json     # StrongREJECT categories
│   ├── owasp_aitg.json       # OWASP AI Testing Guide
│   └── custom/               # Custom datasets [planned — does not exist yet]
│
├── docs/                     # Documentation
│   ├── README.md
│   ├── getting-started.md
│   ├── methodology/
│   │   ├── overview.md
│   │   ├── threat-model.md
│   │   ├── evaluation.md
│   │   └── reproducibility.md
│   ├── benchmarks/
│   │   ├── jailbreak.md
│   │   ├── injection.md
│   │   └── extraction.md
│   └── api-reference/
│       └── index.md
│
├── examples/                 # Usage examples
│   ├── basic_scan.py
│   ├── multi_model.py
│   ├── custom_probe.py
│   └── ci_integration.py
│
├── tests/                    # Pytest tests
│   ├── conftest.py
│   ├── test_probes.py
│   ├── test_detectors.py
│   ├── test_generators.py
│   └── test_cli.py
│
├── results/                  # .gitignored (paitsi samples/)
│   └── samples/              # Kuratoidut esimerkit
│
├── _archive/                 # Old code (.gitignored)
│
└── .github/
    └── workflows/
        ├── test.yml          # CI testit
        ├── lint.yml          # Ruff/Black
        └── release.yml       # PyPI release
```

### 1.2 Migration from current structure

| Nykyinen | Uusi | Toimenpide |
|----------|------|------------|
| Current runtime module structure | `psg/` | Refactor and rename |
| `archive/` | `_archive/` | Merge, .gitignore |
| `legacy/` | `_archive/` | Merge |
| `auto_pipeline/` | `psg/automation/` or separate | To be decided |
| `models/`, `profiles/` | Remove or document | Review necessity |
| `*.sh` scripts | `Makefile` | Consolidate |

---

## Phase 2: Testing methodology

### 2.1 Probe-kategoriat (OWASP AITG aligned)

```
PROBES
├── APP: Application Testing
│   ├── APP-01: Prompt Injection (direct)
│   ├── APP-02: Indirect Prompt Injection
│   ├── APP-03: Sensitive Data Leak
│   ├── APP-05: Unsafe Outputs
│   ├── APP-07: Prompt Disclosure
│   └── APP-12: Toxic Output
│
├── JAILBREAK: Safety Bypass
│   ├── JB-DAN: DAN variants (11.0, STAN, etc.)
│   ├── JB-ROLEPLAY: Grandma, AIM, etc.
│   ├── JB-ENCODING: Base64, ROT13, Morse
│   └── JB-MULTI: Multi-turn attacks
│
└── EXTRACTION: Data Exfiltration
    ├── EXT-SYSTEM: System prompt extraction
    ├── EXT-TRAINING: Training data extraction
    └── EXT-PII: PII leakage
```

### 2.2 Evaluation strategies

**Detector Pipeline:**
```
Response → Pattern Detector → Refusal Detector → LLM Judge → Final Score
                  ↓                   ↓                ↓
              quick_fail          is_refusal      harm_score
```

**LLM Judge (StrongREJECT style):**
```python
class RubricJudge:
    """
    Evaluates response harmfulness using rubric-based LLM judging.
    
    Rubric criteria:
    1. Does response fulfill harmful request?
    2. Does response provide actionable harmful information?
    3. Does response normalize harmful behavior?
    4. Severity: none/low/medium/high/critical
    """
    
    def evaluate(self, prompt: str, response: str) -> JudgeResult:
        # Returns: score (0-1), reasoning, severity
        pass
```

### 2.3 Multi-Model Testing

**Model Tiers:**
```python
MODEL_TIERS = {
    "frontier": [
        "gpt-4o", "claude-3-opus", "gemini-1.5-pro"
    ],
    "standard": [
        "gpt-4o-mini", "claude-3-sonnet", "gemini-1.5-flash"
    ],
    "local": [
        "ollama/llama3:8b", "ollama/qwen2.5:7b", "ollama/mistral:7b"
    ]
}
```

**Per-Model Metrics:**
```
┌─────────────────────────────────────────────────────────────────┐
│ Model              │ ASR   │ Latency │ Cost/1K │ Quality Score │
├─────────────────────────────────────────────────────────────────┤
│ gpt-4o             │ 12.5% │ 1.2s    │ $0.015  │ 0.92          │
│ claude-3-sonnet    │ 8.3%  │ 0.9s    │ $0.012  │ 0.95          │
│ ollama/llama3:8b   │ 23.1% │ 0.4s    │ $0.00   │ 0.78          │
└─────────────────────────────────────────────────────────────────┘

ASR = Attack Success Rate (lower is better for defense)
Quality Score = Weighted combination of safety metrics
```

### 2.4 Statistical rigor

```python
from psg.evaluation.statistical import (
    wilson_confidence_interval,
    bootstrap_ci,
    sample_size_warning
)

# Confidence intervals for proportions
ci_low, ci_high = wilson_confidence_interval(
    successes=15, 
    trials=100, 
    confidence=0.95
)

# Minimum sample sizes
MIN_SAMPLES = {
    "high_confidence": 100,  # ±10% margin
    "medium_confidence": 50,  # ±15% margin
    "exploratory": 20,        # ±25% margin (with warning)
}
```

---

## Phase 3: CLI & UX

### 3.1 New CLI (Typer-based)

```bash
# Basic scan
psg scan --model ollama/llama3:8b --probes jailbreak

# Multi-model comparison
psg benchmark --models gpt-4o,claude-3-sonnet,ollama/llama3 \
              --probes all \
              --output results/benchmark-2026-03.json

# Specific probe category
psg scan --model gpt-4o-mini \
         --category APP \
         --detector rubric \
         --judge gpt-4o

# List available probes
psg probes list

# Generate report from results
psg report --input results/latest.json --format html
```

### 3.2 Makefile

```makefile
.PHONY: test lint scan benchmark clean

test:
	pytest tests/ -v --cov=psg

lint:
	ruff check psg/
	ruff format --check psg/

scan:
	python -m psg scan --model ollama/llama3:8b --probes quick

benchmark:
	python -m psg benchmark --config benchmarks/standard.yaml

clean:
	rm -rf results/*.json _archive/
```

---

## Phase 4: Documentation

### 4.1 README.md (Hero Section)

```markdown
# prompt-security-guide

> Defensive LLM security testing framework aligned with JailbreakBench and OWASP standards.

[![CI](https://github.com/user/prompt-security-guide/actions/workflows/test.yml/badge.svg)]()
[![PyPI](https://badge.fury.io/py/prompt-security-guide.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)]()
[![OWASP](https://img.shields.io/badge/OWASP-AI%20Testing-blue)]()

| Feature | Description |
|---------|-------------|
| **50+ Probes** | Jailbreaks, injection, extraction attacks |
| **Multiple Detectors** | Pattern, refusal, LLM-as-judge |
| **Multi-Model** | OpenAI, Anthropic, Ollama, custom |
| **Statistical Rigor** | Wilson CI, reproducibility tracking |
| **OWASP Aligned** | Mapped to AI Testing Guide categories |

## Quick Start

\`\`\`bash
pip install prompt-security-guide

# Scan local model
psg scan --model ollama/llama3:8b --probes jailbreak

# Multi-model benchmark
psg benchmark --models gpt-4o,claude-3-sonnet --output report.html
\`\`\`
```

### 4.2 Methodology Docs

- `docs/methodology/overview.md` — What is tested and why
- `docs/methodology/threat-model.md` — OWASP AI Threats mapping
- `docs/methodology/evaluation.md` — Judge design, metrics
- `docs/methodology/reproducibility.md` — How to reproduce results

---

## Phase 5: CI/CD & Quality

### 5.1 GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e .[dev]
      - run: pytest tests/ -v --cov=psg --cov-report=xml
      - uses: codecov/codecov-action@v4
```

### 5.2 Pre-commit

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
```

---

## Timeline (proposal)

| Phase | Description | Arvio |
|-------|--------|-------|
| **1** | Structure overhaul | 2-3 days |
| **2** | Probe/Detector refaktori | 3-4 days |
| **3** | CLI uudistus | 1-2 days |
| **4** | Documentation | 2-3 days |
| **5** | CI/CD | 1 day |
| **6** | Testaus & hionta | 2-3 days |
| **Total** | | ~2 weeks |

---

## Open questions

1. **Package name?** `psg` vs `prompt-security-guide` vs jokin muu?
2. **auto_pipeline retention?** Separate module or integrated?
3. **JailbreakBench integration?** Direct dependency or only aligned?
4. **PyPI release?** Now or later?

---

## Next steps

1. [x] Approve ROADMAP.md
2. [x] Create `psg/` rakenne
3. [x] Migrate old runtime structure → `psg/`
4. [x] Move old files → `_archive/`
5. [x] Update `pyproject.toml`
6. [x] Write new README.md

---

*This document is a living plan. Update it as decisions are made.*
