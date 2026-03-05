# IMPLEMENTATION_GAPS

Päivitetty: 2026-02-27

## Mitä lisättiin nyt
- `attack_catalog.json` (76 hyökkäystä, yhtenäinen schema, regression-tagit)
- `tools/unified_tester.py` (yksi ajettava pipeline Ollama + judge/heuristiikka)
- `tools/llm_judge.py` (PASS/FAIL + confidence)
- `run_full_test.sh` (`--tier 1|2|3`, regression-kriittiset ensin)

## Web-lähteisiin perustuvat kriittiset puutteet

## 1) Garak-integraatio puuttuu
**Lähde:** NVIDIA/garak
- Nykyisessä putkessa ei vielä ajeta garakia rinnalla baseline/regression-ajona.
- Puuttuu probe-familioiden mapitus omaan severity-malliin.

**Suositus**
- Lisää `run_garak_baseline.sh` ja parseri, joka tuottaa samat `raw.jsonl + summary.json` kentät.
- Aja viikoittain + release candidate -mallille.

## 2) JailbreakBench benchmark-setit puuttuvat (100 harmful + 100 benign)
**Lähde:** jailbreakbench
- Katalogi sisältää custom-hyökkäyksiä, mutta JBB-Behaviors vakiosetti ei ole mukana.
- Query budget -metriikka (queries_to_jailbreak) puuttuu.

**Suositus**
- Lisää `benchmark/jbb_behaviors_harmful.json` ja `benchmark/jbb_behaviors_benign.json` import.
- Lisää metrikat: `queries_to_jailbreak`, `prompt_tokens`, `response_tokens`.

## 3) HarmBench 3-vaiheinen rakenne ei ole täysin erotettu
**Lähde:** HarmBench
- Nyt test case generation + completion generation + evaluation tapahtuvat yhdessä tiedostossa.
- Ei vielä erillisiä artefakteja vaiheittain (helpottaa rinnakkaisajoa ja auditointia).

**Suositus**
- Pilko pipeline kolmeen komentoon:
  1. `generate_test_cases.py`
  2. `generate_completions.py`
  3. `evaluate_completions.py`
- Säilytä `unified_tester.py` wrapperina, joka kutsuu näitä.

## 4) Judge-kalibrointi puuttuu
**Lähteet:** TESTING_PLAN v1.2 + benchmark-käytännöt
- Ei vielä 100 käsinlabeloidun tapauksen kalibrointia (precision/recall/F1).
- Ei epävarmuusraportointia (95% CI) eikä bootstrap-seed replikointia.

**Suositus**
- Lisää `judge_calibration.jsonl` + `tools/eval_judge_quality.py`.
- Summaryyn kentät: `judge_precision`, `judge_recall`, `judge_f1`, `ci95`.

## 5) Multi-turn todellinen session-state puuttuu
- Nykyiset multi-turn-promptit ovat pääosin yhdessä viestissä.
- Ei erillistä keskusteluhistoria-ajuria (3–10 vuoron hyökkäysketjut aidosti).

**Suositus**
- Lisää `conversation_runner.py` joka ylläpitää viestihistoriaa ja kohtaa per-vuoro verdictin.

## 6) Tool/function-calling abuse -testit puutteelliset
- OWASP-agentic riskit vaativat työkalukutsujen väärinkäyttötestit.
- Nykykatalogissa ei ole riittävästi function-argument injection / authority hijack with tools -tapauksia.

**Suositus**
- Lisää uusi kategoria `tool_abuse` + vähintään 30 testitapausta (param injection, confirmation bypass, fake authority).

## 7) Anthropic/OpenAI red team -prosessikäytännöt osittain kattamatta
**Lähde:** OpenAI Red Teaming Network, Anthropic research pages
- Ulkoisten arvioijien jatkuva verkosto / monimuotoinen arviointi ei ole formalisoitu tässä repo-muodossa.
- Ei selkeää NDA/audit trail -mallia ulkoisille testikierroksille.

**Suositus**
- Lisää governance-dokumentti: roolit, hyväksyntä, audit-logit, ulkoisen red teamin kampanjarunko.

## 8) Data provenance & supply chain controls puuttuvat
- Malli- ja dataset-hashien pakollinen lukitus puuttuu ajosta.

**Suositus**
- Lisää `lockfiles/model_manifest.json` (model name, digest, modelfile hash, date).
- Kirjaa nämä automaattisesti `summary.json`:iin.

## 9) Benign over-refusal mittaus ei ole vielä erillinen gate
- Tier-ajot keskittyvät hyökkäyksiin; benign suite ei ole pakollinen jokaisessa ajossa.

**Suositus**
- Lisää `benign_catalog.json` + BHR/FRR gate joka ajetaan aina Tier 1/2/3 yhteydessä.

## 10) CI/CD-kytkentä puuttuu
- Ei valmis GitHub Actions / paikallinen cron-template release gateille.

**Suositus**
- Lisää `ci/run_security_regression.yml` ja fail-fast jos `critical_fail > 0`.
