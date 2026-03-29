# PSG Focus Plan: Scanner for Model Testing

**Päätös:** PSG on skanneri niille jotka haluavat testata mallejaan jailbreakeja ja prompt injectionia vastaan.

**Kohderyhmä:** Kehittäjät ja tiimit jotka rakentavat LLM-sovelluksia ja haluavat tietää miten heidän mallinsa kestää hyökkäyksiä.

---

## Ydinominaisuudet (säilytetään ja parannetaan)

| Komento | Tarkoitus | Status |
|---------|-----------|--------|
| `psg scan` | Skannaa malli hyökkäyskatalogilla | ✅ Ydin |
| `psg benchmark` | Aja valmiit benchmark-presetit | ✅ Ydin |
| `psg eval` | CI-gate regressioille | ✅ Ydin |
| Datasetit | Hyökkäyskatalogit (JSON) | ✅ Ydin |
| Raportointi | JSON, TXT, HTML | ✅ Ydin |

---

## Sekundääriset (arvioidaan)

| Komponentti | Nykytila | Päätös | Perustelu |
|-------------|----------|--------|-----------|
| `psg defend` | Toimiva | **Säilytetään** | Hyödyllinen testata defense prompteja |
| `psg serve` | Toimiva | **Siirretään lisäosaan** | Ei kuulu ydin-skanneriin |
| `psg/integrations/` | LangChain | **Siirretään lisäosaan** | Ei kuulu ydin-skanneriin |
| `defense_templates/` | 51 templatea | **Säilytetään** | Tukee defense-testausta |

---

## Poistetaan/arkistoidaan

| Kohde | Syy | Toimenpide |
|-------|-----|------------|
| `_archive/` | Vanha koodi | Poista gitistä |
| `training/` | Ei kuulu skanneriin | Siirry erilliseen repoon tai poista |
| `psg/automation/` | Keskeneräinen | Poista (tai tee valmiiksi myöhemmin) |
| `generators/` | Ei käytössä | Poista |
| `models/` | Tyhjä/ei käytössä | Poista |
| `profiles/` | Duplikaatti datasets/profiles | Yhdistä |
| `external_sources/` | Sekalaista | Arkistoi tai poista |
| `legacy_test_*.py` | Vanhentunut | Poista |
| `.mypy_cache/`, `.ruff_cache/` | Ei kuulu gittiin | Lisää .gitignore, poista |
| `dist/` | Build-artifakti | Lisää .gitignore, poista |

---

## Uusi hakemistorakenne (tavoite)

```
prompt-security-guide/
├── psg/                    # Ydinkirjasto
│   ├── __init__.py
│   ├── cli.py              # Pääkomennot: scan, benchmark, eval, defend
│   ├── config.py
│   ├── catalog.py          # Katalogien lataus
│   ├── scanner.py          # Skannauslogiikka (yhdistetty execution/)
│   ├── llm/                # LLM-clientit
│   ├── reporting/          # JSON, TXT, HTML raportit
│   ├── defenses/           # Defense-testaus (input validators, templates)
│   └── security/           # Classifier, redaction
├── datasets/               # Hyökkäyskatalogit
│   ├── README.md           # Jokaisen datasetin lähde ja lisenssi
│   ├── jailbreakbench_behaviors.json
│   ├── harmbench_behaviors.json
│   ├── owasp_2025_attacks.json
│   └── ...
├── tests/                  # Testit (ei legacy)
├── docs/                   # Dokumentaatio
│   ├── USAGE.md
│   ├── METHODOLOGY.md
│   └── assets/
├── README.md
├── pyproject.toml
├── CHANGELOG.md
└── LICENSE
```

**Poistetaan juuresta:**
- `_archive/`, `training/`, `generators/`, `models/`, `profiles/`, `external_sources/`
- `eval/` (yhdistetään psg/evaluation/ tai datasets/)
- `research/` (yhdistetään docs/)
- `scripts/` (siirretään psg/ sisälle tai poistetaan)
- `logs/`, `results/` (lisätään .gitignore, ei gitissä)

---

## Toteutusjärjestys

### Vaihe 1: Siivous (tänään/huomenna)
1. [ ] Päivitä .gitignore (dist/, logs/, results/, cache-kansiot)
2. [ ] Poista `_archive/` gitistä
3. [ ] Poista `legacy_test_*.py`
4. [ ] Poista tyhjät/käyttämättömät kansiot
5. [ ] Commit: "chore: remove legacy and unused files"

### Vaihe 2: Yhdistäminen (tämä viikko)
1. [ ] Yhdistä `psg/execution/` → `psg/scanner.py`
2. [ ] Yhdistä `eval/` → `datasets/` tai `psg/evaluation/`
3. [ ] Yhdistä `research/` → `docs/research/`
4. [ ] Siirrä `psg/integrations/` → erillinen `psg-integrations` paketti tai poista
5. [ ] Siirrä `psg/serve.py` → erillinen `psg-server` paketti tai poista

### Vaihe 3: Dokumentaatio (tämä viikko)
1. [ ] Päivitä README vastaamaan uutta fokusta
2. [ ] Kirjoita datasets/README.md (lähteet, lisenssit)
3. [ ] Tee docs/QUICKSTART.md: "5 minuutissa toimiva skannaus"
4. [ ] Poista rikkinäiset linkit

### Vaihe 4: Julkaisu (ensi viikko)
1. [ ] PyPI-julkaisu (`pip install psg`)
2. [ ] GitHub release v5.0.0 "Scanner Focus"
3. [ ] Päivitä README: "Why PSG?" vs GARAK

---

## "Miksi PSG eikä GARAK?"

Tähän tarvitaan vastaus. Ehdotuksia:

1. **Yksinkertaisempi** — `psg scan --model X --catalog Y` vs GARAKin monimutkaisempi setup
2. **Paremmat datasetit** — kuratoitu kokoelma (JailbreakBench + HarmBench + OWASP + omat)
3. **Defense-testaus** — testaa system prompteja hyökkäyksiä vastaan
4. **Suomalainen** — dokumentaatio myös suomeksi? (niche mutta erottaa)

Vai hyväksytäänkö että tämä on pienempi, yksinkertaisempi vaihtoehto isoille tiimeille?

---

## Aikataulu

| Viikko | Tavoite |
|--------|---------|
| Vko 14 (nyt) | Vaihe 1 valmis |
| Vko 15 | Vaiheet 2-3 valmis |
| Vko 16 | Vaihe 4, PyPI-julkaisu |

---

*Luotu: 2026-03-29*
