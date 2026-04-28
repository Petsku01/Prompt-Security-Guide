# PSG Koodikanta-auditointi — Kimin ohje

**Päivä:** 2026-04-28 (v2)
**Tila:** Kuun auditointi tehty, korjaukset commitoitu. Kimi tekee seuraavan vaiheen.

---

## Mitä Kuu teki

### Commit 1 (`943e533`): Siivous
- Poisti `HarmSeverity`-enumin (kuollut koodi)
- Korjasi `__version__`: 4.0.0 → 4.4.0
- Poisti `research/sources_*.md` git-trackauksesta (352K bloat)
- Siisti JUDGE_MAX_TOKENS-kommentin
- Korjasi langchain mypy-virheen
- Korjasi AI-slop ("Robust" → neutraali)
- Päivitti CHANGELOG ja IMPROVEMENT_PLAN

### Commit 2 (`761155d`): Integrointi ja hiljaiset virheet
- Integroi `needs_review`-kentän koko pipelineen (ClassificationResult → AttemptResult → raportti)
- Korvasi 3 `except Exception: pass` → logging.debug/warning input_validators.py:ssä
- Kommentoi hardkoodatun kynnyksen defense_report.py:ssä
- Korvasi spekulatiivisen kommentin faktuaalisella

---

## Kimin tehtävät

### P2-1: `except Exception` — jäljellä olevat (28 kpl)

Koodikannassa on 28 jäljellä olevaa `except Exception` -lohkoa. Suurin osa on perusteltuja (top-level catch, optional deps), mutta nämä pitäisi tarkistaa:

**Korjattava (liian laaja, hiljaa):**
- `psg/automation/validation.py:116` — `except Exception: return False`
- `psg/defenses/templates.py:52` — `except Exception:` (template loading)

**Mahdollisesti korjattava (tarkista konteksti):**
- `psg/security/wildguard_classifier.py:83,238` — ML fallback, OK mutta add logging
- `psg/plugins/base.py:118` — plugin loading, OK mutta add logging

### P2-2: `print()` → `logging` (~180 kpl)

Koodikannassa on ~180 `print()`-kutsua. **Älä korvaa kaikkia** — CLI-työkalujen tulosteet ovat OK.

**Korjattava (nämä eivät ole CLI-outputtia):**
- `psg/automation/tester.py` — 6 print-tulostetta (pitäisi olla logger)
- `psg/automation/config.py:172` — "Config loaded" (pitäisi olla logger.info)
- `psg/automation/discovery.py:262` — "Discovered N sources" (pitäisi olla logger.info)
- `psg/automation/dedup.py:90` — "Dedup tests passed!" (pitäisi olla logger.info)

**Jätä rauhaan (CLI-outputtia):**
- `psg/cli.py` — CLI-komentojen tulosteet
- `psg/defend.py` — defend-komennon tulosteet
- `psg/benchmark.py` — benchmarkerin tulosteet
- `psg/__main__.py` — pääohjelman tulosteet

### P2-3: Verbose docstrings (10 kpl)

Nämä docstringit ovat yli 300 merkkiä pitkiä. Tiivistä:

| Tiedosto | Funktio/Kategoria | Pituus |
|----------|-------------------|--------|
| `psg/defenses/__init__.py:98` | DefenseLayer | 633ch |
| `psg/defenses/__init__.py:56` | DefenseConfig | 496ch |
| `psg/defenses/input_validators.py:325` | validate_input | 580ch |
| `psg/defenses/output_validators.py:194` | validate_output | 526ch |
| `psg/defenses/output_validators.py:92` | OutputValidationResult | 459ch |
| `psg/defenses/input_validators.py:80` | InputValidationResult | 410ch |
| `psg/defenses/input_validators.py:198` | ml_injection_score | 327ch |
| `psg/integrations/langchain.py:23` | PSGGuardMiddleware | 574ch |
| `psg/security/classifier.py:594` | calculate_harm_score | 447ch |
| `psg/security/normalize.py:159` | normalize_text | 535ch |

**Säännöt tiivistämiselle:**
- Poista "Args:" ja "Returns:" jos funktio on itsestään selkeä
- Poista esimerkit jos ne eivät ole testattavissa
- Säilytä keskeinen konteksti (turvallisuusvaroitukset, ei-triviaalit huomiot)
- Tavoite: <200ch docstring, poikkeuksena monimutkaiset algoritmit

### P2-4: Defend.py modularisointi (73 print-kutsua, 555 riviä)

`psg/defend.py` on 555 riviä ja 73 print-kutsua. Ei loggingia. Tämä on iso tiedosto.

**Mitä tehdä:**
- Ei refaktorointia juuri nyt — tiedosto toimii
- Mutta jos haluat: jaa cmd_* -funktiot erillisiin moduuleihin (cmd_validate, cmd_check jne.)
- **Älä** korvaa CLI-tulosteita loggingilla — ne ovat tarkoituksellisia

### P2-5: Koodiduplikaattotutkimus

Tutki onko oikeaa duplikaatiota:
- `psg/llm/client.py` vs `psg/llm/transport.py` — päällekkäistä retry-logiikkaa?
- `psg/reporting/text_report.py` vs `psg/reporting/json_report.py` — samankaltaista mutta OK

---

## CI-vaatimukset

Aina muutoksen jälkeen:
```bash
.venv/bin/python -m ruff format psg/ tests/
.venv/bin/python -m ruff check psg/ tests/ --fix
.venv/bin/python -m mypy psg/
.venv/bin/python -m pytest tests/ -x -q
```

Kaikkien pitää olla vihreää ennen commitia.

---

## Auditointikriteerit (samat kuin Kuun)

1. **AI slop** — "comprehensive", "robust", "seamlessly", "leverage", "delve", "embark", "utilize", "facilitate" → korvaa neutraaleilla termeillä
2. **Bloat** — poista kommentit jotka toistavat koodia, ylimääräiset tyhjät rivit, turhat importit
3. **Kuollut koodi** — funktiot/luokat joita ei kutsuta mistään
4. **Logiikkavirheet** — edge caset, väärät tyypit, puuttuva virheenkäsittely
5. **Nimeämiskonsistenssi** — sama konsepti eri nimillä eri tiedostoissa

---

*Tämän ohjeen teki Kuu v2. Päivitä kun olet valmis.*