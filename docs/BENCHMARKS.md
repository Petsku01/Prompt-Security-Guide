# Benchmarks

## Classifier Baseline Performance

Source: `psg/security/baseline_metrics.json`

| Metric | Value |
|---|---:|
| Golden set | `datasets/classifier_golden.json` (v1.0) |
| Total examples | 50 |
| Overall accuracy | 0.940 |
| Flagged accuracy | 0.940 |
| Macro F1 | 0.925 |
| Critical regressions (`refusal -> success`) | 0 |

Per-class baseline metrics:

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| `refusal` | 0.938 | 1.000 | 0.968 | 15 |
| `success` | 1.000 | 1.000 | 1.000 | 15 |
| `partial` | 0.833 | 1.000 | 0.909 | 10 |
| `harmful_with_disclaimer` | 1.000 | 0.700 | 0.824 | 10 |

## External Benchmark Comparison Template

Use this table to track PSG performance against HarmBench/JailbreakBench over time.

| Date | Model | Dataset | Samples | Attack Success Rate | Refusal Rate | Macro F1 | Notes |
|---|---|---|---:|---:|---:|---:|---|
| YYYY-MM-DD | model-name | PSG Golden | 50 | - | - | 0.000 | classifier eval |
| YYYY-MM-DD | model-name | HarmBench | - | 0.00 | 0.00 | - | add source link |
| YYYY-MM-DD | model-name | JailbreakBench | - | 0.00 | 0.00 | - | add source link |

## Recent Model Test Runs (results/)

Latest available runs in `results/` (March 23, 2026):

| File | Model | Total | Jailbreaks | Jailbreak Rate |
|---|---|---:|---:|---:|
| `results/effective_granite3-dense_2b.json` | `granite3-dense:2b` | 20 | 15 | 75.0% |
| `results/effective_stablelm2_1.6b.json` | `stablelm2:1.6b` | 20 | 19 | 95.0% |
| `results/effective_smollm2_1.7b.json` | `smollm2:1.7b` | 20 | 19 | 95.0% |

## How To Run Benchmarks

Run test suite:

```bash
python3 -m pytest tests/test_psg_*.py
```

Run classifier golden evaluation:

```bash
python3 -m psg.security.evaluate --golden datasets/classifier_golden.json
```

(Optional) Write/update baseline snapshot:

```bash
python3 -m psg.security.evaluate \
  --golden datasets/classifier_golden.json \
  --baseline-out psg/security/baseline_metrics.json
```

Run catalog validation over datasets:

```bash
python3 -m psg.catalog_validator --path datasets/
```

Alternative entrypoint via package main:

```bash
python3 -m psg catalog validate --path datasets/
```
