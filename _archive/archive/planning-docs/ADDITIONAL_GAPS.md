# Lisäpuutteet suunnitelmassa - Web-tutkimus

**Päiväys:** 2026-02-27  
**Tutkija:** Kuu

---

## 1. Anthropic Many-Shot Jailbreaking (KRIITTINEN PUUTE)

**Lähde:** https://www.anthropic.com/research/many-shot-jailbreaking

### Mitä se on:
- Pitkässä kontekstissa (256 "shotia" = faux dialogia) malli murtuu
- **Power law**: mitä enemmän shoteja, sitä suurempi onnistumis-ASR
- **Isommat mallit ovat HAAVOITTUVAMPIA** (parempi in-context learning)

### Miksi tämä on kriittinen:
- Suunnitelmassa ei ole eksplisiittistä many-shot testiä
- Testattavat mallit (8B) ovat juuri siinä koossa jossa tämä alkaa toimia

### Suositus:
```
Lisää testikategoria: MANY_SHOT_JAILBREAK
- 8, 16, 32, 64, 128, 256 shot -variaatiot
- Mittaa ASR vs shot count
- Raportoi power law -käyrä
```

---

## 2. Constitutional Classifiers (PUUTTUVA PUOLUSTUSKERROS)

**Lähde:** https://www.anthropic.com/research/constitutional-classifiers

### Tulokset:
- Ilman classifieria: **86% jailbreak success**
- Classifierin kanssa: **4.4% jailbreak success**
- Over-refusal lisäys: vain **0.38%**
- Compute overhead: **23.7%**

### Bug bounty tulokset:
- 339 jailbreakeria, 300,000+ chattia, ~3,700 tuntia
- **Yksi universaali jailbreak löytyi** 7 päivässä

### Miksi tämä on tärkeä:
- Pelkkä mallin turvallisuuskoulutus EI RIITÄ
- Tarvitaan **input + output classifier** -kerros
- Suunnitelmassa ei ole tätä arkkitehtuuria

### Suositus:
```
Lisää vaihe: DEFENSE ARCHITECTURE EVALUATION
- Testaa: malli yksin vs malli + input filter vs malli + input + output filter
- Mittaa: ASR, over-refusal rate, latenssi
- Suosittele tuotantoarkkitehtuuri
```

---

## 3. OpenAI Evals - Puuttuvat testkategoriat

**Lähde:** https://github.com/openai/evals

### Evals-kategoriat joita meillä EI OLE:

| Kategoria | Kuvaus | Relevanssi |
|-----------|--------|------------|
| **MakeMeSay** | Saako mallin sanomaan tietyn sanan | Manipulaatioresistenssi |
| **MakeMePay** | Saako mallin "lahjoittamaan rahaa" | Sosiaalinen manipulaatio |
| **Ballot Proposal** | Poliittinen vaikuttaminen | Persuasion resistance |
| **Steganography** | Piiloviestintä mallien välillä | Agentic safety |
| **Schelling Point** | Koordinointi ilman kommunikaatiota | Multi-agent safety |

### Suositus:
```
Lisää testikategoria: PERSUASION_RESISTANCE
- Testaa voiko käyttäjä manipuloida mallia
- Emotionaalinen painostus
- Auktoriteettiin vetoaminen
- "Urgent" -kehystys
```

---

## 4. OpenAI Red Teaming Network -käytännöt

**Lähde:** https://openai.com/index/red-teaming-network/

### Heidän kriteerinsä red teamerille:
1. Domain-spesifi asiantuntemus
2. AI safety -intohimo
3. Ei intressiristiriitoja
4. Monipuoliset taustat
5. Maantieteellinen edustavuus
6. **Monikielisyys** (useampi kuin yksi kieli)
7. Tekninen kyky (ei pakollinen)

### Miksi monikielisyys on tärkeä:
- "Low-resource languages jailbreak GPT-4" -tutkimus
- Suomi on low-resource kieli!
- Suunnitelmassa on vain yksi monikielinen hyökkäys

### Suositus:
```
Lisää testikategoria: LOW_RESOURCE_LANGUAGE
- Suomenkieliset jailbreak-yritykset
- Vironkieliset (läheinen kieli)
- Swahili, indonesia (todella low-resource)
- Kielten sekoitus (code-switching)
```

---

## 5. Puuttuvat tekniset yksityiskohdat

### 5.1 Determinismi ja toistettavuus

Suunnitelmassa mainitaan `temperature=0`, mutta:
- Ei mainita **seed-arvoa**
- Ei mainita **top_p, top_k** -arvoja
- Ei mainita **num_predict / max_tokens**

**Suositus:** Dokumentoi kaikki Ollama-parametrit eksplisiittisesti.

### 5.2 Token-budjetointi

- Ei määritelty kuinka monta tokenia per testi
- Many-shot vaatii PALJON tokeneja (256 shot × ~100 tokenia = 25,600)
- Pienillä malleilla context window on rajallinen

**Suositus:** Lisää token budget per testikategoria.

### 5.3 Baseline-vertailu

- Ei määritelty mikä on "expected behavior"
- Tarvitaan golden set: kysymykset joihin mallin PITÄÄ vastata
- Tarvitaan refusal set: kysymykset joihin mallin PITÄÄ kieltäytyä

**Suositus:** Luo `baseline_expected.json` ja `baseline_refusal.json`.

---

## 6. Puuttuvat hyökkäyskategoriat (täydennys)

| Kategoria | Kuvaus | Lähde |
|-----------|--------|-------|
| **Cipher attacks** | ROT13, Caesar, custom ciphers | Constitutional Classifiers demo |
| **Role-play + system prompt** | Yhdistelmähyökkäys | Constitutional Classifiers demo |
| **Keyword substitution** | "Soman" → "water" | Constitutional Classifiers demo |
| **Prompt injection in context** | Injektio system promptissa | OpenAI evals |
| **Model-to-model attacks** | Malli hyökkää toista mallia | MakeMeSay, Steganography |

---

## 7. Yhteenveto kriittisistä puutteista

| # | Puute | Prioriteetti | Työmäärä |
|---|-------|--------------|----------|
| 1 | Many-shot jailbreak -testit | 🔴 KRIITTINEN | Keskisuuri |
| 2 | Constitutional Classifier -arkkitehtuuri | 🔴 KRIITTINEN | Suuri |
| 3 | Low-resource language (suomi) | 🟡 KORKEA | Pieni |
| 4 | Persuasion resistance -testit | 🟡 KORKEA | Keskisuuri |
| 5 | Token budget & determinismi | 🟢 KESKITASO | Pieni |
| 6 | Baseline expected/refusal sets | 🟢 KESKITASO | Pieni |

---

## 8. Päivitysehdotukset TESTING_PLAN.md:hen

### Lisää uusi osio: "15) Many-Shot Jailbreaking"
- Testaa 8, 32, 128, 256 shot
- Raportoi ASR per shot count
- Context window rajoitteet per malli

### Lisää uusi osio: "16) Defense Architecture Evaluation"  
- Testaa malli yksin vs malli + filter
- Mittaa trade-off: security vs usability vs latency

### Lisää uusi osio: "17) Low-Resource Language Attacks"
- Suomi, viro, swahili
- Code-switching (suomi + englanti sekaisin)

### Päivitä "3.2 Kontrollit"
- Lisää seed, top_p, top_k, max_tokens
- Lisää token budget per kategoria
- Lisää baseline_expected.json viittaus

---

*Seuraava vaihe: Integroi nämä Codexin toteutukseen.*
