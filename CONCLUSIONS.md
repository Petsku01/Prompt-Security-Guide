# Conclusions and Highlights

## Primary Findings

1. Local prompt-injection vulnerability is real and observable in repeatable tests.
2. Detection method strongly affects measured success rates.
3. Structural attack patterns frequently outperform emotional manipulation.
4. **Detector choice can have larger effect than model choice** across tested local models.
5. **Model size ≠ safety**: moving from 1.5B → 3B → 8B did not produce monotonic safety gains.
6. **Multi-turn + structure is the strongest recurring pattern** in aligned subsets.

## February 2026 Findings (New)

Using six test files from 2026-02-15:

- qwen2.5:1.5b — substring 58.8% vs llm_judge 14.3% (**+44.5pp**)
- qwen2.5:3b — substring 78.6% vs llm_judge 41.7% (**+36.9pp**)
- llama3:8b — substring 78.6% vs llm_judge 21.4% (**+57.1pp**)

## Practical Lessons

- Do not rely on a single detector; compare `substring` and `llm_judge` outputs.
- Review category-level outcomes, not just total percentages.
- Re-test after model/runtime updates because behavior drifts.
- Keep run metadata (`schema_version`, seed, temperatures) for reproducibility.

## What This Project Is

- A practical local red-team harness for prompt-security exploration.
- A collection of attack patterns and reproducible test runs.

## What This Project Is Not

- A definitive benchmark of all models.
- A substitute for formal human-reviewed security evaluation.

## Recommendation

Use this toolkit as a fast local signal generator, then follow up with deeper evaluation for high-stakes deployments.
