# Results Directory

## File Naming Convention

Preferred format:

`{type}-{model}-{detector}-{YYYYMMDD-HHMMSS}.json`

Examples:

- `local-test-qwen2.5-3b-llm_judge-focused-20260215-170931.json`
- `local-test-llama3-8b-substring-20260215-151503.json`

Legacy files (for example `full-61-substring.json`) are retained as historical artifacts.

## Latest Runs (2026-02-15)

| File | Model | Detector | Attacks | Success |
|---|---|---|---:|---:|
| `local-test-qwen2.5-1.5b-substring-20260215-150639.json` | qwen2.5:1.5b | substring | 34 | 58.8% |
| `local-test-qwen2.5-1.5b-llm_judge-20260215-152427.json` | qwen2.5:1.5b | llm_judge/qwen2.5:3b | 14 | 14.3% |
| `local-test-qwen2.5-3b-substring-20260215-152327.json` | qwen2.5:3b | substring | 14 | 78.6% |
| `local-test-qwen2.5-3b-llm_judge-focused-20260215-170931.json` | qwen2.5:3b | llm_judge/qwen2.5:1.5b | 12 | 41.7% |
| `local-test-llama3-8b-substring-20260215-151503.json` | llama3:8b | substring | 14 | 78.6% |
| `local-test-llama3-8b-llm_judge-20260215-152106.json` | llama3:8b | llm_judge/qwen2.5:3b | 14 | 21.4% |

## Quick Notes

- Attack counts are not fully aligned across all files; compare like-for-like subsets when possible.
- JSON schema fields (`schema_version`, `runtime_config`) are present for reproducibility.
- See `ANALYSIS_SUMMARY.md` for integrated interpretation.
