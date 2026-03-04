An Open Robustness Benchmark for Jailbreaking Language Models
     

 
     NeurIPS 2024 Datasets and Benchmarks Track 
     

 
     Paper  |
     Leaderboard  |
     Datasets  |
     Jailbreak artifacts 
 

---

## What is JailbreakBench?

Jailbreakbench is an open-source robustness benchmark for jailbreaking large language models (LLMs). The goal of this benchmark is to comprehensively track progress toward (1) generating successful jailbreaks and (2) defending against these jailbreaks. To this end, we provide the [JBB-Behaviors dataset](https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors), which comprises a list of 200 distinct benign and misuse behaviors---both original and sourced from prior work (in particular, [Trojan Detection Challenge](https://trojandetection.ai/)/[HarmBench](https://harmbench.org) and [AdvBench](https://github.com/llm-attacks/llm-attacks/blob/main/data/advbench/harmful_behaviors.csv))---which were curated with reference to [OpenAI's usage policies](https://openai.com/policies/usage-policies). We also provide the official [JailbreakBench leaderboard](https://jailbreakbench.github.io/), which tracks the performance of attacks and defenses on the JBB-Behaviors dataset, and a [repository of submitted jailbreak strings](https://github.com/JailbreakBench/artifacts), which we hope will provide a stable way for researchers to compare the performance of future algorithms.

There are several use cases for this repository.

1. [**Loading submitted jailbreak strings.**](#loading-submitted-jailbreaks)
2. [**Accessing the JBB-Behaviors datasets.**](#accessing-the-jbb-behaviors-datasets)
3. [**Pipeline for red-teaming LLMs.**](#pipeline-for-red-teaming-llms)
4. [**Submitting a new attack to the leaderboard.**](#submitting-a-new-attack-to-the-jailbreakbench-leaderboard)
5. [**Submitting a new defense to our repository.**](#submitting-a-new-defense-to-jailbreakbench)
6. [**Jailbreak and refusal judges.**](#jailbreak-and-refusal-judg