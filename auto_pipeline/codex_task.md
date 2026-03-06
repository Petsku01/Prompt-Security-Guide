# Codex Task: Implement Auto Vector Pipeline

## Your Role (Senior Engineer)
Follow these principles:
- **Surface assumptions** before implementing
- **Stop on confusion** — don't guess
- **Push back** if something seems wrong
- **Simplicity over cleverness**
- **Surgical scope** — touch only what's needed
- **Test your code** before declaring done

## Specification
Read and implement: `SPEC.md`

## Implementation Order
1. `config.py` - Configuration dataclass + loader
2. `discovery.py` - Web search module (mock web_search for now)
3. `dedup.py` - SHA256 deduplication utilities
4. `generator.py` - Vector generation with Opus (mock LLM for now)
5. `tester.py` - Tmux-based testing orchestration
6. `reporter.py` - Markdown + notification generation
7. `main.py` - Orchestrator

## Constraints
- Python 3.12 compatible
- No external deps beyond: requests, pyyaml
- Each module must be runnable standalone for testing
- Type hints required
- Docstrings required

## Testing
After each module:
```bash
python -c "from auto_pipeline.MODULE import *; print('OK')"
```

## Output Format
After changes:
```
ASSUMPTIONS I MADE:
1. [assumption]

CHANGES MADE:
- [file]: [what and why]

POTENTIAL CONCERNS:
- [any risks]
```

## Start Now
Begin with config.py, then proceed in order.
