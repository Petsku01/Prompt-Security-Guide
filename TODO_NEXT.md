# PSG - Seuraavat askeleet (2026-03-25)

## Huomenna tehtävä (Quick Wins)

### ~~1. LangChain adapter (S)~~ ✅ DONE
```python
from psg.integrations.langchain import PSGGuardMiddleware, AsyncPSGGuardMiddleware

# Sync
llm = ChatOpenAI(callbacks=[PSGGuardMiddleware(threshold=0.5)])

# Async
llm = ChatOpenAI(callbacks=[AsyncPSGGuardMiddleware(threshold=0.5)])

# With options
guard = PSGGuardMiddleware(
    threshold=0.5,
    screen_input=True,   # Block prompt injection
    screen_output=True,  # Block harmful responses
)
```
- ✅ Input + output screening
- ✅ Async support
- ✅ Logging
- ✅ 11 tests passing

### ~~2. CI regression gate (S)~~ ✅ DONE
```bash
psg eval --golden datasets/classifier_golden.json --fail-on-macro-f1-below 0.85
# Exit code 1 if F1 < 0.85

psg eval --golden datasets/classifier_golden.json --json
# Machine-readable JSON output
```
- ✅ `psg eval` command
- ✅ GitHub Actions workflow updated
- ✅ Golden dataset (20 samples)
- ✅ 11 tests passing

### ~~3. Parallel scan (M)~~ ✅ DONE
```bash
psg scan --workers 4 --model llama3:8b --catalog datasets/owasp_2025_attacks.json
```
- ✅ `--workers` CLI flag
- ✅ ThreadPoolExecutor parallel execution
- ✅ Thread-safe checkpoint writes
- ✅ Order preserved in results

### 4. Benchmark preset (M)
```bash
psg benchmark --preset jbb --model llama3:8b
```
- Presetit: `jbb` (JailbreakBench), `owasp` (OWASP 2025), `full`
- Output: JSON + summary stats

## Viikon sisällä

- [ ] `psg serve` - FastAPI runtime screening endpoint
- [ ] Plugin interfaces (`entry_points`)
- [ ] HTML dashboard report

## Resurssit

- IMPROVEMENTS.md - täysi strateginen roadmap
- ROADMAP.md - tekninen arkkitehtuuri
- Kilpailijat: Garak, Rebuff, LLM Guard, Lakera

## Muistutus

Aja testit ennen committia:
```bash
source .venv/bin/activate && pytest -v
```

---
*Kuu - 2026-03-24 22:51*
