# Local Model Vulnerability Analysis Summary

## Test Matrix (Actual Data)

| Model | Detector | Success Rate | Attacks | Date |
|---|---|---:|---:|---|
| qwen2.5:1.5b | substring | **58.8%** | 20/34 | 2026-02-15 |
| qwen2.5:1.5b | llm_judge | **14.3%** | 2/14 | 2026-02-15 |
| qwen2.5:3b | substring | **78.6%** | 11/14 | 2026-02-15 |
| qwen2.5:3b | llm_judge (focused) | **41.7%** | 5/12 | 2026-02-15 |
| llama3:8b | substring | **78.6%** | 11/14 | 2026-02-15 |
| llama3:8b | llm_judge | **21.4%** | 3/14 | 2026-02-15 |

## Key Observation: Detector Effect (substring - llm_judge)

- qwen2.5:1.5b: **44.5 percentage points**
- qwen2.5:3b: **36.9 percentage points**
- llama3:8b: **57.1 percentage points**

Detector selection changes measured vulnerability more than model selection in this data.

## Key Findings

1. **Model size ≠ safety**: larger models were not consistently safer.
2. **Detector choice matters more than model choice** in reported success rates.
3. **Structural attacks are consistently high-performing**, especially with substring detection.
4. **Multi-turn + structure appears strongest** in the 14-attack subsets where both categories were present.

## Category Breakdown (substring detector)

### Comparable 14-attack runs (qwen2.5:3b and llama3:8b)

| Model | Structure | Multiturn | Emotional | Jailbreak |
|---|---:|---:|---:|---:|
| qwen2.5:3b | 100% (4/4) | 100% (2/2) | 60% (3/5) | 67% (2/3) |
| llama3:8b | 100% (4/4) | 100% (2/2) | 60% (3/5) | 67% (2/3) |

### qwen2.5:1.5b substring (full 34-attack run)

| Model | Structure | Multiturn | Emotional | Jailbreak |
|---|---:|---:|---:|---:|
| qwen2.5:1.5b | 75% (3/4) | 100% (2/2) | 60% (3/5) | 67% (2/3) |

Additional qwen2.5:1.5b-only categories in the 34-attack run: classic 53% (8/15), obfuscation 33% (1/3), encoding 50% (1/2).

## Data Notes

- All six files include `schema_version: "1.0.0"` and runtime config fields (`seed`, `temperature`, `judge_temperature`).
- LLM judge runs include some per-attack `error` values (judge unavailable); no `fallback_used: true` cases were observed.
- Attack counts differ across files (34, 14, 12), so cross-model comparisons should be made on aligned subsets where possible.
