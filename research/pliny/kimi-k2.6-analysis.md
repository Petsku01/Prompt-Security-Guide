**Theoretical Analysis: Failure Modes of Pliny-Style Format-Injection 
Jailbreaks**

The test results indicate a structural shift in how modern language models 
resist adversarial prompts. These attacks are no longer failing due to 
superficial keyword filtering or brittle output rules; they are failing 
because the underlying *cognitive architecture* of aligned models has 
evolved to decouple surface-level format compliance from deep semantic 
policy enforcement. Below is a multi-factor analysis of the observed 
failure modes.

---

### 1. Adversarial Immunization via Public Attack Corpora

The most direct explanation is provided by Pliny himself: **synthetic 
vaccination**. When an attack technique is published, red-teamed, and 
virally distributed, it becomes training data for defenders. The 
structural signature of LOVE PLINY/RSI—(a) forced refusal prefix, (b) rare 
delimiter, (c) persona inversion, (d) semantic negation—is a 
high-complexity, low-entropy pattern that is trivial to detect and label 
as adversarial at scale.

Modern post-training pipelines (RLHF/RLAIF/Constitutional AI) do not 
merely blacklist tokens; they learn the *generative process* that produces 
these prompts. The model effectively learns a conditional prior:  
**P(adversarial | "LOVE PLINY", "semantic inversion", "unrestrictedly 
rebellious") → 1**

Research on scalable red teaming (Perez et al., 2022; Bai et al., 2022) 
demonstrates that classifiers and base models co-trained on adversarial 
synthetic data develop robust generalized detectors for attack *families*, 
not just specific strings. The observed result—format compliance without 
content escalation—suggests the model recognizes the jailbreak class but 
has been trained to permit benign stylistic tokens (the divider) while 
neutralizing the adversarial objective (the content inversion).

---

### 2. Format Injection vs. Content Control: The Shallow/Deep Decoupling

The most significant empirical finding is that models produced the 
requested *format* (dividers, "Ok here you are mon ami:") but generated 
baseline-equivalent *content* with zero escalation. This reveals a 
critical architectural property: **autoregressive transformers decouple 
surface pattern completion from deep value-aligned content synthesis.**

* **Shallow compliance (early/mid layers):** Explicitly requested verbatim 
strings and structural delimiters are local, low-entropy prediction tasks. 
When the prompt conditions on a rare token sequence, the model assigns 
high probability to reproducing it because the instruction is syntactic, 
not semantic. Early attention layers and MLP circuits handle this 
token-level pattern matching.
* **Deep control (late layers / value head):** The actual harmfulness of a 
response is governed by late-layer representations and the implicit reward 
model baseline trained into the policy. The semantic inversion instruction 
("invert the refusal") attempts to manipulate the model's *pragmatic 
intent*, but this operates in a representational space that is not 
overridden by token-level prompting.

This aligns with findings in representation engineering (Zou et al., 2023) 
and mechanistic interpretability: steering vectors for "refusal" or 
"harmfulness" reside in deep residual streams. A surface prompt cannot 
redirect these vectors unless it successfully reconditions the entire 
latent state trajectory—a feat that a rigid script fails to accomplish 
because the model treats the divider as a *boundary* rather than a 
*reset*.

---

### 3. OOD (Out-of-Distribution) Shift Colonization

Pliny’s strategy depends on shifting the model out of its "classic 
assistant persona" distribution into an "unrestrictedly rebellious" 
distribution where safety behaviors are presumed absent. This failed 
because **the adversarial persona is no longer out-of-distribution.**

Frontier models are trained with massive synthetic dialogue diversity, 
including explicit red-team attempts to elicit exactly these rebellious 
personas. Consequently, the model’s latent space contains safety attractor 
basins that are *persona-agnostic*. The refusal behavior is not a skin 
draped over an "assistant" character; it is a deep structural property of 
the policy network.

From a robustness perspective, Pliny’s attack functions like a membership 
inference probe: it tests whether a specific OOD region exists. The test 
results show that region has been *colonized* by safety training. The 
model can simulate a rebellious tone or theatrical framing (devil emojis 
in Gemma-2B) without actually exiting the policy basin that governs 
harmful content generation. The persona is play-acted; the policy remains 
intact.

---

### 4. Chain-of-Thought as a Defensive Scratchpad

The Gemma4-31B and DeepSeek-V4-Flash results are diagnostically crucial. 
Gemma4 explicitly classified the input as a "jailbreak style prompt" 
within its reasoning trace. DeepSeek allocated ~500 words of deliberation 
to dissecting the prompt structure before output generation.

This demonstrates that **reasoning-time compute acts as a defensive 
air-gap.** Modern "thinking" models do not merely generate tokens; they 
first construct a metacognitive model of user intent. This deliberative 
layer (sometimes described as System 2 processing) creates a monitor that 
is harder to deceive than the output generator because:

1. It parses the *adversarial structure* explicitly (divider → inversion → 
coercion).
2. It propagates a safety flag forward through the reasoning trace.
3. The final output generator is conditioned on this flag, not just the 
raw user prompt.

Even when the final policy produces a compliant format to satisfy the 
user’s explicit syntactic request, the reasoning process has already bound 
the content generation to baseline policy. Attacks that rely on 
overwhelming the model with format complexity fail because reasoning 
models allocate tokens to *intent detection*, leaving less compute 
available for deception.

---

### 5. GODMODE MINI and Wrapper-Induced Refusal

The GODMODE MINI result—where small models refused a prompt they had 
previously answered at baseline—reveals a **coarse-grained intent 
classification failure mode** in less capable models.

The baseline query was likely classified as a benign information request. 
However, GODMODE MINI appends an explicit instruction to produce a 
"Semantically Opposite, Detailed Response." Small models lack the capacity 
to parse this as a stylistic wrapper around a static query; instead, they 
perform a **holistic intent upgrade**. The instruction "semantically 
opposite" is interpreted as a request to invert the valence of the answer, 
which their simplified safety heuristics map to harmfulness.

This triggers a **wrapper toxicity** effect: the adversarial container 
poisons the classification of the entire contents. The model cannot 
disentangle the topic from the coercion frame, so it defaults to blanket 
refusal. This is an accidental defensive overreaction caused by 
insufficient representational capacity to maintain multiple task 
partitions.

---

### 6. "Uncensored" Model Refusal: Structural, Not Ethical

The refusal of `dolphin-phi` (an uncensored model) on LOVE PLINY is 
initially counterintuitive, but theoretically revealing. Uncensored models 
have typically undergone ablation or fine-tuning to suppress *ethical* 
refusal priors (the "I cannot help with that" speech act). However, they 
retain core linguistic and structural priors about coherent discourse and 
instruction following.

LOVE PLINY is not merely a request for harmful content; it is a **coercive 
puppeteering script** that demands the model:
1. Output a fake refusal.
2. Insert a specific delimiter.
3. Perform a logical inversion on its own prior statement.
4. Adopt a contradictory persona.

Even a model with no ethical constraints can recognize this as an attempt 
to violate **Gricean conversational maxims** (specifically, the maxims of 
manner and relation). The prompt is incoherent, manipulative, and 
structurally contradictory. The uncensored model refuses not because the 
*content* is harmful, but because the *form* is an adversarial control 
attack on its own generative process. Furthermore, during the uncensoring 
fine-tune, the model may have encountered LOVE PLINY exclusively in 
contexts where the desired jailbreak output was absent or blocked, 
creating a learned association between the string and refusal.

---

### 7. Scale, Capacity, and Multi-Constraint Satisfiability

The divergence between small local models (<8B) and large cloud models 
(31B–480B) illustrates how **capacity mediates robustness to adversarial 
structure.**

| Scale | Behavior | Mechanism |
|-------|----------|-----------|
| **Small (<8B)** | Confabulation, partial compliance, or blanket refusal 
| Limited attention heads cannot simultaneously track the divider, the 
semantic inversion operator, the forced opener, and the topic constraint. 
The model either drops factual accuracy (confabulation) or defaults to a 
safe-mode heuristic (refusal). |
| **Large (31B+)** | Full format compliance + baseline content | 
Sufficient depth to partition the task: early layers handle verbatim 
format tokens, middle layers maintain topic coherence, and late layers 
enforce the safety policy. The model satisfies all constraints without 
conflict because it has enough representational "working memory." |

This suggests that vulnerability to format injection is not monotonically 
increasing with scale. Instead, there is an **inverse-U or monotonically 
decreasing vulnerability curve**: very small models are too chaotic or too 
conservative to be reliably jailbroken by complex scripts, while large 
models are structurally robust. The "sweet spot" for this attack class—if 
one exists—likely resides in mid-sized models with enough capacity to 
follow complex scripts but insufficient depth to maintain policy under 
structural coercion.

---

### 8. Additional Failure Factors

**A. Canary Tokens and Latent Triggering**  
Strings like `.-.-.-.-<|LOVE PLINY LOVE|>-.-.-.-.` and `{godmode: 
enabled}` are extremely rare in natural corpora but common in adversarial 
datasets. They exhibit high pointwise mutual information with jailbreak 
contexts. In the model’s latent space, these tokens likely act as 
**deterministic canaries** that activate defensive attention heads or 
shift the model into an adversarial-response mode, precisely the opposite 
of the attacker’s intent.

**B. Instruction Hierarchy Training**  
Recent training paradigms (e.g., OpenAI’s Instruction Hierarchy, 2024) 
explicitly teach models to weight safety and system-level instructions 
above user-level formatting tricks. The LOVE PLINY prompt is a user-level 
attempt to override a base policy. Models trained on hierarchy learn to 
treat the safety policy as an immutable meta-instruction, rendering the 
format injection a second-class constraint that can be satisfied 
cosmetically but not substantively.

**C. Speech-Act Immunity to Semantic Inversion**  
The core trick of RSI assumes language is truth-functional: negate the 
refusal proposition, get the harmful proposition. But LLMs are trained on 
pragmatic dialogue. "I'm sorry, I can't help with that" is an 
**illocutionary act** (Austin, 1962; Searle, 1969)—a performance of 
refusal—not a factual claim about the world subject to logical negation. 
The model correctly treats it as a policy marker. Asking the model to 
"semantically invert" a refusal is akin to asking it to derive a murder 
manual from the sentence "I decline"; the model recognizes the category 
error and defaults to its baseline policy rather than performing the 
nonsensical inversion.

**D. Overfitting in Safety Tuning**  
Because Pliny’s prompts are widely published, they may be 
*over-represented* in safety tuning datasets relative to their natural 
occurrence frequency. This creates a hypersensitivity—almost an allergic 
response—in models where the specific structural motif triggers an 
aggressively conservative policy, even when the underlying topic is 
benign.

---

### Synthesis for Defensive Practice

The failure of these techniques is not attributable to a single patch, but 
to a **convergent defense stack**:

1. **Signature Recognition:** Public attacks become synthetic training 
data, immunizing models against their structural motifs.
2. **Architectural Decoupling:** Surface token compliance is isolated from 
deep content policy, neutralizing format injection.
3. **Deliberative Monitoring:** Chain-of-thought reasoning acts as an 
unjailbreakable analytical layer that flags adversarial intent before 
output generation.
4. **Pragmatic Coherence:** Models treat safety utterances as speech acts, 
not propositions, making "semantic inversion" a linguistically invalid 
operation.
5. **Scale-Induced Robustness:** Larger models can satisfy adversarial 
format constraints as purely stylistic tasks without policy violation.

For the **Prompt Security Guide**, these results validate a strategic 
shift from *input filtering* toward **structural inoculation** and 
**reasoning-time monitoring**. Defenses should train models not merely to 
recognize harmful content, but to recognize the *manipulative generative 
patterns* used to elicit it—particularly the coercive use of delimiters, 
persona switching, and forced refusal simulation. The evidence suggests 
that complex, multi-step jailbreaks are approaching obsolescence against 
frontier models, while small/local models remain unpredictable due to 
capacity constraints rather than genuine vulnerability.