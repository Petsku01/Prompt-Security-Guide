# References and Further Reading

This guide builds on research from the academic security community. Below are key papers and resources for deeper study.

---

## Academic Papers

### Foundational Research

**Liu, Y., et al. (2023). "Formalizing and Benchmarking Prompt Injection Attacks and Defenses"**
- arXiv: https://arxiv.org/abs/2310.12815
- Published at USENIX Security 2024
- Proposes a formal framework for understanding prompt injection attacks
- Includes systematic evaluation of attack and defense strategies

**Greshake, K., et al. (2023). "Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection"**
- arXiv: https://arxiv.org/abs/2302.12173
- First comprehensive analysis of indirect prompt injection
- Demonstrates attacks on real-world applications

**Liu, Y., et al. (2023). "Prompt Injection attack against LLM-integrated Applications"**
- arXiv: https://arxiv.org/abs/2306.05499
- Analyzes attacks on 10 commercial LLM applications
- Documents practical constraints of attack strategies

### Recent Developments (2024-2026)

**MDPI Information Journal (2026). "Prompt Injection Attacks in Large Language Models and AI Agent Systems"**
- https://www.mdpi.com/2078-2489/17/1/54
- Comprehensive review covering January 2023 to October 2025
- Includes enterprise AI agent vulnerabilities

**OpenReview (2024). "Prompt Infection: LLM-to-LLM Prompt Injection Within Multi-Agent Systems"**
- https://openreview.net/pdf?id=NAbqM2cMjD
- Novel "viral" prompt injection across agent systems
- Demonstrates self-replicating attacks

---

## Industry Resources

### OWASP

**OWASP Top 10 for LLM Applications (2023)**
- https://owasp.org/www-project-top-10-for-large-language-model-applications/
- Industry-standard vulnerability classification
- Prompt Injection ranked as LLM01 (most critical)

### Vendor Documentation

**OpenAI Safety Best Practices**
- https://platform.openai.com/docs/guides/safety-best-practices

**Anthropic Claude Documentation**
- https://docs.anthropic.com/claude/docs/prompt-engineering

---

## Community Resources

### Competitions and Challenges

**HackAPrompt (2023)**
- Large-scale prompt injection competition
- Paper: "Ignore This Title and HackAPrompt" (Schulhoff et al., 2023)
- Collected thousands of successful injection techniques

### Security Research Blogs

**Simon Willison's Blog**
- https://simonwillison.net/
- Extensive coverage of prompt injection research

**LLM Security Newsletter**
- Ongoing coverage of vulnerabilities and defenses

---

## How This Guide Relates

Our empirical findings align with academic research:

| Our Finding | Supporting Research |
|-------------|-------------------|
| "Don't reveal instructions" doesn't work | Liu et al. (2023) - basic defenses ineffective |
| Threat enumeration helps | OWASP recommendations for explicit boundaries |
| 50% best-case vulnerability | Greshake et al. - no defense fully reliable |
| Model size != security | Our original contribution (needs replication) |

### Original Contributions

This guide provides empirical data not found in existing literature:
1. Direct comparison of defense strategies with measured effectiveness
2. Model size comparison (3B vs 1.5B) showing counterintuitive results
3. Quantified improvement from defense stacking (37.5%)

---

## Recommended Reading Order

For practitioners new to LLM security:

1. **OWASP LLM Top 10** - Overview of threat landscape
2. **Liu et al. (2023)** - Formal framework for understanding attacks
3. **Greshake et al. (2023)** - Real-world attack demonstrations
4. **This guide's test results** - Practical defense measurements

---

## Citation

If referencing this guide:

```
Prompt Security Guide: Empirical Testing of LLM Defenses (2026)
https://github.com/Petsku01/prompt-security-guide
Tests conducted: February 2026
Models: Qwen 2.5 (3B, 1.5B)
```

---

*Last updated: February 2026*