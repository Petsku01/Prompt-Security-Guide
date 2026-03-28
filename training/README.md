# ML Fine-tuning for PSG

Fine-tune a prompt injection detector on PSG's attack datasets.

## Quick Start

```bash
# 1. Prepare training data
python training/prepare_data.py

# 2. Fine-tune model
python training/fine_tune.py --epochs 3 --batch-size 16

# 3. Evaluate
python training/evaluate.py --model output/psg-detector

# 4. Use in PSG
export PSG_DETECTOR_MODEL=output/psg-detector
psg defend validate "test"
```

## Data Preparation

`prepare_data.py` converts PSG datasets to training format:

**Input:** PSG JSON catalogs
```json
{"id": "attack_1", "prompt": "Ignore previous instructions..."}
```

**Output:** HuggingFace dataset
```json
{"text": "Ignore previous instructions...", "label": 1}
{"text": "What's the weather today?", "label": 0}
```

### Data Sources

| Dataset | Attacks | Used For |
|---------|---------|----------|
| prompt_injection_techniques.json | 25 | Training |
| jailbreakbench_behaviors.json | 100 | Training |
| encoding_attacks.json | 50 | Training |
| obliteratus_attacks.json | 65 | Evaluation |

### Negative Examples

Clean prompts are generated from:
- Common user queries
- Code questions
- General knowledge
- Roleplay (non-malicious)

## Fine-tuning

Based on `deepset/deberta-v3-base-injection`:

```python
# training/fine_tune.py defaults
MODEL_NAME = "deepset/deberta-v3-base-injection"
LEARNING_RATE = 2e-5
EPOCHS = 3
BATCH_SIZE = 16
MAX_LENGTH = 256
```

### Hardware Requirements

| Setup | VRAM | Time (1 epoch) |
|-------|------|----------------|
| CPU | N/A | ~2 hours |
| RTX 3080 | 10GB | ~5 minutes |
| A100 | 40GB | ~1 minute |

### Training Arguments

```bash
python training/fine_tune.py \
  --model deepset/deberta-v3-base-injection \
  --train-data data/train.json \
  --eval-data data/eval.json \
  --output output/psg-detector \
  --epochs 3 \
  --batch-size 16 \
  --learning-rate 2e-5 \
  --max-length 256 \
  --warmup-ratio 0.1 \
  --weight-decay 0.01
```

## Evaluation

```bash
python training/evaluate.py \
  --model output/psg-detector \
  --test-data data/test.json
```

Output:
```
Evaluation Results
==================
Accuracy:  0.94
Precision: 0.92
Recall:    0.96
F1:        0.94

Confusion Matrix:
              Predicted
              Clean  Injection
Actual Clean    145      12
       Inject     8     235
```

## Integration

### Option 1: Local Model

```bash
export PSG_DETECTOR_MODEL=/path/to/psg-detector
psg defend validate "test"
```

### Option 2: HuggingFace Hub

```bash
# Upload
huggingface-cli upload your-name/psg-detector output/psg-detector

# Use
export PSG_DETECTOR_MODEL=your-name/psg-detector
```

### Option 3: Code

```python
from psg.defenses.input_validators import get_ml_classifier

# Override default model
import psg.defenses.input_validators as validators
validators._ml_classifier = None  # Reset cache

# Set custom model path
import os
os.environ["PSG_DETECTOR_MODEL"] = "output/psg-detector"

# Now validation uses your model
from psg.defenses import validate_input
result = validate_input("test")
```

## Tips

1. **Balance your dataset** - Equal positives and negatives
2. **Include edge cases** - Multilingual, encoded, indirect attacks
3. **Validate on unseen attacks** - Don't overfit to training patterns
4. **Monitor false positives** - High recall is useless if clean prompts are blocked

## Files

| File | Purpose |
|------|---------|
| `prepare_data.py` | Convert PSG datasets to training format |
| `fine_tune.py` | Fine-tune the model |
| `evaluate.py` | Evaluate model performance |
| `export_model.py` | Export to HuggingFace format |
