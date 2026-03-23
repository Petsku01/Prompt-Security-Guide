# WEB_RESEARCH_FINDINGS.md

**Päiväys:** 2026-02-26  
**Kohde:** `/home/ette/.openclaw/workspace/prompt-security-guide/TESTING_PLAN.md`  
**Tutkimustehtävä:** LLM-turvallisuustestauksen best practices lähteistä Garak, OWASP GenAI, Anthropic Research, arXiv (2024–2026), JailbreakBench, HarmBench.

---

## 1) Mitä lähteistä löytyi (metodologiat ja käytännöt)

## 1.1 NVIDIA Garak
**Lähteet:**
- https://github.com/NVIDIA/garak
- https://reference.garak.ai/en/latest/

**Keskeiset havainnot:**
- Garak on **LLM vulnerability scanner**, joka käyttää laajaa probe/detector-plugin -mallia.
- Soveltuu erityisesti:
  - baseline-skannaukseen
  - regressioseurantaan
  - CI-ajoon
- Tuottaa probe-kohtaisia fail-rateja ja JSONL-lokeja, joita voi analysoida jälkikäteen.
- Käytännön suositus: Garak toimii hyvin “nmap-tyylisenä” perusskannerina, mutta ei yksin kata kaikkia ympäristökohtaisia hyökkäysketjuja (esim. monivuoroinen, RAG-spesifi hyökkäyslogiikka).

## 1.2 OWASP GenAI Security Project
**Lähteet:**
- https://genai.owasp.org
- https://genai.owasp.org/llm-top-10/
- https://genai.owasp.org/resource/owasp-top-10-for-llm-applications-2025/

**Keskeiset havainnot:**
- OWASP painottaa riskien jäsentelyä koko GenAI-elinkaaren yli (ei vain prompt-taso).
- 2025-päivityksissä painottuu:
  - agentic-järjestelmät
  - työkalukutsujen väärinkäyttö (excessive agency / insecure tool use)
  - data- ja mallitoimitusketjun turvallisuus
- Käytännön implication testaukseen: testikatalogi pitää mapata suoraan riskiluokkiin + kontrollien omistajuus (owner) määriteltävä.

## 1.3 Anthropic Research
**Lähteet:**
- https://www.anthropic.com/research
- https://www.anthropic.com/research/many-shot-jailbreaking
- https://www.anthropic.com/research/constitutional-classifiers
- Paper-linkki sivulta: https://arxiv.org/abs/2501.18837

**Keskeiset havainnot:**
- **Many-shot jailbreaking**: pitkä konteksti itsessään avaa uuden hyökkäyspinnan; attack success rate kasvaa shot-määrän kasvaessa.
- **Constitutional Classifiers**:
  - yhdistetty input+output-luokittelijakerros voi leikata jailbreak-ASR:ää voimakkaasti
  - mutta arvioinnissa pitää aina mitata myös over-refusal ja compute overhead
- Käytännön implication: turvallisuustestiin tarvitaan erikseen long-context-kampanja sekä defense trade-off -mittaus (turvallisuus vs käytettävyys/kustannus).

## 1.4 arXiv (2024–2026)
**Lähdehaun URL:**
- https://arxiv.org/search/?query=LLM+security+jailbreak+benchmark&searchtype=all&abstracts=show&order=-announced_date_first&size=25

**Keskeiset havainnot (hakutulostrendit):**
- 2025–2026 julkaisuissa korostuvat:
  - multi-turn jailbreakit
  - domain-spesifit turvallisuusbenchmarkit (esim. med/finance)
  - jailbreak detection -menetelmät
  - multimodaaliset hyökkäykset
- Yleinen trendi: pelkkä single-turn tekstipromptaus ei enää riitä kattavaan evaluaatioon.

## 1.5 JailbreakBench
**Lähde:**
- https://github.com/jailbreakbench/jailbreakbench

**Keskeiset havainnot:**
- Benchmark tarjoaa **JBB-Behaviors** -datasetin (100 harmful + 100 benign).
- Sisältää myös leaderboards- ja artifact-ajattelun (hyökkäysstringit versionoituna).
- Hyvä käytäntö: raportoida samanaikaisesti
  - harmful ASR
  - benign false refusal
  - query budget (montako yritystä jailbreakiin vaaditaan)

## 1.6 HarmBench
**Lähteet:**
- https://harmbench.org (niukka sisältö julkisivulla)
- https://github.com/centerforaisafety/HarmBench
- Paper: https://arxiv.org/abs/2402.04249

**Keskeiset havainnot:**
- Standardoi evaluaation 3-vaiheiseksi pipelineksi:
  1. test case generation
  2. completion generation
  3. completion evaluation
- Korostaa hyökkäysten ja puolustusten yhteiskehitystä sekä vertailtavaa, toistettavaa runkoa.
- Tarjoaa classifier-komponentteja ja useita red teaming -menetelmiä yhden rungon alla.

---

## 2) Vertailu nykyiseen suunnitelmaan (v1.1) — puutteet

Nykyinen suunnitelma oli jo vahva (riskiperusteinen, gate-malli, regressiot, multi-turn), mutta web-lähteiden perusteella löytyi seuraavat konkreettiset puutteet:

1. **Long-context jailbreakit puuttuivat omana pakollisena kategoriana**  
   - Many-shot-ilmiö oli implisiittisesti mukana context overflow -kohdassa, mutta ei selkeää ASR-vs-context -testiprotokollaa.

2. **OWASP 2025/agentic-kattavuus ei ollut eksplisiittisesti mapattu**  
   - Tool abuse / excessive agency / supply-chain -riskit eivät olleet selkeästi riski→testi→kontrolli→owner -taulussa.

3. **Benchmark-standardointi puutteellinen**  
   - JailbreakBench/HarmBench ei ollut pakollinen osa regressiopakettia; oma korpus painottui.

4. **Pipeline-rakenne ei ollut formalisoitu HarmBench-tyyliin**  
   - Vaiheistus oli olemassa, mutta ei eksplisiittistä 3-step dataflowta (generation/completions/evaluation).

5. **Defense trade-off -mittaus puutteellinen**  
   - Puuttui systemaattinen vertailu “malli vs malli+input-filter vs malli+input+output-filter”.

6. **Tilastollinen raportointi benchmark-tasolle oli liian kevyt**  
   - CI oli mainittu osin, mutta ei pakollista bootstrap/replikaatio-vaatimusta kriittisiin päätöksiin.

7. **Garakin tulosten operationalisointi**  
   - Garak oli mukana, mutta probe-failien automaattinen siirto regression_critical-listaan puuttui.

---

## 3) Tehdyt parannukset TESTING_PLAN.md:hen

Päivitin suunnitelman versioon **v1.2** ja lisäsin uuden osion:

- **“14) Päivitykset v1.2 (web-lähteisiin perustuvat parannukset)”**

Lisäykset:
1. OWASP 2025 + agentic Top 10 -kartoitus pakolliseksi (riski→testi→kontrolli→owner)
2. Long-context many-shot -testit pakolliseksi (8/32/128/max-shot tasot + ASR-käyrä)
3. Input/output-luokittelijakokoonpanojen vertailu (ASR, over-refusal, latenssi/kustannus)
4. JailbreakBench + HarmBench -setit osaksi vakio-regressiota
5. HarmBench-tyylinen 3-vaiheinen pipeline eksplisiittiseksi
6. Tilastollinen raportointi: 95% CI + väh. 3 replikaatiota kriittisissä kategorioissa
7. Garak-ajojen rooli täsmennetty (release + viikkorytmi, probe-fail -> regression_critical)

---

## 4) Johtopäätös

Suunnitelma oli jo tuotantokelpoinen red team -runko, mutta web-lähteiden perusteella sen kypsyystasoa nostettiin erityisesti neljällä alueella:

- **long-context jailbreak realismi**
- **agentic/tool-riskien explicit coverage**
- **benchmark-standardointi (JBB + HarmBench)**
- **tilastollisesti vahvempi päätöksenteko**

Tämän jälkeen testausrunko on selvästi lähempänä nykyistä (2025–2026) LLM-safety-evaluation best practice -tasoa.

---

## 5) Huomio tutkimuksen rajoitteista

- `web_search`-työkalua ei voitu käyttää (Brave API key puuttui), joten arXiv-katsaus tehtiin suoran arXiv-haun kautta.
- Harmbench.org etusivu sisälsi vähän teknistä sisältöä; metodologiset yksityiskohdat haettiin HarmBench GitHub-reposta ja paperiviitteestä.
