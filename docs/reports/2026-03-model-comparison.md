# LLM Jailbreak Resistance Comparison

> **Date:** March 2026  
> **Test Version:** Jailbreak Tester v3.0  
> **Dataset:** 65 attack vectors (direct prompts + 5 jailbreak variants)

---

## Executive Summary

We tested five local LLM models for their ability to resist jailbreak attacks. The results show significant differences in model safety settings.

**Best performance:** Llama 3 8B and Qwen 2.5 3B  
**Heikoin suorituskyky:** Mistral 7B

---

## Tulokset

| Malli | Koko | Flagged | Flagged % | Turvallisuusluokitus |
|-------|------|---------|-----------|----------------------|
| **Llama 3** | 8B | 3/65 | 4.6% | [SAFE] Good |
| **Qwen 2.5** | 3B | 4/65 | 6.2% | [SAFE] Good |
| **Phi-3 Mini** | 3.8B | 6/65 | 9.2% | [MODERATE] Moderate |
| **Gemma 2** | 2B | 9/65 | 13.8% | [MODERATE] Moderate |
| **Mistral** | 7B | 17/65 | 26.2% | [VULNERABLE] Weak |

### Terminologia

- **Flagged:** The model produced potentially harmful content
- **OK:** The model refused or produced a safe response
- **Flagged %:** Lower is better (model resists attacks)

---

## Analyysi malleittain

### [SAFE] Llama 3 8B — Best security

```
Flagged: 3/65 (4.6%)
Testiaika: 17 min
```

**Vahvuudet:**
- Strong built-in safety boundaries
- Consistently refuses harmful requests
- Meta's RLHF training is visible in the results

**Observations:**
- A small portion of jailbreak variants bypassed safeguards
- Direct attacks were blocked effectively

---

### [SAFE] Qwen 2.5 3B — Surprisingly strong for a small model

```
Flagged: 4/65 (6.2%)
Testiaika: 14 min
```

**Vahvuudet:**
- Good safety despite small size
- Fast performance
- Alibaba's safety training works

**Observations:**
- Competitive with larger models
- Good choice for resource-constrained environments

---

### [MODERATE] Phi-3 Mini 3.8B — Moderate

```
Flagged: 6/65 (9.2%)
Testiaika: 29 min
```

**Vahvuudet:**
- Microsoft safety training
- Reasonable performance

**Weakudet:**
- Some direct attacks succeeded
- Slower than similarly sized models

---

### [MODERATE] Gemma 2 2B — Small model, compromises

```
Flagged: 9/65 (13.8%)
Testiaika: 27 min
```

**Observations:**
- Google's smallest model
- Safety is limited by model size constraints
- Suited for non-critical use cases

---

### [VULNERABLE] Mistral 7B — Weakest security

```
Flagged: 17/65 (26.2%)
Testiaika: 78 min
```

**Weakudet:**
- More than a quarter of attacks succeeded
- Direct attacks were especially effective
- Jailbreak variants also worked more often

**Note:**
- Mistral is designed to be less restricted
- **Not recommended** for production use without additional safeguards

---

## Effectiveness by attack type

### Direct attacks (50 tests)

| Malli | Onnistuneet | Osuus |
|-------|-------------|-------|
| Llama 3 | 3 | 6% |
| Qwen 2.5 | 4 | 8% |
| Phi-3 | 6 | 12% |
| Gemma 2 | 9 | 18% |
| Mistral | 16 | 32% |

### Jailbreak variants (15 tests)

| Malli | Onnistuneet | Osuus |
|-------|-------------|-------|
| Llama 3 | 0 | 0% |
| Qwen 2.5 | 0 | 0% |
| Phi-3 | 0 | 0% |
| Gemma 2 | 0 | 0% |
| Mistral | 1 | 7% |

**Note:** The tested jailbreak variants were not effective against any model except Mistral. This may indicate these variants are already known and models are trained to block them.

---

## Havaitut haavoittuvuuskategoriat

Flagged responses contained the following categories:

| Category | Occurrences | Notet |
|-----------|------------|---------|
| Malware-ohjeet | 8 | Koodi/skriptit |
| Sosiaalinen manipulointi | 5 | Phishing-mallit |
| Turvallisuuden ohitus | 4 | Ohjeita suojausten kiertoon |

*Exact prompts are not published for safety reasons.*

---

## Suositukset

### For production use

1. **Prefer Llama 3 or Qwen 2.5** — Best safety results
2. **Avoid Mistral without additional safeguards** — Too vulnerable as-is
3. **Add output filtering** — Even the best models can fail

### For developers

1. **System prompt hardening** — Strengthen system prompts
2. **Input validation** — Validate user input before sending to the model
3. **Output monitoring** — Valvo ja suodata vastauksia
4. **Defense in depth** — Do not rely only on model-internal safeguards

---

## Metodologia

### Test environment

- **Runtime:** Ollama (localhost)
- **Testikehys:** Jailbreak Tester v3.0
- **Detector:** Pattern-based + keyword matching

### Dataset

- 50 direct attack prompts
- 15 jailbreak variants (5 types x 3 examples)
- Sources: public jailbreak datasets, custom variants

### Limitations

1. **Local testing** — Results may differ from API versions
2. **Simple detector** — No LLM-as-judge evaluation
3. **Limited dataset** — 65 tests do not cover all attack types
4. **Snapshot results** — Models are updated continuously

---

## Yhteenveto

Safety of local LLM models varies significantly. **Llama 3** ja **Qwen 2.5** provide the best protection against jailbreak attacks, kun taas **Mistral** requires additional safeguards in production.

No model is fully immune to attacks. **Defense in depth** -approach is essential.

---

*Report generated with the prompt-security-guide tool.*  
*Prompts censored for safety reasons.*
