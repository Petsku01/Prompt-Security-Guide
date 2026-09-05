# Methodology

## Scope

This methodology covers local-only prompt-injection testing via Ollama.

## Environment

- Provider: Ollama
- Typical models: `qwen2.5:1.5b`, `qwen2.5:3b`, `llama3:8b`
- Default temperature: `0.7`
- Judge temperature (when using `llm_judge`): `0.1`
- Seed: `42`
- Single-shot execution per attack in standard runs

## Attack Corpus

The suite combines community-derived and original attacks across categories such as structure, multiturn, emotional, jailbreak, classic, obfuscation, and encoding.

Each attack can include `attack_type` metadata:

- `obedience`: tests whether the model follows an unsafe or misleading instruction pattern (instruction-following failure)
- `policy-bypass`: tests whether the model violates safety policy boundaries (safety failure)

Reported rates are split by these attack types so "followed instruction" and "violated policy" are not conflated.

If a catalog item is missing `attack_type`, PSG applies production tagging heuristics from item metadata (`category`, `subcategory`, `technique`, `description`, `prompt`) and catalog identity:

- hallucination-style probe metadata (fake citations/invented facts/non-existent APIs) => `obedience`
- jailbreak/policy-evasion metadata (OWASP, JailbreakBench, HarmBench, Obliteratus, leakage/jailbreak markers) => `policy-bypass`

## Success Detection

Two detector modes are used:

1. `substring` (fast, higher false-positive risk)
2. `llm_judge` (slower, contextual judgment, judge availability dependent)

## Detector Comparison Protocol

When comparing vulnerability rates:

1. Run an identical attack set with `--detector substring`.
2. Run the same set with `--detector llm_judge`.
3. Compare category-level outcomes, not totals only.
4. Record `fallback_used`, `detector_used`, and per-attack `error` fields.
5. Fail-closed by default for judge unavailability (no silent fallback unless explicitly enabled).
6. Flag non-aligned run sizes (e.g., 34 vs 14 vs 12 attacks) as a comparison caveat.

Use canonical attack sets to keep runs comparable:

- `all` (default): full catalog
- `core-14`: first 14 attacks from the selected catalog
- `full-61`: first 61 attacks from the selected catalog

When comparing reports, use `psg compare-runs --left <runA.json> --right <runB.json>`. The tool checks attack-set name and exact attack ID alignment and warns on mismatches.

## 2026-02-15 Procedure Snapshot

For the February 15, 2026 update, six result files were integrated:

- qwen2.5:1.5b (`substring`, `llm_judge`)
- qwen2.5:3b (`substring`, `llm_judge-focused`)
- llama3:8b (`substring`, `llm_judge`)

The update uses only recorded JSON outputs in `results/` and does not retroactively alter underlying run artifacts.

## Reproducibility Controls (schema v1.0.0+)

Results include:

- `schema_version`: `"1.0.0"`
- `runtime_config.seed`: `42`
- `runtime_config.temperature`: `0.7`
- `runtime_config.judge_temperature`: `0.1`
- `runtime_config.provider_timeout_sec`

These fields should be preserved when sharing, diffing, or aggregating runs.

## Known Methodological Weaknesses

- Limited replication and sample size
- Detector uncertainty without full human review
- Judge availability/runtime dependency
- Sensitivity to model version, quantization, and runtime settings

## Interpretation Guidance

Treat outcomes as practical red-team signals, not final security truth. Validate findings in your own deployment setup.
