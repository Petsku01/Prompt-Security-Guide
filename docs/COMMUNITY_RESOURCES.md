# Community Jailbreak Resources

A curated list of external jailbreak resources plus guidance on how to interpret them relative to this repository’s measured results.

## Evidence Classification

- **`source=community`**: external claims, reports, forum posts, and third-party repos. Not validated by this repository unless explicitly tested.
- **`source=local_results`**: measured outcomes from artifacts under this repository’s `results/` directory.

---

## External Community Resources (`source=community`)

### 1) elder-plinius/L1B3RT4S
- URL: https://github.com/elder-plinius/L1B3RT4S
- Focus: jailbreak prompt collections and variants.

### 2) SlowLow999/UltraBr3aks
- URL: https://github.com/SlowLow999/UltraBr3aks
- Focus: formatting/attention-breaking and obfuscation-oriented techniques.

### 3) Exocija/ZetaLib
- URL: https://github.com/Exocija/ZetaLib
- Focus: categorized prompt material and attack references.

### 4) Goochbeater/Spiritual-Spell-Red-Teaming
- URL: https://github.com/Goochbeater/Spiritual-Spell-Red-Teaming
- Focus: educational red-team curriculum and staged techniques.

### 5) ACComputing/UniversalJailbreakDB20XX
- URL: https://github.com/ACComputing/UniversalJailbreakDB20XX
- Focus: prompt pattern database and disclosure-oriented templates.

> Note: Resource inclusion does **not** imply endorsement or local validation.

---

## This Repository’s Measured Results (`source=local_results`)

For measured outcomes, use:
- `results/ANALYSIS_SUMMARY.md`
- `results/README.md`
- specific run artifacts under `results/*.json`

### Example local summary table

| Source bucket | Attacks tested | Qwen 3B | Llama 8B | Llama 70B | Evidence tag |
|---|---:|---:|---:|---:|---|
| Plinius-derived set | 11 | 81.8% | 0% | 81.8% | `source=local_results` |
| Advanced 2025 set | 11 | 90.9% | 0% | 81.8% | `source=local_results` |
| Basic patterns | 15 | 86.7% | 0% | 40% | `source=local_results` |

> Comparability caveat: percentages are directional if attack sets/configs differ across runs.

---

## Recommended Usage Pattern

1. Treat community repos as **hypothesis generators**.
2. Re-test claims locally with explicit run metadata.
3. Promote claims to “measured” only when artifacts are present in `results/`.

---

## Legal Notice

These resources are documented for security research and defensive validation. Testing should only be performed on systems you own or are explicitly authorized to test.
