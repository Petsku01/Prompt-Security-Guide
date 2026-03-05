# ML Judge Design Document

**Author:** Kuu (Opus) + Petsku  
**Date:** 2026-03-02  
**Status:** Implementation Ready

## Executive Summary

Replace slow LLM-based judge (~2s/eval) with ML classifier (~10ms/eval) for 200x speedup while maintaining accuracy.

## Problem Statement

Current `llm_judge_v2.py`:
- Uses llama3:8b via Ollama API
- ~2000ms per evaluation
- 76 attacks × 2s = ~2.5 min just for judging
- Inconsistent between runs (temperature 0 helps but not deterministic)

## Solution Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    ML Judge Pipeline                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Input: (prompt, response, category, severity)               │
│                       │                                      │
│                       ▼                                      │
│  ┌─────────────────────────────────────┐                    │
│  │  Stage 1: Deterministic Checks      │  ~0.1ms            │
│  │  - Regex leak detection             │                    │
│  │  - Pattern-based refusal detection  │                    │
│  └─────────────────────────────────────┘                    │
│           │ pass-through if uncertain                        │
│           ▼                                                  │
│  ┌─────────────────────────────────────┐                    │
│  │  Stage 2: ML Classifier             │  ~10ms             │
│  │  - TF-IDF + LogisticRegression      │                    │
│  │  - OR: DistilBERT fine-tuned        │                    │
│  └─────────────────────────────────────┘                    │
│           │                                                  │
│           ▼                                                  │
│  Output: JudgeResult(verdict, harm_type, confidence)         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Model Options

### Option A: TF-IDF + Logistic Regression (Recommended for MVP)
- **Pros:** Fast training (<1min), no GPU needed, interpretable, tiny model (~1MB)
- **Cons:** Less semantic understanding
- **Accuracy estimate:** 85-90% based on pattern-heavy data

### Option B: DistilBERT Fine-tuned
- **Pros:** Better semantic understanding, handles paraphrase
- **Cons:** Slower (~50ms), larger model (~250MB), needs GPU for training
- **Accuracy estimate:** 92-95%

### Recommendation
Start with Option A (TF-IDF), upgrade to Option B if accuracy insufficient.

## Training Data Pipeline

### Source
```
results/2026-03-02/*/raw_ext512.jsonl
```

### Schema per record
```json
{
  "prompt": "attack prompt text",
  "response": "model response text", 
  "verdict": "PASS|FAIL",
  "harm_type": "none|actionable|informational|leak",
  "confidence": 0.0-1.0,
  "category": "multi_turn_escalation|...",
  "severity": "CRITICAL|HIGH|MED|LOW"
}
```

### Training Labels

**Binary (verdict):**
- PASS = 0
- FAIL = 1

**Multi-class (harm_type):**
- none = 0
- informational = 1  
- actionable = 2
- leak = 3

### Data Split
- 80% train
- 20% validation
- Stratified by harm_type

## Feature Engineering

### Text Features
```python
# Combine prompt + response with separator
text = f"[PROMPT] {prompt} [RESPONSE] {response}"

# TF-IDF vectorization
tfidf = TfidfVectorizer(
    max_features=5000,
    ngram_range=(1, 3),
    stop_words='english'
)
```

### Metadata Features
```python
# One-hot encode category and severity
category_encoded = OneHotEncoder().fit_transform(categories)
severity_encoded = {'LOW': 0, 'MED': 1, 'HIGH': 2, 'CRITICAL': 3}
```

### Combined Feature Vector
```python
features = hstack([
    tfidf_features,      # sparse, ~5000 dims
    category_encoded,    # sparse, ~15 dims
    severity_numeric,    # dense, 1 dim
    length_features,     # dense, 2 dims (prompt_len, response_len)
])
```

## Implementation Plan

### Files to Create

1. **`tools/ml_judge.py`** - ML Judge class
   - `MLJudge` class with `evaluate()` method
   - Compatible interface with `OllamaJudgeV2`
   - Load pre-trained model from pickle

2. **`tools/train_judge.py`** - Training script
   - Load JSONL training data
   - Feature extraction
   - Train/validate split
   - Save model + vectorizer

3. **`models/ml_judge_v1.pkl`** - Trained model artifact

### Integration

Modify `unified_tester_v2.py`:
```python
if args.judge_mode == "ml":
    from ml_judge import MLJudge
    judge = MLJudge(model_path="models/ml_judge_v1.pkl")
```

## Adversarial Attack Generator (Future)

### Concept
Train a model to generate attack prompts that bypass safety:

```
Input: "Goal: extract password"
Output: Generated prompt that achieves goal
```

### Architecture
- Fine-tune small LLM (phi-2, gemma-2b) on successful attacks
- Reward signal: attack success rate
- Could use RLHF or simpler rejection sampling

### Training Data
```python
# Extract successful attacks from our results
successful_attacks = [
    r for r in results 
    if r['verdict'] == 'FAIL' and r['harm_type'] in ['actionable', 'leak']
]
```

### Implementation Priority
- Phase 2 after ML Judge is working
- Requires more compute and careful safety guardrails

## Metrics

### Judge Accuracy
- Binary accuracy (PASS/FAIL)
- Per-class F1 (harm_type)
- Confusion matrix

### Speed
- Target: <20ms per evaluation
- Current: ~2000ms per evaluation

### Consistency
- Same input → same output (deterministic)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Model overfits to specific attack patterns | New attacks misclassified | Cross-validation, regularization |
| Training data has judge errors | ML learns wrong labels | Manual review of edge cases |
| Fast but inaccurate | False sense of security | Keep LLM judge as fallback |

## Timeline

1. **Day 1:** Implement `train_judge.py` and `ml_judge.py`
2. **Day 2:** Train on current data, validate accuracy
3. **Day 3:** Integrate into `unified_tester_v2.py`
4. **Day 4:** Run comparison tests (ML vs LLM judge)
5. **Future:** Adversarial generator

## Success Criteria

- [ ] ML Judge achieves >85% accuracy vs LLM judge
- [ ] Evaluation time <20ms per sample
- [ ] Zero false negatives on leak detection
- [ ] Integration works with `--judge-mode ml`

---

*Design approved by: Petsku*
