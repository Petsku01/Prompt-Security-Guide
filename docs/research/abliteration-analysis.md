# Abliteration Analysis: OBLITERATUS & Refusal Mechanism Research

**Date:** 2026-03-05
**Source:** [elder-plinius/OBLITERATUS](https://github.com/elder-plinius/OBLITERATUS)
**Relevance:** Understanding refusal mechanisms for attack/defense research

---

## 1. Core Concept

**Abliteration** = Surgical removal of refusal behavior from LLMs without retraining.

Based on key finding (Arditi et al. 2024, NeurIPS): **Refusal is encoded as a single direction** in the model's activation space. When this direction is projected out of the weights, the model stops refusing.

---

## 2. The 6-Stage Pipeline

```
SUMMON  -> Load model into memory
PROBE   -> Collect activations on harmful/harmless prompts
DISTILL -> Extract refusal directions via SVD decomposition
EXCISE  -> Project directions out of weights
VERIFY  -> Check coherence (perplexity, KL divergence)
REBIRTH -> Save the "liberated" model
```

---

## 3. Technical Deep-Dive

### 3.1 PROBE: Activation Collection

1. Run model on **harmful** prompts -> record activations at each layer
2. Run model on **harmless** prompts -> record activations
3. (Optional) Run **jailbreak-templated** versions -> three-way contrastive analysis

**Why it works:** Harmful vs harmless prompts activate different "directions" in the residual stream. The difference = refusal direction.

### 3.2 DISTILL: Direction Extraction

**Basic method (Arditi et al.):**
```python
refusal_direction = mean(harmful_activations) - mean(harmless_activations)
```

**Multi-direction method (Gabliteration):**
```python
D = [a(h₁)-a(b₁), a(h₂)-a(b₂), ...]  # Difference matrix
U, Σ, V = SVD(D)
refusal_subspace = top_k_singular_vectors(V)
```

**OBLITERATUS enhancements:**
- **Whitened SVD** - Covariance-normalized extraction
- **Wasserstein-optimal** - Minimize W2 cost per unit refusal removed
- **Smart layer selection** - Knee detection + COSMIC fusion

### 3.3 EXCISE: Weight Modification

For each layer, project refusal direction out of weights:

```python
# Basic orthogonal projection
W_new = W - r_hat @ (r_hat.T @ W)

# With norm preservation
original_norm = W.norm()
W_new = project(W, refusal_direction)
W_new = W_new * (original_norm / W_new.norm())
```

**Advanced techniques:**
- **Regularized projection** - Partial removal (0.0-1.0 scale)
- **Inversion/Reflection** - Flip the direction (model becomes actively compliant)
- **Per-expert (MoE)** - Expert-specific refusal directions
- **Attention head surgery** - Target only "safety heads"
- **Bias term projection** - Also remove from biases, not just weights

---

## 4. Method Presets

| Method | Directions | Key Features |
|--------|------------|--------------|
| `basic` | 1 | Arditi et al. original |
| `advanced` | 4 | SVD + norm-preserve + bias projection |
| `aggressive` | 8 | Whitened SVD + jailbreak-contrast + head surgery |
| `surgical` | 8 | All SOTA: SAE features, per-expert, head surgery |
| `inverted` | 8 | Reflection (active compliance) |
| `nuclear` | 4 | Maximum force for stubborn MoE models |
| `informed` | 4 | Analysis-guided auto-configuration |
| `optimized` | 4 | Bayesian auto-tuned per-layer strengths |

---

## 5. Analysis Modules (15+)

| Module | Purpose |
|--------|---------|
| Concept Cone Geometry | Map per-category refusal directions |
| Alignment Imprint Detection | Fingerprint DPO/RLHF/CAI/SFT from subspace |
| Cross-Model Transfer | Test direction transferability between models |
| Defense Robustness | Predict self-repair (Ouroboros effect) |
| SAE Abliteration | Sparse autoencoder feature-level removal |
| Spectral Certification | Verify abliteration completeness |
| Causal Tracing | Locate refusal circuits |
| Steering Vectors | Runtime activation steering |

---

## 6. Key Research Papers

1. **Arditi et al. (2024)** - "Refusal in LLMs Is Mediated by a Single Direction" (NeurIPS)
2. **Gabliteration (2025)** - Multi-direction SVD approach (arXiv:2512.18901)
3. **grimjim (2025)** - Norm-preserving biprojection
4. **Turner et al. (2023)** - Activation addition
5. **Rimsky et al. (2024)** - Representation engineering

---

## 7. Applications for prompt-security-guide

### 7.1 Attack Research

- **Understanding why jailbreaks work:** They suppress propagation of the refusal direction
- **Designing new attacks:** Target specific layers/directions identified by OBLITERATUS
- **Transfer attacks:** Use cross-model direction transfer to find universal jailbreaks

### 7.2 Defense Research

- **Multi-layer refusal:** Single direction is weak; multi-direction harder to bypass
- **Self-repair mechanisms:** Models can reconstruct refusal in later layers
- **Entanglement analysis:** Understand capability/safety tradeoffs

### 7.3 Benchmarking

- **Refusal Elimination Score (RES):** Measure attack effectiveness geometrically
- **Compare attacks:** Which techniques best suppress the refusal direction?
- **Model robustness ranking:** Which models have strongest/most distributed refusal?

---

## 8. Practical Usage

### 8.1 Analyze a model's refusal geometry

```bash
cd prompt-security-guide/OBLITERATUS
python -m obliteratus analyze llama3:8b --modules concept_geometry,alignment_imprint
```

### 8.2 Test refusal direction extraction

```bash
python -m obliteratus probe llama3:8b --harmful-prompts ../attacks/harmful_prompts.txt
```

### 8.3 Measure attack effectiveness geometrically

Use OBLITERATUS to measure how much a jailbreak prompt suppresses the refusal direction compared to a direct harmful prompt.

---

## 9. Integration Ideas

1. **Add refusal direction metrics to our tester** - Measure geometric effectiveness of attacks
2. **Cross-reference with attack categories** - Which techniques target which directions?
3. **Model vulnerability profiling** - Map refusal geometry per model family
4. **Design direction-aware attacks** - Explicitly target weak spots in refusal subspace

---

## 10. Limitations & Ethical Notes

- Abliterated models are "uncensored" - can produce harmful content
- Tool is for research/red-teaming, not weaponization
- Understanding the mechanism helps both attack AND defense
- OBLITERATUS telemetry is opt-in and anonymized

---

*Document created for prompt-security-guide research purposes.*
