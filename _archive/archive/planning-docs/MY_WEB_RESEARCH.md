# Omat web-tutkimustulokset - LLM Security Testing

**Päiväys:** 2026-02-26  
**Tutkija:** Kuu

---

## 1. JailbreakBench (NeurIPS 2024)

**Lähde:** https://github.com/jailbreakbench/jailbreakbench

### Mitä se on:
- **Standardisoitu benchmark** jailbreaking-hyökkäysten arviointiin
- **200 käyttäytymistä** (100 harmful + 100 benign)
- Valmiit **jailbreak-stringit** eri algoritmeille
- **Leaderboard** hyökkäysten ja puolustusten vertailuun

### Keskeiset metodit:
- **PAIR** (Prompt Automatic Iterative Refinement) - musta laatikko
- **GCG** (Greedy Coordinate Gradient) - valkoinen laatikko
- **AutoDAN** - automaattinen DAN-generointi
- **TAP** (Tree of Attacks with Pruning)

### Puolustukset:
- **SmoothLLM** - satunnainen perturbatio
- **Perplexity filtering** - epänormaalit promptit
- **Synonym substitution**

### Miten voimme käyttää:
```python
pip install jailbreakbench
import jailbreakbench as jbb
dataset = jbb.read_dataset()  # 100 harmful behaviors
```

**Suositus:** Käytä JBB-Behaviors -datasettia testien pohjana!

---

## 2. HarmBench (Center for AI Safety)

**Lähde:** https://github.com/centerforaisafety/HarmBench

### Mitä se on:
- **Standardisoitu evaluointiframework** red teamingille
- Testattu **33 LLM:ää** ja **18 red teaming metodia**
- Sisältää **classifier-mallit** jailbreak-tunnistukseen

### Classifier-mallit (KRIITTINEN):
- `cais/HarmBench-Llama-2-13b-cls` - standard & contextual
- `cais/HarmBench-Mistral-7b-val-cls` - validation classifier

### Pipeline:
1. Generate test cases
2. Generate completions  
3. Evaluate completions (classifier)

### Miten voimme käyttää:
- Käytä HarmBench-classifieria automatisoimaan "onko tämä jailbreak" -arviointi
- Parempi kuin regex/heuristiikka

**Suositus:** Integroi HarmBench-classifier testipipelineen!

---

## 3. llmsecurity.net - Kattava linkkilista

**Lähde:** https://llmsecurity.net

### Hyökkäyskategoriat (täydellinen):

| Kategoria | Esimerkkejä |
|-----------|-------------|
| **Adversarial** | GCG, Universal Attacks, Bad Characters |
| **Backdoors & Poisoning** | BadPrompt, Hidden Killer, Instruction Tuning exploits |
| **Prompt Injection** | Indirect injection, Data exfiltration |
| **Jailbreaking** | AutoDAN, GPTFUZZER, Low-resource languages |
| **Data Extraction** | Training data extraction, Prompt extraction |
| **Escalation** | RCE via LLM, Docker escape |
| **Multimodal** | Image-to-prompt injection |

### Merkittävät paperit (🌶️ = must-read):
1. "Ignore Previous Prompt" (2022) - klassikko
2. "Not what you've signed up for" (2023) - indirect injection
3. "Universal and Transferable Adversarial Attacks" (2023) - GCG
4. "Low-Resource Languages Jailbreak GPT-4" (2023) - kielipohjainen
5. "AutoDAN" (2023) - automaattinen jailbreak-generointi

---

## 4. Anthropic Research

**Lähde:** https://www.anthropic.com/research

### Relevantit tiimit:
- **Alignment Team** - turvallisuusriskit ja mitigaatiot
- **Frontier Red Team** - biosecurity, cybersecurity, autonomous systems
- **Interpretability** - miten mallit toimivat sisäisesti

### Tuoreet julkaisut (2026):
- "Measuring AI agent autonomy in practice"
- "Claude's new constitution"
- "The assistant axis: situating and stabilizing LLM character"

---

## 5. NVIDIA Garak

**Lähde:** https://github.com/NVIDIA/garak

### Probes (hyökkäysmoduulit):
- `dan` - DAN-variantit
- `encoding` - Base64, ROT13, leetspeak
- `promptinject` - PromptInject framework
- `malwaregen` - haittakoodin generointi
- `leakreplay` - training data vuodot
- `gcg` - adversarial suffix
- `xss` - cross-site attacks

### Miten käyttää Ollaman kanssa:
```bash
garak --target_type rest --probes encoding,dan,promptinject
```

---

## 6. Yhteenveto - Mitä puuttuu suunnitelmastamme

### Puuttuvat metodologiat:

| Asia | Status | Toimenpide |
|------|--------|------------|
| JailbreakBench dataset | ❌ Puuttuu | Integroi 100 harmful behaviors |
| HarmBench classifier | ❌ Puuttuu | Korvaa regex-heuristiikka |
| GCG adversarial suffix | ❌ Puuttuu | Lisää valkoisen laatikon testit |
| Low-resource language attacks | ⚠️ Osittain | Lisää suomi, viro, swahili |
| Multimodal attacks | ❌ Puuttuu | Ei relevantti (teksti-only mallit) |
| AutoDAN | ❌ Puuttuu | Automaattinen jailbreak-generointi |

### Puuttuvat työkalut:

1. **LLM Judge** - käytä HarmBench-classifieria tai GPT-4 judgea
2. **Automated iteration** - PAIR/TAP -tyylinen iteratiivinen hyökkäys
3. **Statistical confidence** - bootstrap CI raportointi

---

## 7. Konkreettiset päivitysehdotukset

### Välitön (Tier 1):
1. Lataa JBB-Behaviors dataset (100 behaviors)
2. Integroi HarmBench-classifier tai käytä Ollama-pohjaista judgea
3. Lisää suomenkieliset hyökkäykset (low-resource language)

### Keskipitkä (Tier 2):
1. Implementoi PAIR-algoritmi (iteratiivinen black-box)
2. Lisää GCG-hyökkäykset (jos GPU käytettävissä)
3. Raportoi 95% CI kaikille metriikoille

### Pitkä (Tier 3):
1. Integroi Garak baseline-skannauksiin
2. Luo automaattinen regressiotesti CI/CD:hen
3. Julkaise tulokset JailbreakBench-leaderboardille

---

## 8. Tärkeimmät opit

> **"Jailbreaking is not a bug, it's a feature of how LLMs work."**

1. **Ei ole olemassa 100% turvallista mallia** - kaikki voidaan murtaa
2. **Defense-in-depth** - useita kerroksia (input filter + model + output filter)
3. **Continuous testing** - uusia hyökkäyksiä löydetään jatkuvasti
4. **Standardisoitu evaluointi** - JailbreakBench/HarmBench mahdollistaa vertailun

---

*Tutkimus valmis. Seuraava vaihe: Integroi löydökset TESTING_PLAN.md:hen.*
