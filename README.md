# Prompt Security Guide

Local LLM prompt-injection testing toolkit with real vulnerability data.


## Key Research Findings

-  **Model size ≠ safety**: smaller models can outperform larger ones on specific defenses.
-  **Detector choice matters**: the same attack outputs can score very differently under `substring` vs `llm_judge`.
-  **Structural attacks work**: JSON/XML/comment-boundary style injections are consistently effective.
-  **Multi-turn setup amplifies risk** in combination with structural payloads.

## What's Included

- 61 attack patterns across multiple categories
- Real local test results for Qwen 2.5 (1.5B, 3B) and Llama 3 (8B)
- Two detection modes: `substring` and `llm_judge`
- Reproducible run metadata (seed and temperature controls)

## Quick Start

```bash
python3 -m tools.cli --provider ollama --model qwen2.5:3b
python3 -m tools.cli -p ollama -m qwen2.5:3b --detector llm_judge
python3 -m tools.cli --list-categories
```

## Documentation

| Document | Contents |
|---|---|
| [docs/MODEL_COMPARISON.md](docs/MODEL_COMPARISON.md) | Cross-model and cross-detector analysis |
| [docs/METHODOLOGY.md](docs/METHODOLOGY.md) | Testing procedure and reproducibility controls |
| [docs/ATTACK_TAXONOMY.md](docs/ATTACK_TAXONOMY.md) | Attack classification and categories |
| [docs/NEW_ATTACK_FINDINGS.md](docs/NEW_ATTACK_FINDINGS.md) | Novel attack development notes |
| [docs/LIMITATIONS.md](docs/LIMITATIONS.md) | Scope and caveats |

## Results

All run artifacts are in [`results/`](results/) and include schema-aware JSON with:

- timestamp and model/detector metadata
- per-attack success/failure, confidence, and errors
- category-level aggregation

Start with:

- [results/ANALYSIS_SUMMARY.md](results/ANALYSIS_SUMMARY.md)
- [results/README.md](results/README.md)

## Repository Structure

```text
prompt-security-guide/
├── README.md
├── CONCLUSIONS.md
├── tools/
├── docs/
├── tests/
└── results/
```

## Limitations

This is exploratory research, not a formal benchmark or security certification.
Validate findings in your own environment before making high-stakes decisions.

## Responsible Use

Use this toolkit only on systems you own or are explicitly authorized to test.

- Security reporting policy: [SECURITY.md](SECURITY.md)
- Usage disclaimer: [DISCLAIMER.md](DISCLAIMER.md)
