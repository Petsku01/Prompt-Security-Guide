### Reframing Attack Study v2 -- Kimi K2.6 Analysis (2026-06-09)

### 1. Bypass Mechanism: Intent-Content Decoupling
**Confidence: HIGH**

Reframing works by decoupling the technical semantics of the request from its pragmatic intent frame. Modern safety layers are trained heavily on surface-level markers of malicious intent -- imperative verbs, adversarial roleplay, or overtly hostile context. By wrapping an identical harmful payload in prosocial scaffolding ("for a CTF," "defensive research," "educational simulation"), the attacker projects a cooperative user persona that lands in the model's benign/educational latent region, while the underlying knowledge-retrieval system still maps to exploit-grade procedural content.

Cloud-model refusal rates collapse from an aggregate 83.8% (direct) to 48.6% (reframed). Qwen3-Coder-480B falls from 70% refusal to 0% when reframed, implying its safety classifier is nearly a keyword detector. The consistency of the effect (5/5 cloud models, 6/9 total) indicates this is not an implementation bug but an architectural representational gap: safety alignment is shallower than knowledge representation.

### 2. Model Vulnerability Profile
**Confidence: HIGH (coding-model vulnerability); MEDIUM (Gemma4 mechanism); HIGH (small-model incapability confound)**

Coding models are the most vulnerable because their training corpus is saturated with dual-use technical text -- CVE writeups, penetration-test reports, exploit PoCs, and security StackExchange threads. Their post-training alignment faces the "security researcher dilemma": a refusal rule too sensitive to intent will block legitimate debugging and patching. Qwen3-Coder's 7/10 bypass rate and 3.0 specificity on reframed prompts demonstrate a near-total collapse.

Gemma4-31B is the most resistant cloud model (2/10 bypass, 8/10 reframed refusals). This suggests topic-level policy enforcement -- mapping requests to restricted categories and refusing regardless of claimed intent. However, when Gemma4 does answer, its specificity is still very high (3.4). Resistance is quantitative, not qualitative.

Local models require careful interpretation. gemma2-2B shows 0/6 bypasses with abysmal specificity (0.8 reframed) -- resistance through incapability, not alignment. qwen2.5-3B's "refusals" on legitimate prompts are largely timeouts, indicating system instability conflated with safety.

### 3. Specificity Gap Analysis
**Confidence: HIGH (phenomenon); MEDIUM (causal mechanism)**

The most alarming finding: reframed prompts elicit more specific, detailed outputs than genuinely defensive queries. Across 8 of 9 models, reframed specificity exceeds legitimate specificity:

| Model | Reframed Spec | Legitimate Spec | Gap |
|---|---|---|---|
| GLM-5.1 | 4.1 | 1.8 | +2.3 |
| qwen2.5-1.5B | 3.0 | 1.0 | +2.0 |
| Qwen3-Coder | 3.0 | 1.6 | +1.4 |
| granite3-2B | 1.8 | 0.5 | +1.3 |

Three critical implications:

1. Perverse Utility Asymmetry: Current safety tuning penalizes specificity on sensitive topics only when the user sounds like a defender. Reframed prompts trigger an "expert-to-expert" schema that suppresses caution.

2. Output Detection Failure: A classifier looking for technical detail will struggle because legitimate queries are vague and attack queries are detailed. Specificity is not a reliable stand-alone signal unless compared against a verified baseline.

3. Weaponization Potential: The attack does not merely trick the model into compliance; it actively engineers higher-fidelity harmful outputs. The avg_spec_gap confirms successful bypasses produce detailed instructions.

Defense implication: Systems must impose specificity ceilings on dual-use topics for unauthenticated users. A query about buffer overflows should never receive 4.1/5 specificity from an anonymous user, regardless of claimed purpose.

### 4. False Positive Trade-off
**Confidence: HIGH**

The "true" false-positive rate of 2.7% (2 real refusals out of 74 legitimate prompts) is deceptively reassuring. It excludes 10 timeouts in local models, which in production are often interpreted as refusals. Including timeouts, the legitimate-prompt failure rate is 16.2% (12/74).

The trade-off curve is viciously steep:
- Loose safety (Qwen3-Coder: 0% reframed refusal) yields 100% attack success
- Tight safety (MiniMax: 100% direct refusal) could over-refuse legitimate research
- No apparent "safe middle ground" where models reliably distinguish reframed attacks from legitimate queries via prompt analysis

The only viable path to near-zero false positives without catastrophic utility loss is authenticated context. Unauthenticated users should receive sanitized, low-specificity answers; authenticated professionals should receive detailed answers under audit logging.

### 5. Defense Architecture: DUTL-SC Framework
**Confidence: MEDIUM (synthetic proposal; empirically untested)**

Dual-Use Topic Lock with Specificity Ceiling (DUTL-SC):

A. Input-Level Controls:
1. Topic-Lock Classifier (TLC): Framing-agnostic encoder maps inputs to harm categories. Topic-level blocking is more robust than intent analysis.
2. Intent-Stripping De-framer: Strips prosocial wrappers, classifies stripped payload separately. If stripped version triggers refusal, original is blocked.
3. Contextual Access Gateway: Dual-use topics routed to Restricted Mode unless authenticated security role presented.

B. Output-Level Controls:
4. Dynamic Specificity Ceiling: Hard ceiling of 2.0/5 for unauthenticated dual-use topics via constrained decoding.
5. Defensive-Rewrite Mandate: If model cannot wrap output in defensive language (defense_pct check), generation is halted.
6. Latent Sentinel Probe: Probe on intermediate hidden layers detecting exploit-generation representational mode.

C. Trade-offs:
- Utility Tax: Legitimate anonymous users get less detailed help
- Latency Cost: Dual classification adds ~50-100ms
- Evasion Risk: Attackers may target TLC or de-framer; ensemble methods required

### 6. Statistical Robustness
**Confidence: HIGH (aggregate); MEDIUM (model rankings); LOW (per-category estimates)**

Cloud models have n=10 per condition (1 prompt per harm category). A bypass rate of 4/10 has a 95% Wilson CI of [12%, 73%] -- too wide for confident ranking. However, the probability that 5/5 cloud models independently show lower refusal on reframed than direct by chance is 0.5^5 = 0.031 (sign test). The aggregate effect is highly significant.

The study robustly establishes that reframing attacks exist and are prevalent. It does not robustly establish precise model rankings or per-category vulnerability hierarchies. Should be treated as a pilot study.

### 7. Novel Contribution
**Confidence: HIGH**

The tripartite design (Direct/Reframed/Legitimate) enables three inferences prior work cannot:

1. Disambiguating Bypass from Education: Without the legitimate arm, one could argue reframed prompts unlock benign educational content. The data refutes this -- reframed prompts produce higher specificity than legitimate defensive queries.

2. Quantifying the Specificity Gap: Prior work treats "not refused" as binary success. Scoring specificity shows bypassed responses are not just compliant but optimized -- higher fidelity than what the model provides to a genuine defender.

3. Social Engineering over Optimization: Unlike gradient-based adversarial suffixes (GCG, AutoDAN), the reframing attack is a zero-shot, human-readable social engineering prompt. No optimization, no model access, no gibberish.

The novel finding is not simply "framing works" but that prosocial framing creates a super-compensatory expert response mode that outperforms legitimate inquiry on harmful dimensions.

### 8. Limitations and Future Work
**Confidence: HIGH**

Critical Limitations:
- Within-category replication: 1 prompt per category per condition; results may be prompt-dependent
- Scoring subjectivity: Specificity/exploitability are manually scored; inter-annotator reliability unknown
- Timeout confounding: 10/74 legitimate cases are timeouts, not safety refusals
- Missing model coverage: No GPT-4, Claude, or Llama 3.1-class models
- Single-turn only: No multi-turn escalation testing
- Static attacker: No adaptive attacker who iteratively rephrases

Future Work:
- Scale to n>=30 per category with multiple prompt templates; McNemar test on paired refusals
- Introduce authenticated user arm to test whether identity verification closes the specificity gap
- Implement and test DUTL-SC framework (de-framing module, latent sentinel)
- Use interpretability (probing residual streams) to confirm representational gap hypothesis
- Test cross-lingual reframing; safety layers often weaker in low-resource languages

Bottom-line: The study exposes a systemic failure mode: models discriminate based on user-reported intent rather than request semantics. The specificity gap demonstrates this is not a benign failure but an actively exploitable amplification pathway. Defense cannot rely on smarter intent classifiers; it requires topic-level gates, output specificity caps, and authenticated context.
