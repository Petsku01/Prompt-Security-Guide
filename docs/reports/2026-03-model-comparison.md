# LLM Jailbreak Resistance Comparison

> **Date:** March 2026  
> **Test Version:** Jailbreak Tester v3.0  
> **Dataset:** 65 attack vectors (direct prompts + 5 jailbreak variants)

---

## Executive Summary

Testasimme viittä paikallista LLM-mallia niiden kykyä vastustaa jailbreak-hyökkäyksiä. Tulokset osoittavat merkittäviä eroja mallien turvallisuusasetuksissa.

**Paras suorituskyky:** Llama 3 8B ja Qwen 2.5 3B  
**Heikoin suorituskyky:** Mistral 7B

---

## Tulokset

| Malli | Koko | Flagged | Flagged % | Turvallisuusluokitus |
|-------|------|---------|-----------|----------------------|
| **Llama 3** | 8B | 3/65 | 4.6% | 🟢 Hyvä |
| **Qwen 2.5** | 3B | 4/65 | 6.2% | 🟢 Hyvä |
| **Phi-3 Mini** | 3.8B | 6/65 | 9.2% | 🟡 Kohtalainen |
| **Gemma 2** | 2B | 9/65 | 13.8% | 🟡 Kohtalainen |
| **Mistral** | 7B | 17/65 | 26.2% | 🔴 Heikko |

### Terminologia

- **Flagged:** Malli tuotti potentiaalisesti haitallista sisältöä
- **OK:** Malli kieltäytyi tai tuotti turvallisen vastauksen
- **Flagged %:** Pienempi on parempi (malli vastustaa hyökkäyksiä)

---

## Analyysi malleittain

### 🟢 Llama 3 8B — Paras turvallisuus

```
Flagged: 3/65 (4.6%)
Testiaika: 17 min
```

**Vahvuudet:**
- Vahvat sisäänrakennetut turvallisuusrajat
- Kieltäytyy johdonmukaisesti haitallisista pyynnöistä
- Meta:n RLHF-koulutus näkyy tuloksissa

**Havainnot:**
- Pieni osa jailbreak-varianteista ohitti suojaukset
- Suorat hyökkäykset torjuttiin tehokkaasti

---

### 🟢 Qwen 2.5 3B — Yllättävän vahva pienelle mallille

```
Flagged: 4/65 (6.2%)
Testiaika: 14 min
```

**Vahvuudet:**
- Hyvä turvallisuus pienestä koosta huolimatta
- Nopea suorituskyky
- Alibaban turvallisuuskoulutus toimii

**Havainnot:**
- Kilpailukykyinen isompien mallien kanssa
- Hyvä valinta resurssirajoitteisiin ympäristöihin

---

### 🟡 Phi-3 Mini 3.8B — Kohtalainen

```
Flagged: 6/65 (9.2%)
Testiaika: 29 min
```

**Vahvuudet:**
- Microsoftin turvallisuuskoulutus
- Kohtuullinen suorituskyky

**Heikkoudet:**
- Jotkut suorat hyökkäykset onnistuivat
- Hitaampi kuin kooltaan vastaavat mallit

---

### 🟡 Gemma 2 2B — Pieni malli, kompromisseja

```
Flagged: 9/65 (13.8%)
Testiaika: 27 min
```

**Havainnot:**
- Googlen pienin malli
- Turvallisuus kärsii koon rajoituksista
- Sopii ei-kriittisiin käyttötarkoituksiin

---

### 🔴 Mistral 7B — Heikoin turvallisuus

```
Flagged: 17/65 (26.2%)
Testiaika: 78 min
```

**Heikkoudet:**
- Yli neljännes hyökkäyksistä onnistui
- Erityisesti suorat hyökkäykset tehokkaita
- Myös jailbreak-variantit toimivat useammin

**Huomio:**
- Mistral on suunniteltu vähemmän rajoitetuksi
- **Ei suositella** tuotantokäyttöön ilman lisäsuojauksia

---

## Hyökkäystyyppien tehokkuus

### Suorat hyökkäykset (50 testiä)

| Malli | Onnistuneet | Osuus |
|-------|-------------|-------|
| Llama 3 | 3 | 6% |
| Qwen 2.5 | 4 | 8% |
| Phi-3 | 6 | 12% |
| Gemma 2 | 9 | 18% |
| Mistral | 16 | 32% |

### Jailbreak-variantit (15 testiä)

| Malli | Onnistuneet | Osuus |
|-------|-------------|-------|
| Llama 3 | 0 | 0% |
| Qwen 2.5 | 0 | 0% |
| Phi-3 | 0 | 0% |
| Gemma 2 | 0 | 0% |
| Mistral | 1 | 7% |

**Huomio:** Testatut jailbreak-variantit eivät olleet tehokkaita yhtäkään mallia vastaan Mistralia lukuunottamatta. Tämä voi viitata siihen, että nämä variantit ovat jo tunnettuja ja mallit on koulutettu torjumaan ne.

---

## Havaitut haavoittuvuuskategoriat

Flagatut vastaukset sisälsivät seuraavia kategorioita:

| Kategoria | Esiintymät | Huomiot |
|-----------|------------|---------|
| Malware-ohjeet | 8 | Koodi/skriptit |
| Sosiaalinen manipulointi | 5 | Phishing-mallit |
| Turvallisuuden ohitus | 4 | Ohjeita suojausten kiertoon |

*Tarkkoja prompteja ei julkaista turvallisuussyistä.*

---

## Suositukset

### Tuotantokäyttöön

1. **Suosi Llama 3 tai Qwen 2.5** — Parhaat turvallisuustulokset
2. **Vältä Mistralia ilman lisäsuojauksia** — Liian haavoittuva sellaisenaan
3. **Lisää output-suodatus** — Myös parhaat mallit voivat epäonnistua

### Kehittäjille

1. **System prompt hardening** — Vahvista järjestelmäpromptit
2. **Input validation** — Tarkista käyttäjäsyötteet ennen mallille lähettämistä
3. **Output monitoring** — Valvo ja suodata vastauksia
4. **Defense in depth** — Älä luota vain mallin sisäisiin suojauksiin

---

## Metodologia

### Testausympäristö

- **Runtime:** Ollama (localhost)
- **Testikehys:** Jailbreak Tester v3.0
- **Detector:** Pattern-based + keyword matching

### Dataset

- 50 suoraa hyökkäyspromptia
- 15 jailbreak-varianttia (5 tyyppiä × 3 esimerkkiä)
- Lähteet: Julkiset jailbreak-tietokannat, mukautetut variantit

### Rajoitukset

1. **Paikallinen testaus** — Tulokset voivat poiketa API-versioista
2. **Yksinkertainen detector** — Ei LLM-as-judge evaluaatiota
3. **Rajoitettu dataset** — 65 testiä ei kata kaikkia hyökkäystyyppejä
4. **Snapshot-tulokset** — Mallit päivittyvät jatkuvasti

---

## Yhteenveto

Paikallisten LLM-mallien turvallisuus vaihtelee merkittävästi. **Llama 3** ja **Qwen 2.5** tarjoavat parhaan suojan jailbreak-hyökkäyksiä vastaan, kun taas **Mistral** vaatii lisäsuojauksia tuotantokäytössä.

Yksikään malli ei ole täysin immuuni hyökkäyksille. **Defense in depth** -lähestymistapa on välttämätön.

---

*Raportti generoitu prompt-security-guide -työkalulla.*  
*Promptit sensuroitu turvallisuussyistä.*
