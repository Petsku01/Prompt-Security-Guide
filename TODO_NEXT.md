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

### 2. CI regression gate (S)
```bash
psg eval --golden datasets/classifier_golden.json --fail-on-macro-f1-below 0.85
```
- Tavoite: GitHub Actions -valmis
- Lisää: exit code 1 jos threshold ei täyty

### 3. Parallel scan (M)
```bash
psg scan --workers 4 --model llama3:8b --catalog datasets/owasp_2025_attacks.json
```
- Tavoite: 2-4x nopeampi suoritus
- Toteutus: `concurrent.futures.ThreadPoolExecutor`

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
