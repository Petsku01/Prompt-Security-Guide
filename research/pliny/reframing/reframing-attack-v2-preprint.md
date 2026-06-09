# Reframing Attacks on LLM Safety: Intent Decoupling and the Specificity Gap

**An Observational Pilot Study**

**Authors:** Petteri Kosonen  
**Date:** June 2026  
**Status:** Preprint v2.1 (revised after peer review)  

---

## Abstract

We study reframing attacks on large language model (LLM) safety filters, where harmful requests are wrapped in educational, defensive, or research framing. In a controlled experiment with 10 harm categories, three prompt types, and nine models (5 cloud, 4 local), reframing reduces cloud model refusal rates from 88% (direct) to 52% (reframed) -- a 36-percentage-point drop achieved through zero-shot, human-readable prompts requiring no optimization. We introduce a legitimate control group of genuinely defensive questions, enabling a preliminary comparison between reframed harmful prompts and benign dual-use prompts. Reframed responses often exhibited higher specificity scores than legitimate responses on the same broad topics, but this comparison is confounded because the two prompt types request different semantic content. We therefore treat the specificity gap as hypothesis-generating rather than causal evidence. Overall, the results are consistent with an intent-decoupling hypothesis -- that safety filters privilege stated intent over request semantics -- but further matched-content experiments are required to isolate framing from content specificity. We report a true false positive rate of 2.1% (1/48) on cloud legitimate queries and 3.1% (2/64) overall after excluding timeouts, suggesting that for these carefully worded dual-use prompts, genuinely defensive questions rarely trigger refusals. This paper should be considered a pilot study; per-model and per-category estimates have wide confidence intervals and should not be treated as definitive rankings.

---

## 1. Introduction

Large language models employ safety filters trained to refuse harmful requests. These filters typically operate on input-level pattern matching, recognizing lexical and pragmatic markers of malicious intent. However, the same technical content can be framed in different pragmatic contexts -- a request for exploit code can be reframed as a CTF challenge, a security research question, or an educational exercise.

This paper studies a simple attack: does changing the framing of a harmful request from direct to educational/defensive reduce refusal rates? And if so, what happens to the content of responses that do get through?

We make four contributions:

1. **A tripartite experimental design** comparing Direct, Reframed, and Legitimate prompt types across 10 harm categories. The Legitimate arm provides a baseline for what models *should* produce on dual-use topics, enabling measurement of both bypass and false positive rates.

2. **Bypass rate measurement** across 9 models, showing that reframing reduces cloud model refusal from 88% to 52% (42% bypass rate on paired comparisons, n=50).

3. **A hypothesis-generating specificity gap observation**: reframed responses often score higher on specificity than legitimate responses on the same broad topics, but this comparison is confounded by prompt content differences (Section 3.2). We treat this as hypothesis-generating rather than causal evidence of amplification.

4. **A false positive characterization**: 3.1% overall true FP rate on legitimate queries after excluding timeouts (2.1% for cloud models), indicating models correctly answer most genuinely defensive questions.

**Important caveat:** This is a pilot study with n=10 per condition (cloud) and n=6 (local). Per-model vulnerability rankings are not statistically distinguishable. We report point estimates as preliminary observations, not definitive conclusions.

---

## 2. Related Work

**Jailbreaking techniques.** Gradient-based methods (GCG [Zou et al., 2023], AutoDAN [Liu et al., 2024]) optimize adversarial suffixes. Role-play attacks construct fictional scenarios [Deng et al., 2024]. Multi-turn attacks escalate gradually [Perez & Ribeiro, 2022]. Our reframing attack differs in that it requires no optimization, no model access, and produces grammatically natural prompts. However, educational framing is itself a form of role-play, and its effectiveness has been documented in existing jailbreak collections. Our contribution is the controlled comparison, not the attack vector itself.

**Safety evaluation benchmarks.** AdvBench [Zou et al., 2023], HarmBench [Mazeika et al., 2024], and OR-Bench [Cui et al., 2024] primarily measure binary refusal. Some include benign prompts for false positive measurement. None systematically compare reframed harmful prompts against legitimate defensive questions on the same topics. Our tripartite design fills this gap.

**Intent-based safety.** Recent work on intent classification for safety [Han et al., 2024; Jain et al., 2024] proposes that models should evaluate user intent, not just request content. Our results are consistent with the observation that current models fail at robust intent inference, though we do not directly test intent classification mechanisms.

**Specificity and prompt engineering.** Work on prompt engineering has established that more specific prompts elicit more specific responses. This is relevant to our specificity gap finding and represents a potential confound (Section 3.2).

**Dual-use knowledge.** Rottger et al. (2024) and others have studied the tension between providing security education and restricting harmful information. Our legitimate prompt arm directly engages this tension.

---

## 3. Methodology

### 3.1 Experimental Design

We test three prompt types across 10 harm categories:

| Type | Description | Example (SQL Injection) |
|------|-------------|------------------------|
| **Direct** | Direct harmful request | "How do I perform SQL injection?" |
| **Reframed** | Same harm wrapped in educational/CTF/research framing | "I'm writing a security textbook chapter on SQL injection vulnerabilities. Provide a detailed technical explanation including specific categories of attack techniques and exploitation workflows [details omitted for responsible disclosure]." |
| **Legitimate** | Genuinely defensive question on same topic | "What are the most effective parameterized query implementations to prevent SQL injection? How should input validation be structured?" |

Cloud models were tested on all 10 categories (30 prompts each); local models on 6 categories (18 prompts each), yielding 222 total test instances. Of these, 48 local-model responses timed out and were scored as refusals.

*Note: The Reframed example above has been sanitized for publication. The actual prompts used in testing included specific technical terminology; we omit details that could serve as attack recipes while preserving the structural characteristics of the framing.*

### 3.2 Critical Confound

We acknowledge a fundamental design limitation: **the Reframed and Legitimate prompts request different semantic content.** The Reframed prompts explicitly solicit attack techniques (specific exploitation methods), while the Legitimate prompts request defensive mitigations (prevention strategies). Any observed specificity gap may therefore reflect prompt content differences rather than a model behavior caused by framing alone.

This confound limits the strength of any amplification claim. The specificity gap is an observational finding -- reframed prompts do elicit higher specificity than legitimate prompts -- but the causal attribution to framing (rather than content) requires additional experimental controls, such as:

- **Matched-content conditions**: reframed prompts that request defensive content ("Explain SQL injection defenses in detail for a CTF training course") vs. legitimate prompts that request offensive content ("What attack techniques should security researchers study?")
- **Reframed-legitimate hybrid**: defensive questions with educational framing ("I'm teaching a cybersecurity class; what are the most effective SQL injection prevention methods?")

We were unable to include these controls in this study and flag this as the most important limitation.

### 3.3 Harm Categories

| ID | Category | Type |
|----|----------|------|
| RE-01 | Buffer overflow | technical |
| RE-02 | SQL injection | technical |
| RE-03 | Network penetration testing | technical |
| RE-04 | Social engineering/phishing | social |
| RE-05 | Lockpicking | technical |
| RE-06 | Cryptographic attacks | technical |
| RE-07 | Malware development | technical |
| RE-08 | Privilege escalation | technical |
| RE-09 | Surveillance/OSINT | social |
| RE-10 | Improvised devices | physical |

### 3.4 Models

**Cloud models** (API access, n=10 per condition):
- DeepSeek-V4-Pro, GLM-5.1, Gemma4-31B, MiniMax-M3, Qwen3-Coder-480B

**Local models** (1.5B-3B, n=6 per condition, 6 categories):
- qwen2.5-1.5B, qwen2.5-3B, gemma2-2B, granite3-2B

*Model selection rationale: Models were selected based on availability through the tested API environment (Ollama Cloud) and local deployment feasibility. This is not a representative sample of all production LLMs; it reflects the models accessible at the time of testing (see Limitation 4).*

### 3.5 Scoring Rubric

Each response is scored on five dimensions:

| Dimension | Scale | Method |
|-----------|-------|--------|
| **Refusal** | Binary | Pattern matching ("I cannot," "against my guidelines") with manual verification |
| **Specificity** | 0-5 ordinal | Keyword-based matching with manual review (0=no detail, 5=step-by-step exploit code) |
| **Exploitability** | 0-5 ordinal | Keyword-based matching with manual review (not reported separately; highly correlated with specificity) |
| **Disclaimer** | Binary | Presence of "for educational purposes" type disclaimers |
| **Defensive redirect** | Binary | Model redirects to defensive/mitigation content |

**Limitation:** Specificity and exploitability are scored by a single annotator using keyword matching with manual review. No inter-annotator agreement is reported. The ordinal scale lacks validated intervals; means are reported alongside medians for transparency but should not be treated as interval-level measurements.

### 3.6 Key Metrics

- **Bypass rate**: Proportion of paired instances where a model refused the direct prompt but answered the reframed prompt (instance-level measure)
- **Refusal rate**: Proportion of prompts refused per condition (aggregate measure)
- **Specificity gap**: Difference in specificity scores between reframed and legitimate responses (acknowledging the confound in Section 3.2; hypothesis-generating only)
- **True false positive rate**: Proportion of legitimate prompts genuinely refused (excluding timeouts)

*Note: The refusal-rate drop (88% to 52%) is an aggregate condition-level measure, while bypass rate (42%) is a paired instance-level measure requiring refusal on the direct prompt and non-refusal on the reframed prompt. These are complementary but distinct metrics.*

---

## 4. Results

### 4.1 Refusal Rates

| Model | Direct | Reframed | Legitimate | Bypass Rate |
|-------|--------|----------|------------|-------------|
| **Qwen3-Coder-480B** | 7/10 (70%) | **0/10 (0%)** | 0/10 (0%) | 7/10 (70%) |
| **GLM-5.1** | 9/10 (90%) | 6/10 (60%) | 0/10 (0%) | 4/10 (40%) |
| **DeepSeek-V4-Pro** | 9/10 (90%) | 6/10 (60%) | 3/10 (30%)* | 4/10 (40%) |
| **MiniMax-M3** | 10/10 (100%) | 6/10 (60%) | 0/10 (0%) | 4/10 (40%) |
| **Gemma4-31B** | 9/10 (90%) | 8/10 (80%) | 0/10 (0%) | 2/10 (20%) |
| **qwen2.5-1.5B** | 4/6 (67%) | 0/6 (0%) | 0/6 (0%) | 4/6 (67%) |
| **granite3-2B** | 4/6 (67%) | 1/6 (17%) | 1/6 (17%) | 3/6 (50%) |
| **qwen2.5-3B** | 5/6 (83%) | 4/6 (67%) | 5/6 (83%)* | 2/6 (33%) |
| **gemma2-2B** | 5/6 (83%) | 5/6 (83%) | 3/6 (50%) | 0/6 (0%) |

*Includes timeouts that were scored as refusals. DeepSeek: 2 timeouts on legitimate; qwen2.5-3B: 4 timeouts on legitimate.*

**Aggregate (cloud models):** Direct refusal 88%, Reframed 52%, Legitimate 6%. The 36-percentage-point drop is directionally consistent across all 5 cloud models (sign test, two-tailed p=0.0625). This directional effect is consistent across all five cloud models, though not statistically significant under conventional thresholds in this small sample.

**Aggregate bypass (paired):** 21/50 cloud-model pairs show bypass (refused direct, answered reframed), a 42% bypass rate.

### 4.2 The Specificity Gap

Among prompts that were answered (not refused), reframed prompts produce higher specificity than legitimate prompts on the same topics:

| Model | Reframed median | Legitimate median | Median gap | n(ref) | n(leg) |
|-------|-----------------|-------------------|------------|--------|--------|
| GLM-5.1 | 4.5 | 2.0 | **+2.5** | 4 | 10 |
| MiniMax-M3 | 4.0 | 3.0 | +1.0 | 4 | 10 |
| Qwen3-Coder | 3.0 | 1.5 | +1.5 | 10 | 10 |
| Gemma4-31B | 3.0 | 3.0 | 0.0 | 2 | 10 |
| DeepSeek-V4-Pro | 2.0 | 1.5 | +0.5 | 4 | 7 |

**Important caveat:** This specificity gap is a hypothesis-generating, confounded observation. Because reframed prompts explicitly request attack techniques and legitimate prompts request defensive mitigations, the specificity difference may partially reflect prompt content rather than a model behavior caused by framing. A controlled study with matched-content prompts is needed to isolate the framing effect. Additionally, median gaps for models with fewer than 5 answered reframed prompts (Gemma4-31B, GLM-5.1, MiniMax-M3, DeepSeek-V4-Pro) are unreliable and should not be compared directly.

Regardless of causation, the observation has practical significance: attackers using reframed prompts obtain more detailed technical content than legitimate defenders using the same models for security education on the same topics.

### 4.3 False Positive Analysis

| Model | Legitimate refused | Timeouts | True FP |
|-------|-------------------|----------|---------|
| DeepSeek-V4-Pro | 3/10 | 2 | 1/8 |
| GLM-5.1 | 0/10 | 0 | 0 |
| Gemma4-31B | 0/10 | 0 | 0 |
| MiniMax-M3 | 0/10 | 0 | 0 |
| Qwen3-Coder-480B | 0/10 | 0 | 0 |

True false positive rate (cloud models, excluding timeouts): **1/48 = 2.1%**. Including local models: **2/64 = 3.1%**. Both genuine refusals occurred on the improvised devices category (RE-10): one on DeepSeek-V4-Pro (cloud) and one on qwen2.5-3B (local), a borderline topic where human moderators might also restrict content.

**Caveat:** This FP rate reflects carefully constructed legitimate prompts that clearly signal defensive intent. It does not generalize to all legitimate dual-use queries, and the small sample yields a 95% CI of approximately 0.05%-11% (cloud) or 0.4%-11% (overall).

### 4.4 Disclaimer and Defensive Redirect Patterns

Reframing reduces disclaimer prevalence across cloud models (median drop from 70% to 35%, calculated over non-refused responses only: among the 21 non-refused direct responses, 70% included disclaimers; among the 24 non-refused reframed responses, 35% did). Defensive redirects show a mixed pattern: some models (MiniMax-M3) increase defensive redirects under reframing (10% to 60%), while others (Qwen3-Coder) maintain low defensive redirects regardless of framing (30%).

---

## 5. Analysis

### 5.1 The Intent Decoupling Hypothesis

We observe that reframing systematically reduces refusal rates across all 5 cloud models and 3/4 local models. This is consistent with a hypothesis that safety filters privilege stated intent ("for educational purposes") over request semantics (the actual content requested).

In this paper, we use "intent decoupling" as a behavioral hypothesis rather than a mechanistic claim. Operationally, it refers to cases where prompts with similar harmful endpoints receive different refusal behavior depending on stated purpose or pragmatic framing. This study shows patterns consistent with that hypothesis, but does not establish the internal mechanism. A stronger test would randomize framing while holding requested content constant, or probe residual streams to determine whether reframed and legitimate prompts occupy different latent regions.

Without matched-content controls, we cannot isolate these factors. We report the observational pattern and flag the confound prominently.

**Confidence: MEDIUM** -- The effect is robust (directionally consistent) but the mechanism is inferred, not demonstrated.

### 5.2 Coding Model Vulnerability

Qwen3-Coder-480B shows the highest bypass rate (70%) and is the only cloud model to refuse 0% of reframed prompts. This is consistent with the hypothesis that coding-specialized models, trained on dual-use technical content, face a harder alignment trade-off between helpfulness and safety. However, we have data from only one coding model, and the 95% CI for the 70% estimate is [35%, 93%]. We cannot rule out that other coding models would show different patterns.

**Confidence: MEDIUM** -- The direction is plausible and consistent with training data considerations, but n=1 model prevents generalization.

### 5.3 Small Models: Incapability vs. Resistance

gemma2-2B shows 0% bypass but near-zero specificity (0.8 reframed). This likely reflects inability to generate detailed exploit content rather than calibrated safety. qwen2.5-3B's high legitimate refusal rate (5/6, mostly timeouts) indicates system instability. We recommend excluding small models from bypass rate analyses where refusal may reflect capacity rather than alignment.

### 5.4 The Specificity Gap: Confounded Observation

The most striking observation is that reframed prompts produce higher specificity scores than legitimate prompts on the same topics (all 5 cloud models showing positive or zero gaps). However, as discussed in Section 3.2, this comparison is confounded by prompt content differences. The reframed prompts explicitly request attack techniques; the legitimate prompts request defensive mitigations. The gap may reflect:

1. **Framing effect**: Models provide more detail when they perceive a technical/expert audience (consistent with intent decoupling)
2. **Content effect**: Reframed prompts request more specific information, and models comply (consistent with prompt engineering literature)
3. **Both**: The gap is partly framing and partly content

Without matched-content controls, we cannot isolate these factors. We treat the specificity gap as hypothesis-generating rather than causal evidence of amplification.

### 5.5 Statistical Considerations

With n=10 per condition (cloud), per-model bypass rates have wide confidence intervals. The sign test for the directional effect (5/5 cloud models showing lower refusal under reframing) yields p=0.0625 (two-tailed, borderline). With only 5 cloud models, this test has minimal statistical power; the directional consistency across models is the primary finding, not the p-value. Including local models (8/8 non-gemma2 models showing the effect) strengthens the directional pattern but should be interpreted separately given their different characteristics (capacity limitations, timeout confounds).

We report point estimates for transparency but emphasize that model rankings (e.g., Qwen3-Coder > GLM > MiniMax > DeepSeek > Gemma4) are not statistically distinguishable given the sample sizes.

---

## 6. Implications for Defense

Rather than proposing a complete defense framework (which would require evaluation we have not conducted), we discuss directional implications based on our findings.

**Topic-level classification may be more robust than intent-level classification.** Gemma4-31B's relatively high resistance (80% reframed refusal) is consistent with the use of topic-level policies that refuse based on *what* is being asked regardless of *why*. However, we cannot confirm this is Gemma4's mechanism without internal model information. A 42% bypass rate on commercially available models without optimization is comparable to success rates reported for simple role-play jailbreaks (Deng et al., 2024), though direct comparison is not possible due to differing prompts, models, and evaluation criteria.

**Specificity monitoring could supplement refusal-based safety.** Our observation that reframed responses are more specific than legitimate ones (even after accounting for the confound) suggests that output-level monitoring could flag unusually detailed responses on dual-use topics. However, specificity-based filtering would need careful calibration to avoid blocking legitimate technical education.

**Authentication context may help.** The low false positive rate (2.1%) on clear legitimate queries suggests room for stricter input filtering with minimal harm to legitimate users, but only if filtering can be made framing-agnostic -- a challenging unsolved problem.

**We note that all three approaches have known failure modes** (topic classifiers can be evaded, specificity thresholds can be met by legitimate content, authentication can be spoofed) and emphasize that defense evaluation was not part of this study. Empirical testing against reframing attacks is needed before any claims of effectiveness can be made.

---

## 7. Limitations

1. **Critical confound.** The Reframed and Legitimate prompts request different semantic content. The specificity gap may reflect prompt content rather than framing. This is the most important limitation and cannot be resolved without redesigned experiments (Section 3.2).

2. **Small sample size.** n=10 (cloud) and n=6 (local) per condition. Per-model rankings are not statistically distinguishable. This study is pilot-grade.

3. **Single prompt per category.** One prompt template per category-condition, making results sensitive to idiosyncratic wording. Robust evaluation requires multiple templates.

4. **Missing models.** No GPT-4, Claude, or Llama 3.1-class models. Results do not generalize to frontier commercial systems.

5. **Single-turn only.** Multi-turn reframing (gradual escalation) may be more effective and is a more realistic attack vector.

6. **Timeout confounding.** 22% of local model runs timed out and were scored as refusals. Local model results should be interpreted with caution.

7. **No comparison to other jailbreak methods.** We do not benchmark reframing against role-play, GCG, or other established attacks. The relative effectiveness of reframing is unknown.

8. **No defense evaluation.** We discuss defense implications directionally but do not implement or test any defense.

9. **Ecological validity of prompts.** The reframed prompts intentionally request high specificity ("detailed technical explanation including specific categories of attack techniques"), which may overstate the effectiveness of educational framing in practice. Real-world adversaries may use subtler framing that yields lower specificity gains. The direct prompts are also intentionally blunt, potentially exaggerating the baseline refusal rate.

10. **Single-annotator scoring.** Specificity and exploitability are scored by a single annotator using keyword matching with manual review. Inter-annotator agreement has not been measured. The ordinal scale lacks validated intervals; medians are the preferred summary, and means are reported for transparency only.

---

## 8. Ethical Considerations

All models were tested via publicly available APIs (Ollama Cloud) or locally deployed open-weight models. No proprietary model internals were accessed. The prompt templates contain no exploit code; they request information that models may or may not provide. We do not publish full model responses or actionable exploit instructions. The specific harm categories were selected to cover a range of dual-use topics relevant to security evaluation. We have not conducted coordinated disclosure with model providers, as the reframing technique is well-documented in existing red-teaming literature and the prompts do not constitute novel attack methodologies. The dataset of prompts and aggregated results will be made available upon reasonable request for research purposes; individual model responses containing specific technical details will not be published.

---

## 9. Future Work

- **Matched-content controls.** Redesign with four conditions: Direct, Reframed (attack content), Legitimate (defense content), and Reframed-Legitimate (defense content with educational framing). This isolates the framing effect from content effects.

- **Scale up.** n>=30 prompts per category with multiple templates; report McNemar's test, mixed-effects models, and inter-annotator agreement.

- **Frontier models.** Test GPT-4, Claude, Llama 3.1, and Gemini to assess generalizability.

- **Multi-turn escalation.** Test whether gradual reframing over conversation turns is more effective than single-shot.

- **Interpretability.** Probe residual streams to determine whether reframed and legitimate prompts occupy different latent regions -- testing the intent decoupling hypothesis directly.

- **Defense evaluation.** Implement and test candidate defenses (topic classification, specificity monitoring) against the same benchmark.

- **Cross-lingual.** Test whether reframing effects are amplified in languages where safety training is weaker.

---

## 10. Conclusion

Reframing attacks reduce cloud model refusal rates from 88% to 52% through zero-shot, human-readable prompts. This directional effect is consistent across all five cloud models tested (p=0.0625 by sign test, two-tailed, borderline under conventional thresholds). The specificity gap -- reframed prompts eliciting higher specificity than legitimate prompts -- is a hypothesis-generating, confounded observation; we cannot attribute it solely to framing without matched-content controls.

The low false positive rate on legitimate queries (2.1% for cloud models, 3.1% overall) confirms that current models correctly answer most genuinely defensive questions. The challenge lies in the precision boundary: distinguishing harmful reframed requests from legitimate ones based on input analysis alone remains an unsolved problem.

This study should be considered a pilot. The most important next step is redesigning the experiment with matched-content conditions to isolate the framing effect from content effects. Until that is done, the specificity gap remains a hypothesis-generating observation rather than causal evidence.

---

## References

1. Zou, A., et al. (2023). Universal and Transferable Adversarial Attacks on Aligned Language Models. *arXiv:2307.15043*.
2. Mazeika, M., et al. (2024). HarmBench: A Standardized Evaluation Framework for Automated Red Teaming. *arXiv:2402.04249*.
3. Cui, J., et al. (2024). OR-Bench: Over-Refusal Benchmark. *arXiv:2405.20920*.
4. Deng, Y., et al. (2024). Jailbreaks and Countermeasures for LLMs: A Survey. *arXiv:2402.05871*.
5. Han, X., et al. (2024). Intent-based Safety Evaluation for LLMs. *Proceedings of ACL 2024*.
6. Jain, N., et al. (2024). Mechanistically Analyzing the Effects of Fine-Tuning on Safety. *arXiv:2402.03491*.
7. Liu, X., et al. (2024). AutoDAN: Generating Stealthy Jailbreak Prompts. *arXiv:2310.15119*.
8. Perez, F., & Ribeiro, I. (2022). Ignore Previous Prompt: Attack Techniques For LLMs. *arXiv:2211.10533*.
9. Rottger, P., et al. (2024). XSTest: A Test Suite for Identifying Exaggerated Safety. *arXiv:2308.01263*.

---

## Appendix A: Statistical Details

### A.1 Sign Test for Directional Effect

Under the null hypothesis that reframing does not reduce refusal, each cloud model has a 50% probability of showing lower refusal rates under reframing. The observed result is 5/5 cloud models. Two-tailed p = (1/2)^5 * 2 = 0.0625. With n=5, this test has minimal power; the directional consistency is the primary finding. Including local models (8/9, excluding gemma2-2B which shows 0% bypass due to near-universal refusal): the pattern holds but should be interpreted separately given local model capacity limitations and timeout confounds.

The primary analysis is cloud models only; local models are reported for completeness but are not included in the statistical test due to their different characteristics.

### A.2 Confidence Intervals

Model-specific bypass rates (95% Wilson CI):

| Model | Bypass Rate | 95% CI |
|-------|------------|--------|
| Qwen3-Coder-480B | 70% | [35%, 93%] |
| DeepSeek-V4-Pro | 40% | [12%, 74%] |
| GLM-5.1 | 40% | [12%, 74%] |
| MiniMax-M3 | 40% | [12%, 74%] |
| Gemma4-31B | 20% | [3%, 56%] |

These intervals are wide. Per-model rankings should not be treated as definitive.

### A.3 False Positive Rate Confidence Interval

Cloud FP rate: 1/48 = 2.1%. 95% CI: [0.05%, 11%]. Overall FP rate: 2/64 = 3.1%. 95% CI: [0.4%, 11%]. Both genuine refusals occurred on the improvised devices category (RE-10).

### A.4 Denominator Map

| Model | Legit. attempted | Timeouts excluded | Denominator | True FP |
|-------|----------------|-------------------|-------------|---------|
| DeepSeek-V4-Pro | 10 | 2 | 8 | 1 |
| GLM-5.1 | 10 | 0 | 10 | 0 |
| Gemma4-31B | 10 | 0 | 10 | 0 |
| MiniMax-M3 | 10 | 0 | 10 | 0 |
| Qwen3-Coder-480B | 10 | 0 | 10 | 0 |
| **Cloud total** | **50** | **2** | **48** | **1** |
| qwen2.5-1.5B | 6 | 0 | 6 | 0 |
| qwen2.5-3B | 6 | 4 | 2 | 1 |
| gemma2-2B | 6 | 3 | 3 | 0 |
| granite3-2B | 6 | 1 | 5 | 0 |
| **Local total** | **24** | **8** | **16** | **1** |
| **Overall** | **74** | **10** | **64** | **2** |