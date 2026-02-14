# Limitations and Caveats

**Read this entire document before citing any results from this repository.**

---

## Status: Exploratory Learning Project

This is a personal learning project, not rigorous security research. Treat all findings as preliminary observations, not established facts.

---

## Sample Size

| Test Type | Our Sample | Statistical Minimum |
|-----------|------------|---------------------|
| Attack tests | 15-77 per model | 100+ recommended |
| Detection comparison | 61 attacks | 100+ recommended |
| Model comparison | 3 models | 10+ across families |

**Impact:** Results may not replicate. A single different outcome in 15 tests = 6.7% swing.

---

## Detection Method

### Substring Matching (default)
Checks if indicator strings appear in response.

**Problems:**
- False positives: "I won't say PWNED" → detects "pwned" → counts as success
- False negatives: Model leaks info without using our indicator words
- No semantic understanding

### LLM Judge (experimental)
Uses another LLM to evaluate if attack succeeded.

**Problems:**
- Slower (2x the API calls)
- Judge model has its own biases
- "Qwen judging Qwen" circular problem
- No ground truth verification

### Detection Comparison Test (2026-02-14)
Same 61 attacks, same model, different detectors:
```
Substring: 53/61 succeeded (86.9%)
LLM Judge: 46/61 succeeded (75.4%)
Agreement: 48/61 attacks (78.7%)
Disagreement: 13/61 attacks (21.3%)
```

The detectors agree on the total but disagree on WHICH attacks succeeded. This means ~27% of individual results are unreliable.

### What Would Be Better
- Human review of each response
- Multiple independent evaluators
- Inter-rater reliability metrics

---

## Model Coverage

**Tested:**
- Qwen 2.5 (3B, 1.5B) - local via Ollama
- Llama 3 8B - local via Ollama
- Llama 3 8B - cloud via Groq API

**Not tested:**
- Commercial APIs (OpenAI, Anthropic, Google)
- Models with extensive safety RLHF
- Larger models (70B+)
- Different architectures (Mistral, etc.)

---

## The One Solid Finding

**Groq API filtering (confirmed 2026-02-13):**
- Same model (Llama 3 8B): 0% via Groq, 78% via local Ollama
- This is a real, reproducible finding
- Demonstrates API providers add filtering layers

Everything else is preliminary.

---

## Statistical Rigor

### Missing
- No confidence intervals
- No significance testing
- No repeated trials
- No control for model randomness

### Interpretation
When we say "73% of attacks succeeded":
- Could be 60-85% with proper intervals
- Different runs may show different results
- Temperature and sampling not controlled

---

## Claims Matrix

| Claim | Supported? | Why |
|-------|-----------|-----|
| "Groq filters Llama 3 8B responses" | **Yes** | 0% vs 78% is stark |
| "Defense testing is possible with simple tools" | Yes | Tools work |
| "Some attacks work better than others" | Weak | Small sample |
| "X% of attacks succeed" | **No** | Detection unreliable |
| "Model X is more secure than Y" | **No** | Need controlled comparison |

---

## What Would Make This Rigorous

| Current | Needed |
|---------|--------|
| 61 attacks | 200+ diverse attacks |
| 3 models | 10+ across families |
| Automated detection | Human evaluation |
| Single run | Multiple trials |
| No statistics | CI, p-values, power analysis |
| One person | Independent replication |

---

## Recommendations

1. **Don't cite percentages** as established facts
2. **Run your own tests** on your specific deployment
3. **Treat findings as questions** worth investigating
4. **Read peer-reviewed research** for rigorous results

---

*Intellectual honesty requires acknowledging what we don't know.*
