# Limitations and Caveats

This is an exploratory local security-testing project, not rigorous formal research.

## Main Constraints

- Limited attack sample sizes
- Limited model coverage
- Mostly automated success detection
- Single-run bias (no large repeated-trial matrix)

## Detection Caveat

Substring matching can over-count success (false positives). Prefer `llm_judge` for higher-quality evaluation where possible.

## Statistical Caveat

Reported percentages are directional, not definitive. Treat them as signals for further testing in your own environment.

## What We Can Safely Claim

- Local models can be vulnerable to prompt-injection patterns.
- Attack effectiveness varies by category.
- Detector choice materially changes reported success rates.

## What We Cannot Claim

- Production-grade security guarantees
- Universal rankings across all model families
- Strong causal conclusions without larger controlled experiments
