# Model Comparison (Local Focus)

This repository is now scoped to local testing workflows.

## Scope

- Local provider: **Ollama**
- Goal: evaluate prompt-injection vulnerability patterns across local models
- Excludes: commercial API provider benchmarking

## What to Compare Locally

- Different local model families (Qwen, Llama, etc.)
- Different model sizes (small vs larger local models)
- Detector differences (`substring` vs `llm_judge`)
- Attack-category-level variance

## Practical Guidance

1. Run the same attack set across multiple local models.
2. Keep temperature/system prompt consistent.
3. Compare both aggregate success rate and per-category behavior.
4. Use `llm_judge` when possible to reduce substring false positives.

## Result Hygiene

- Store outputs in `results/`
- Include model and detector in filenames
- Re-run periodically after model updates
