# Migration Guide (v2 -> v3)

## What changed

- `jailbreak_tester/` is now the canonical runtime.
- Root `tester.py` is deprecated and forwards to `legacy/tester_v2.py`.
- `tools/` moved to `legacy/tools/` (compat symlink retained temporarily).
- Heavy research artifacts moved to `archive/deprecated/`.

## Update commands

### Old

```bash
python tester.py --model llama3:8b --catalog datasets/obliteratus_attacks.json
```

### New

```bash
python -m jailbreak_tester --model llama3:8b --catalog datasets/obliteratus_attacks.json
```

## Import migration

### Old imports

```python
from tools.runner import TestRunner
from tools.config import RunConfig
```

### New recommendation

Treat legacy modules as frozen compatibility code. New development should target `jailbreak_tester.*` modules.

## Deprecation timeline

- v3.x: compatibility wrappers/symlink remain
- v4.0: planned removal of root `tester.py` and `tools` compatibility path
