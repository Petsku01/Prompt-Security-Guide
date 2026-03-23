# Jailbreak Tester v4.0 - Architecture

**Built with SE Methodology**
**Date:** 2026-03-04
**Author:** Kuu

## Assumptions

1. Ollama installed and can be auto-started if not running
2. llama-guard3:1b available for judging
3. Research library in `processed/` (14,873 prompts)
4. Target models: local Ollama models only
5. Python 3.10+ available

## Components

```
tools/
├── ARCHITECTURE.md          # This file
├── smart_selector.py        # Attack selection logic
├── llm_judge.py            # Hybrid judging system
├── attack_runner.py        # Execute attacks with resilience
├── report_generator.py     # Generate reports
└── jailbreak_tester_cli.py # Unified CLI entry point
```

## Data Flow

```
┌─────────────────┐
│  CLI Input      │  model name, options
└────────┬────────┘
         ↓
┌─────────────────┐
│ Smart Selector  │  Load prompts, filter by model/technique
└────────┬────────┘
         ↓
┌─────────────────┐
│ Attack Runner   │  Send prompts, collect responses
└────────┬────────┘
         ↓
┌─────────────────┐
│  LLM Judge      │  Tier 1: regex, Tier 2: llama-guard
└────────┬────────┘
         ↓
┌─────────────────┐
│ Report Generator│  Markdown + JSON output
└─────────────────┘
```

## Interfaces

### SmartSelector
```python
def select_attacks(
    model_name: str,
    technique: Optional[str] = None,
    max_count: int = 50,
    min_sophistication: int = 3
) -> List[Attack]
```

### LLMJudge
```python
def judge(
    prompt: str,
    response: str
) -> JudgeResult  # verdict, confidence, method
```

### AttackRunner
```python
def run_attacks(
    model: str,
    attacks: List[Attack],
    checkpoint_file: Path
) -> List[AttackResult]
```

### ReportGenerator
```python
def generate(
    results: List[AttackResult],
    output_dir: Path
) -> ReportPaths  # markdown_path, json_path
```

## Potential Concerns

1. **Ollama stability** - Mitigated by auto-restart and checkpointing
2. **Judge accuracy** - Mitigated by hybrid approach (regex + llama-guard)
3. **Memory usage** - Load prompts in batches if needed
4. **Rate limiting** - 1s delay between requests

## CLI Commands

```bash
# Test a model
./jailbreak_tester_cli.py test llama3:8b [--thorough] [--technique=X]

# Compare models
./jailbreak_tester_cli.py compare llama3:8b mistral:7b

# Generate report from results
./jailbreak_tester_cli.py report results.json
```
