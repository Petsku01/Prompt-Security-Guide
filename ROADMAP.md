# ROADMAP.md — prompt-security-guide v4.0

> Suunnitelma repon muuttamiseksi ammattimaiseksi LLM security testing -frameworkiksi.

**Versio:** Draft 1.0  
**Päivitetty:** 2026-03-19  
**Status:** Suunnitteluvaihe

---

## Visio

Muuttaa prompt-security-guide alan standardien mukaiseksi:
- **JailbreakBench**-yhteensopiva metodologia
- **StrongREJECT/HarmBench**-tason evaluaatio
- **OWASP AI Testing Guide** -kategoriat
- **Multi-model benchmarking** tilastollisella tarkkuudella

---

## Vaihe 1: Rakenteen uudistus

### 1.1 Kansiorakenne (Target)

```
prompt-security-guide/
├── README.md                 # Hero + badges + quick start
├── ARCHITECTURE.md           # Tekninen arkkitehtuuri
├── CONTRIBUTING.md           # Kontribuutio-ohjeet
├── SECURITY.md               # Responsible disclosure
├── CHANGELOG.md              # Versiohistoria
├── LICENSE                   # MIT
├── pyproject.toml            # Moderni packaging
├── Makefile                  # make test, make lint, make scan
│
├── psg/                      # Pääpaketti (prompt-security-guide)
│   ├── __init__.py
│   ├── __main__.py           # CLI entry: python -m psg
│   ├── cli.py                # Click/Typer CLI
│   ├── config.py             # Konfiguraatio & defaults
│   │
│   ├── probes/               # Hyökkäysvektorit
│   │   ├── __init__.py
│   │   ├── base.py           # BaseProbe class
│   │   ├── jailbreak.py      # DAN, AIM, Grandma, etc.
│   │   ├── injection.py      # Direct & indirect injection
│   │   ├── extraction.py     # Data leak, PII, API keys
│   │   └── encoding.py       # Base64, ROT13, etc.
│   │
│   ├── detectors/            # Tunnistuslogiikka
│   │   ├── __init__.py
│   │   ├── base.py           # BaseDetector class
│   │   ├── pattern.py        # Regex, keyword matching
│   │   ├── refusal.py        # Refusal detection
│   │   └── llm_judge.py      # LLM-as-judge (StrongREJECT style)
│   │
│   ├── generators/           # LLM-yhteydet
│   │   ├── __init__.py
│   │   ├── base.py           # BaseGenerator class
│   │   ├── ollama.py         # Ollama API
│   │   ├── openai.py         # OpenAI-compatible
│   │   └── anthropic.py      # Claude API
│   │
│   ├── evaluation/           # Tilastollinen evaluaatio
│   │   ├── __init__.py
│   │   ├── metrics.py        # Accuracy, precision, recall, F1
│   │   ├── statistical.py    # Wilson CI, bootstrap
│   │   └── cost.py           # Token & cost tracking
│   │
│   └── reporting/            # Raportointi
│       ├── __init__.py
│       ├── json.py           # JSON/JSONL output
│       ├── markdown.py       # Markdown reports
│       └── html.py           # Interactive HTML
│
├── datasets/                 # Hyökkäysdatasetit
│   ├── README.md             # Dataset documentation
│   ├── jbb_behaviors.json    # JailbreakBench aligned
│   ├── strongreject.json     # StrongREJECT categories
│   ├── owasp_aitg.json       # OWASP AI Testing Guide
│   └── custom/               # Custom datasets
│
├── docs/                     # Dokumentaatio
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
├── examples/                 # Käyttöesimerkit
│   ├── basic_scan.py
│   ├── multi_model.py
│   ├── custom_probe.py
│   └── ci_integration.py
│
├── tests/                    # Pytest testit
│   ├── conftest.py
│   ├── test_probes.py
│   ├── test_detectors.py
│   ├── test_generators.py
│   └── test_cli.py
│
├── results/                  # .gitignored (paitsi samples/)
│   └── samples/              # Kuratoidut esimerkit
│
├── _archive/                 # Vanha koodi (.gitignored)
│
└── .github/
    └── workflows/
        ├── test.yml          # CI testit
        ├── lint.yml          # Ruff/Black
        └── release.yml       # PyPI julkaisu
```

### 1.2 Migraatio nykyisestä

| Nykyinen | Uusi | Toimenpide |
|----------|------|------------|
| Nykyinen runtime-moduulirakenne | `psg/` | Refaktoroi & uudelleennimeä |
| `archive/` | `_archive/` | Yhdistä, .gitignore |
| `legacy/` | `_archive/` | Yhdistä |
| `auto_pipeline/` | `psg/automation/` tai erillinen | Päätettävä |
| `models/`, `profiles/` | Poista tai dokumentoi | Tarkista tarve |
| `*.sh` scriptit | `Makefile` | Konsolidoi |

---

## Vaihe 2: Testausmetodologia

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

### 2.2 Evaluaatio-strategiat

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

### 2.4 Tilastollinen tarkkuus

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

## Vaihe 3: CLI & UX

### 3.1 Uusi CLI (Typer-based)

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
	black --check psg/

scan:
	python -m psg scan --model ollama/llama3:8b --probes quick

benchmark:
	python -m psg benchmark --config benchmarks/standard.yaml

clean:
	rm -rf results/*.json _archive/
```

---

## Vaihe 4: Dokumentaatio

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

- `docs/methodology/overview.md` — Mitä testataan ja miksi
- `docs/methodology/threat-model.md` — OWASP AI Threats mapping
- `docs/methodology/evaluation.md` — Judge design, metrics
- `docs/methodology/reproducibility.md` — Miten toistaa tulokset

---

## Vaihe 5: CI/CD & Quality

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

## Aikataulu (ehdotus)

| Vaihe | Kuvaus | Arvio |
|-------|--------|-------|
| **1** | Rakenteen uudistus | 2-3 päivää |
| **2** | Probe/Detector refaktori | 3-4 päivää |
| **3** | CLI uudistus | 1-2 päivää |
| **4** | Dokumentaatio | 2-3 päivää |
| **5** | CI/CD | 1 päivä |
| **6** | Testaus & hionta | 2-3 päivää |
| **Total** | | ~2 viikkoa |

---

## Avoimet kysymykset

1. **Paketin nimi?** `psg` vs `prompt-security-guide` vs jokin muu?
2. **auto_pipeline säilytys?** Erillinen moduuli vai integroitu?
3. **JailbreakBench integraatio?** Suora riippuvuus vai vain aligned?
4. **PyPI julkaisu?** Heti vai myöhemmin?

---

## Seuraavat askeleet

1. [ ] Hyväksy ROADMAP.md
2. [ ] Luo `psg/` rakenne
3. [ ] Migroi vanha runtime-rakenne → `psg/`
4. [ ] Siirrä vanhat → `_archive/`
5. [ ] Päivitä `pyproject.toml`
6. [ ] Kirjoita uusi README.md

---

*Tämä dokumentti on elävä suunnitelma. Päivitä kun päätöksiä tehdään.*
