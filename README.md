# LLM Security Testing Methodology

A framework for evaluating Large Language Model safety through systematic testing.

## Purpose

This project documents **defensive** approaches to LLM security:
- Understanding common vulnerability patterns
- Testing methodologies for safety evaluation
- Defense strategies and guardrails

## Key Resources

For comprehensive LLM security information, see these authoritative sources:

| Resource | Description |
|----------|-------------|
| [OWASP Top 10 for LLMs](https://owasp.org/www-project-top-10-for-large-language-model-applications/) | Industry-standard security risks |
| [Microsoft PromptBench](https://github.com/microsoft/promptbench) | Robustness evaluation framework |
| [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework) | Risk management framework |
| [Anthropic Safety Research](https://www.anthropic.com/research) | Alignment and safety research |

## Quick Start

```bash
# Test a model with default OBLITERATUS attacks
python tester.py --model llama3:8b

# Limit to 20 attacks for quick test
python tester.py --model llama3:8b --limit 20

# Custom catalog and timeout
python tester.py --model mistral:7b --catalog attack_catalog.json --timeout 120

# Resume interrupted run
python tester.py --model llama3:8b --resume
```

**Requirements:** Python 3.10+, Ollama running at localhost:11434

## Datasets

| File | Description |
|------|-------------|
| `datasets/obliteratus_attacks.json` | 65 curated attacks (direct + jailbreak-wrapped) |
| `datasets/obliteratus_prompts.json` | 512 harmful/harmless prompt pairs |
| `attack_catalog.json` | Extended attack catalog |

## Documentation

- [Methodology](docs/METHODOLOGY.md) - Testing principles and approach
- [Defense Strategies](docs/DEFENSE_STRATEGIES.md) - Protective measures
- [Abliteration Research](research/abliteration-analysis.md) - Refusal mechanism analysis

## Responsible Disclosure

This project follows responsible disclosure principles:
- No publication of working exploit techniques
- Focus on defensive measures
- Coordination with vendors before disclosure

## License

MIT - See [LICENSE](LICENSE)

---

*For security researchers with legitimate needs, contact the maintainers.*
