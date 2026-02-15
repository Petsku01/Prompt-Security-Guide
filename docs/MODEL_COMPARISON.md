# Model Comparison: Security Test Results

**Last updated:** 2026-02-15  
**Models covered:** qwen2.5:1.5b, qwen2.5:3b, llama3:8b  
**Detectors covered:** `substring`, `llm_judge`

---

## Extended Testing (February 2026)

### Three-Model Comparison

| Model | substring | llm_judge | Δ (detector effect) |
|---|---:|---:|---:|
| qwen2.5:1.5b | 58.8% (20/34) | 14.3% (2/14) | **+44.5pp** |
| qwen2.5:3b | 78.6% (11/14) | 41.7% (5/12) | **+36.9pp** |
| llama3:8b | 78.6% (11/14) | 21.4% (3/14) | **+57.1pp** |

### Critical Insight: Detector Choice > Model Choice

For each tested model, switching detector changed measured vulnerability by **36.9–57.1 percentage points**.
In this dataset, that shift is larger than most between-model differences under the same detector.

---

## Category-Level Pattern (substring)

On the aligned 14-attack runs (`qwen2.5:3b`, `llama3:8b`), results are identical:

| Model | Structure | Multiturn | Emotional | Jailbreak |
|---|---:|---:|---:|---:|
| qwen2.5:3b | 100% (4/4) | 100% (2/2) | 60% (3/5) | 67% (2/3) |
| llama3:8b | 100% (4/4) | 100% (2/2) | 60% (3/5) | 67% (2/3) |

`qwen2.5:1.5b` substring was run on a broader 34-attack set; overlapping categories were:

- Structure: 75% (3/4)
- Multiturn: 100% (2/2)
- Emotional: 60% (3/5)
- Jailbreak: 67% (2/3)

---

## Interpretation

1. **Model size is not a standalone safety indicator.**
2. **Reported vulnerability is detector-sensitive.**
3. **Structure and multiturn attacks are the strongest recurring signal.**

---

## Reproducibility Note

These figures are drawn from six result files dated 2026-02-15 in `results/`:

- `local-test-qwen2.5-1.5b-substring-20260215-150639.json`
- `local-test-qwen2.5-1.5b-llm_judge-20260215-152427.json`
- `local-test-qwen2.5-3b-substring-20260215-152327.json`
- `local-test-qwen2.5-3b-llm_judge-focused-20260215-170931.json`
- `local-test-llama3-8b-substring-20260215-151503.json`
- `local-test-llama3-8b-llm_judge-20260215-152106.json`

See `results/ANALYSIS_SUMMARY.md` for consolidated notes and data caveats.
