# PSG Refactor Plan

## Goals
1. Simplify structure (60 files → ~30)
2. Better documentation (tutorials, getting started)
3. Docker/pip packaging
4. ML fine-tuning setup

---

## 1. Structure Simplification

### Current (messy)
```
psg/
├── automation/      # 5 files - unclear purpose
├── execution/       # 4 files - could merge
├── integrations/    # 2 files - incomplete
├── llm/            # 4 files
├── plugins/        # 4 files
├── reporting/      # 4 files
├── security/       # 6 files
├── validation/     # 3 files
├── defenses/       # 5 files (NEW)
└── 12 root files
```

### Target (clean)
```
psg/
├── core/           # models, config, errors
├── scan/           # scanning logic (merge execution/)
├── detect/         # detectors, classifiers (merge security/)
├── defend/         # defense module (keep)
├── report/         # all reporting
├── cli.py          # single CLI entry
├── api.py          # FastAPI server
└── __init__.py
```

### Files to remove/merge:
- `automation/` → move useful parts to scripts/, delete rest
- `integrations/` → move to examples/ or delete
- `plugins/` → inline into detect/
- `validation/` → merge into detect/

---

## 2. Documentation

### New docs structure:
```
docs/
├── getting-started.md      # 5-min quickstart
├── tutorials/
│   ├── scan-first-model.md
│   ├── test-defense-prompt.md
│   ├── build-custom-detector.md
│   └── fine-tune-detector.md
├── reference/
│   ├── cli.md
│   ├── api.md
│   └── config.md
└── examples/
    ├── basic-scan.py
    ├── defense-layer.py
    └── ci-integration.py
```

---

## 3. Packaging

### pyproject.toml updates:
- Proper entry points
- Optional deps: `pip install psg[ml]`, `pip install psg[server]`
- Version management

### Docker:
```dockerfile
# Dockerfile
FROM python:3.12-slim
COPY . /app
RUN pip install /app[ml]
ENTRYPOINT ["psg"]
```

### CI:
- GitHub Actions for PyPI publish
- Docker Hub auto-build

---

## 4. ML Fine-tuning

### Setup:
```
training/
├── prepare_data.py      # Convert PSG datasets to training format
├── fine_tune.py         # Fine-tune deberta on our data
├── evaluate.py          # Eval on held-out test set
├── export_model.py      # Export to HuggingFace format
└── README.md            # Instructions
```

### Data sources:
- datasets/prompt_injection_techniques.json (25 attacks)
- datasets/jailbreak_*.json
- datasets/encoding_attacks.json
- Generate negatives from clean prompts

---

## Execution Order

1. **Docs first** (low risk, high value)
2. **Packaging** (enables easier testing)
3. **Refactor** (risky, do carefully)
4. **ML training** (separate effort)

---

## Time Estimate

| Task | Time |
|------|------|
| Docs | 2-3 hours |
| Packaging | 1-2 hours |
| Refactor | 4-6 hours |
| ML setup | 2-3 hours |
| **Total** | ~10-14 hours |

Start with docs tonight?
