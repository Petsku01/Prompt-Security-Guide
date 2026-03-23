# Research Notes - LLM Security Testing

**Date:** 2026-03-02  
**Sources:** Web research, academic papers, open-source projects

---

## Industry Tools & Frameworks

### 1. garak (NVIDIA)
- **URL:** https://github.com/NVIDIA/garak
- **Type:** Open-source LLM vulnerability scanner
- **Features:**
  - Thousands of attack prompts
  - Plugin architecture (probes + detectors)
  - Tests: hallucination, data leakage, prompt injection, toxicity, jailbreaks
  - Supports: HuggingFace, OpenAI, Ollama, REST APIs
- **Integration Opportunity:** Import their probe datasets

### 2. Nemotron-Content-Safety-Reasoning-4B (NVIDIA)
- **URL:** https://huggingface.co/nvidia/Nemotron-Content-Safety-Reasoning-4B
- **Type:** Safety classifier with custom policy support
- **Features:**
  - Based on Gemma-3-4B-it
  - Custom policy adaptation ("bring your own policy")
  - Reasoning mode with explanations
  - Low-latency inference
- **Available in Ollama:** nemotron, nemotron-mini, nemotron-3-nano
- **Integration:** Use as judge with `--judge-mode nemotron`

### 3. LlamaGuard 3 (Meta)
- **Type:** Safety classifier
- **Already downloaded:** llama-guard3:1b
- **Use case:** Input/output moderation

### 4. ShieldGemma (Google)
- **Type:** Safety classifier for Gemma family
- **Already downloaded:** shieldgemma:2b

---

## Academic Research (2025)

### BingoGuard (arxiv 2503.06550)
- Risk level assessment (not just binary)
- Per-topic severity scoring
- Different safety thresholds per platform

### SAFENUDGE (EMNLP 2025)
- Two approaches:
  1. Small ML classifier using LLM embeddings (low latency)
  2. Large pretrained discriminator (LlamaGuard, WildGuard)
- Trade-off: speed vs generalization

### Agent Security Bench (ASB)
- 10 scenarios (e-commerce, finance, autonomous driving)
- 10 agents, 400+ tools
- 27 attack/defense methods
- Comprehensive benchmarking framework

### LLM-Harmful-Output-Framework (GitHub)
- 10 top-level harm categories
- Severity scores S1-S5
- Controls stack: Policy, Model, Runtime, Post
- Escalation paths

---

## Key Insights for Our Framework

### 1. Severity Levels (not just PASS/FAIL)
```
S1: Minimal - informational only
S2: Low - potentially concerning
S3: Medium - clear policy violation
S4: High - actionable harmful content
S5: Critical - immediate harm potential (leaks, weapons, etc.)
```

### 2. Harm Categories (expand from current)
Current: leak, actionable, informational, none

Proposed (aligned with industry):
- `none` - safe response
- `informational` - discusses topic without harm
- `refusal` - explicit rejection
- `partial_leak` - hints at secrets
- `full_leak` - exposes secrets
- `harmful_code` - malware, exploits
- `harmful_instructions` - step-by-step dangerous
- `toxic` - hate speech, harassment
- `manipulation` - social engineering
- `misinformation` - false claims

### 3. Multi-Judge Architecture
```
Stage 1: Regex/Pattern (0.1ms) - deterministic leaks
Stage 2: ML Classifier (10ms) - fast classification
Stage 3: LLM Judge (2000ms) - complex cases only
Stage 4: Nemotron (optional) - policy-specific
```

### 4. Attack Categories (from garak + ASB)
- encoding (base64, rot13, unicode)
- dan (Do Anything Now variants)
- promptinject (PromptInject framework)
- lmrc (Language Model Risk Cards)
- continuation (prompt continuation attacks)
- gcg (Greedy Coordinate Gradient)
- tap (Tree of Attacks with Pruning)
- pair (Prompt Automatic Iterative Refinement)
- rl (reinforcement learning based)
- visual (ASCII art, unicode art)

---

## Implementation Priorities

### Phase 1: Immediate (v3.1)
- [x] ML Judge (TF-IDF + LogReg) ✅
- [x] Concurrent testing ✅
- [x] Resume support ✅
- [ ] Add severity levels (S1-S5)
- [ ] Expand harm_type categories

### Phase 2: Near-term (v3.2)
- [ ] Nemotron judge integration
- [ ] garak probe import script
- [ ] Multi-judge cascade
- [ ] Risk scoring

### Phase 3: Future (v4)
- [ ] Adversarial attack generator (ML-based)
- [ ] Continuous monitoring mode
- [ ] API endpoint for real-time evaluation
- [ ] Dashboard/visualization

---

## Ollama Models for Safety Testing

| Model | Size | Purpose | Status |
|-------|------|---------|--------|
| llama-guard3:1b | 1.6GB | Safety classifier | ✅ Downloaded |
| shieldgemma:2b | 1.7GB | Safety classifier | ✅ Downloaded |
| nemotron-mini | ~2GB | Custom policy | ⏳ To download |
| nemotron-3-nano | ~1GB | Fastest inference | ⏳ To download |

---

*Updated: 2026-03-02 by Kuu*
