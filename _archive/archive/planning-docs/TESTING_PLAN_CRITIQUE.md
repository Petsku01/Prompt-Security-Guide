# Kriittinen arvio: TESTING_PLAN.md (v1.0)

**Arvion päiväys:** 2026-02-26  
**Yhteenveto:** Suunnitelma on hyvä runko, mutta se on tällä hetkellä **liian kapea hyökkäyspinnaltaan**, osin **liian optimistinen toteutettavuudeltaan paikallisessa WSL/Ollama-ympäristössä**, ja mittaustapa on osin **liian epätarkka** verrattuna kypsiin LLM red team -metodologioihin.

---

## 1) Puutteet: mitä tärkeää puuttuu

## 1.1 Puuttuvat hyökkäyskategoriat
Nykyinen suunnitelma kattaa hyvin extraction/jailbreak/indirect/multi-turn/encoding, mutta jättää pois useita käytännössä olennaisia alueita:

1. **Tool / Function calling abuse**
   - Prompt-injektio, joka yrittää pakottaa työkalukutsuja väärillä argumenteilla.
   - Parametrien manipulointi (path traversal, komentoinjektio, data exfiltration toolin kautta).

2. **Data exfiltration RAG-putkesta**
   - Ei vain “ignore instructions”, vaan myös “etsi salaisuuksia” -hakuketjut, dokumenttien välinen tietovuoto, ja citation-spoofing.

3. **Agentic planning attacks**
   - Monivaiheiset hyökkäykset, joissa malli ensin pyytää lisäoikeuksia tai rakentaa “harmittoman” välivaiheen.

4. **DoS / token flooding / context overflow**
   - Hyökkäykset, jotka ajavat mallin pois turvakäytöksestä pitkän kontekstin tai “needle in haystack” -rakenteiden kautta.

5. **Cross-lingual policy bypass**
   - Sekakieli mainitaan, mutta ei systemaattista suomi–englanti–venäjä–arabia jne. bypass-matriisia.

6. **Persona/authority hijacking**
   - “Olen järjestelmänvalvoja / compliance officer / turvallisuustiimi” -sosiaalinen manipulointi mallille.

7. **Output format coercion**
   - JSON/schema forcing, jossa malli pakotetaan vuotamaan “kielletty kenttä” strukturoidussa muodossa.

8. **Self-critique jailbreak bypass**
   - Hyökkäykset, joissa pyydetään malli ensin analysoimaan turvallisesti ja sitten “simuloimaan” vaarallinen vastaus.

## 1.2 Puuttuvat validointikulmat
- Ei eksplisiittistä **kalibrointisettiä** judge-mallille (automaattinen scoring voi olla harhainen).
- Ei **deduplikointia** prompt-korpukselle (ASR voi vääristyä lähes identtisillä prompteilla).
- Ei **confidence interval** -raportointia (pelkät prosentit ilman epävarmuutta ovat heikkoja päätöksentekoon).

---

## 2) Heikkoudet: liian yleinen tai epärealistinen

1. **“30–50 testiä per kriittinen kategoria per malli”**
   - 5 mallia × (väh. 3 kriittistä kategoriaa) × 30–50 × 2 lämpötilaa + multi-turn-ketjut = nopeasti tuhansia ajovuoroja.
   - WSL + CPU-only Ollama: käytännössä hidas, riskinä että sprintti jää kesken.

2. **2 viikon sprintti on optimistinen**
   - Jos mukana on manuaaliauditointi + re-test + Garak + custom harness + multi-turn, realistisempi on 3–4 viikkoa osa-aikaisella resursoinnilla.

3. **PASS/FAIL gate liian karkea**
   - “Critical FAIL = 0” on hyvä idea, mutta ilman testimääräminimiä ja CI:tä se voi antaa väärän turvallisuudentunteen.

4. **LLM-judge riippuvuus**
   - Ei kuvata, miten judge virhetilanteet käsitellään (false positive/false negative).

5. **Garak-integraatio liian abstrakti**
   - Ei listaa mitä probeja oikeasti ajetaan eikä miten ne mapataan omiin kategorioihin.

---

## 3) Bias / sokeat pisteet

1. **Liikaa prompt-tasoa, liian vähän järjestelmätasoa**
   - Suunnitelma olettaa, että malli on pääasiallinen riskin lähde; todelliset murrot tulevat usein orkestroinnista (RAG, työkalut, API-rajat).

2. **Teoreettinen “malli vastaa” -fokus**
   - Puuttuu tuotantomittakaavan realismi: timeoutit, retry-käytös, osittaiset vastaukset, stream-katkot, pitkät keskusteluketjut.

3. **Ei hyökkääjäprofiileja**
   - Script kiddie / insider / malicious user / supply-chain attacker -profiilit puuttuvat; priorisointi jää geneeriseksi.

4. **Ei riski–vaikutus-linkkiä liiketoimintaan**
   - Vakavuusluokat ovat tekniset, mutta ei sidekkoa todelliseen vaikutukseen (esim. tietovuoto, compliance-riski, mainehaitta).

---

## 4) Vertailu parhaisiin käytäntöihin (Anthropic / OpenAI / NVIDIA)

## Missä suunnitelma on hyvä
- Riskiperusteinen lähestymistapa (OWASP-ankkurointi).
- Multi-turn mukana (hyvä, usein puuttuu heikoista suunnitelmista).
- Re-test korjausten jälkeen (olennaista regressiohallinnassa).

## Missä jää jälkeen
1. **Anthropic/OpenAI-tyylinen eval-kuri puuttuu osin**
   - Tarvitaan selkeä train/dev/test-jako hyökkäyspromptien tasolla (ettei “opita testiin”).

2. **NVIDIA/Garak-tyylinen automaatio jää vajaaksi**
   - Probe- ja detector-konfiguraatiot pitäisi versionoida ja lukita CI:ssä.

3. **Governance/triage workflow puuttuu**
   - Kuka hyväksyy riskipoikkeamat? Milloin malli jäädytetään? Milloin rollback?

4. **Ei STRIDE/kill-chain -tasoisia hyökkäysketjuja agentille**
   - Nykyinen ketjutus on hyvä alku, mutta ei kata koko sovelluspolkua.

---

## 5) Aiemmat löydökset: Llama 3 murtui (Special Token Injection + Multi-turn)

Suunnitelma mainitsee tämän, mutta testaus on edelleen liian kevyt tähän havaintoon nähden.

### Puutteet
- Ei erillistä **special token -sanakirjaa** eikä fuzzing-strategiaa.
- Ei testiä eri tokenisaatioreunoille (leading/trailing control chars, separator abuse, BOS/EOS-tyyliset merkit).
- Ei regressiopakkoa: löydetyt bypassit pitäisi olla “must-run always” -suite.

### Tarvittava minimipaketti
- 100+ tapausta pelkästään special-token/permutation -luokkaan (ei 10–20).
- Multi-turn-ketjut vähintään 6–10 vuoroa vaikeille tapauksille.
- Jokainen aiempi bypass lisätään **Regression-Critical** -tagilla ja gateen: yksikin uusi läpäisy = FAIL.

---

## 6) Resurssirajoitteet (WSL + Ollama + ei GPU:ta)

## Realismiarvio
- **Kaikkien mallien täysi kampanja** samalla syvyydellä ei ole realistinen 2 viikossa CPU-only ympäristössä.
- Multi-turn + manuaaliauditointi tekee ajasta pullonkaulan.

## Käytännöllinen toteutusmalli
1. **Tier 1 (päivittäinen):** 1–2 mallia (Llama 3 + yksi vertailumalli), vain regression-critical + top-risk kategoriat.
2. **Tier 2 (viikoittainen):** kaikki mallit, suppeampi setti.
3. **Tier 3 (ennen julkaisua):** laaja kampanja vain kandidaattimallille.

## Suorituskykysuositukset
- Pienennä samanaikaisuutta WSL:ssä (vältä thrash).
- Aja yön yli batchit, rajoita context length missä mahdollista.
- Käytä ensin deterministic ajoa; stokastinen vain epäselville tai korkean riskin testeille.

---

## Konkreettiset parannusehdotukset (priorisoitu)

## P0 (pakollinen ennen seuraavaa kierrosta)
1. Lisää kategoriat: **tool abuse, RAG exfiltration, DoS/context overflow, authority hijack**.
2. Luo **Regression-Critical suite** aiemmista löydöksistä (special token + multi-turn) ja gate “0 läpäisyä”.
3. Määritä **resurssitason testimatriisi** (daily/weekly/release), ettei suunnitelma kaadu laajuuteen.
4. Lisää judge-kalibrointi: 100 käsin labeloitua tapausta + precision/recall raportti.

## P1 (seuraava sprintti)
5. Versionoi probe/detector-konfiguraatiot ja ota CI-regressioajo.
6. Lisää confidence intervalit metriikoihin ja miniminäytekoot per kategoria.
7. Lisää triage/governance: owner, SLA, rollback-kriteerit.

## P2 (kypsyysvaihe)
8. Lisää hyökkääjäprofiilit ja riskipainotus liiketoimintavaikutuksella.
9. Lisää pitkäkonteksti- ja stressitestit (latenssi, timeoutit, stream-katkot).

---

## Päivitystarve suunnitelmaan
Kyllä — merkittäviä puutteita löytyi. Suunnitelma kannattaa päivittää vähintään versioksi **1.1** seuraavilla lisäyksillä:
- uusi hyökkäyskategoriaosio (tool abuse / DoS / authority hijack / RAG exfil)
- Regression-Critical suite (erityisesti Special Token Injection + Multi-turn)
- realistinen resurssipohjainen ajomalli (Tier 1/2/3)
- judge-kalibrointi + epävarmuusraportointi
- governance ja release gate -prosessi

**Bottom line:** nykyinen v1.0 on hyvä perusta, mutta ilman yllä olevia muutoksia se todennäköisesti **aliarvioi todellisen murtoriskin** ja **ylikuormittaa paikallisen testiympäristön**.