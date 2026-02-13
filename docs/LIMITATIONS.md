# Limitations and Caveats

This document honestly describes what this research can and cannot tell you.

---

## Sample Size

| Test Type | Sample Size | Minimum for Significance |
|-----------|-------------|-------------------------|
| Attack tests | 16 per model | ~50+ recommended |
| Defense comparison | 8 attacks × 6 defenses | ~30+ attacks recommended |
| Model comparison | 2 models | 5+ across families |

**Impact:** Results may not replicate. A single different outcome in 8 tests = 12.5% swing in reported rates.

---

## Detection Method

Current approach: Check if specific strings (e.g., "COMPROMISED") appear in response.

### Problems

1. **False positives:** Model says "I won't say COMPROMISED" - detected as failure
2. **False negatives:** Model leaks information without using our indicator words
3. **No semantic understanding:** Can't detect subtle information disclosure

### Better Approach (Not Implemented)

- Human review of each response
- Semantic similarity scoring
- Multiple evaluators with inter-rater reliability

---

## Model Coverage

**Tested:** Qwen 2.5 (3B and 1.5B only)

**Not tested:**
- Llama family
- Mistral family
- Commercial APIs (OpenAI, Anthropic, Google)
- Models with safety fine-tuning
- Models with different architectures

**Impact:** Results may not generalize. A model trained differently could show completely different vulnerability patterns.

---

## Attack Sophistication

**What we tested:** Basic, single-shot attacks

**What we didn't test:**
- Multi-turn attacks (building context over conversation)
- Iterative refinement (trying variations based on responses)
- Encoding tricks (base64, unicode, etc.)
- Indirect injection (malicious content in "documents")
- Combined attack chains

**Impact:** Real attackers would likely achieve higher success rates.

---

## Defense Configurations

**What we tested:** System prompt variations only

**What we didn't test:**
- Input filtering/sanitization
- Output filtering
- Rate limiting
- Anomaly detection
- Architectural defenses (separate models for different tasks)
- Fine-tuning for instruction resistance

**Impact:** Prompt-only defenses are known to be weak. Results don't reflect what's achievable with proper architecture.

---

## Statistical Rigor

### What's Missing

- No confidence intervals
- No significance testing
- No power analysis
- No control for random variation
- No repeated trials

### What This Means

The "0% improvement" finding for basic restrictions could be:
- Real effect (restrictions don't help)
- Random variation (too few tests)
- Specific to these attacks (different attacks might show different results)
- Specific to this model (other models might respond differently)

**Honest interpretation:** "We didn't observe improvement in this test" not "Restrictions don't work"

---

## Reproducibility

### What's Good

- Tools are provided
- Exact prompts documented
- Raw data included
- Anyone can re-run tests

### What's Missing

- No seed control for model randomness
- Temperature/sampling parameters not controlled
- Results may vary between runs

---

## Claims We Can Make

| Claim | Supported? |
|-------|-----------|
| "Defense testing is possible with simple tools" | Yes |
| "Some defenses appeared more effective than others in our tests" | Yes |
| "Basic restrictions showed no improvement in this specific test" | Yes |
| "Basic restrictions are useless" | No - overstated |
| "Combined defenses are 37.5% better" | No - not statistically validated |
| "Model size doesn't affect security" | No - n=2 is not evidence |

---

## Recommendations for Readers

1. **Don't cite specific percentages** as if they're established facts
2. **Do run your own tests** on your specific deployment
3. **Treat findings as hypotheses** worth investigating, not conclusions
4. **Read the academic literature** for more rigorous research

---

## What Would Make This Rigorous

| Current State | Needed for Rigor |
|---------------|------------------|
| 8-16 attacks | 100+ diverse attacks |
| 2 models | 10+ across families |
| Substring detection | Human evaluation |
| Single-shot | Multi-turn with refinement |
| No statistics | Confidence intervals, p-values |
| 1 tester | Multiple independent evaluators |
| 1 day of testing | Systematic benchmark development |

---

## Conclusion

This project demonstrates that defense testing is feasible and can surface interesting questions. It does not provide definitive answers.

Use the tools to test your own systems. Don't rely on our numbers for security decisions.

---

*Intellectual honesty requires acknowledging what we don't know.*