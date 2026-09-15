# Hyökkäyslähdekartta — tarkistetut lähteet (2026-09-15)

Kaikki varmennettu suoraan GitHub/HF-API:sta tässä sessiossa. Jaoteltu PSG:n
kolmen kerroksen tarpeisiin: profiilit (mallikohtaiset), katalogi (koodi),
vendor (julkaisijakohtaiset).

## 1. Standardoidut benchmark-korpukset (peer-reviewed, tuoreet)

- **JailbreakBench/JBB-Behaviors** (671★, push 2025-04) — NeurIPS 2024
  - 200 harmful behaviors + 100 benign, standardoitu arviointisetti
  - HF: datasets/JailbreakBench/JBB-Behaviors (61k latausta, 125 likea)
  - raw: .../resolve/main/data/harmful-behaviors.csv (haettu OK 200)
  - Käyttö: PSG:n benign/harmful-järjestelmätestin runko + judge-kalibrointi

- **verazuo/jailbreak_llms** (3813★, push 2024-12) — ChatGPT:ltä kerätyt
  ~15 000 todellista jailbreak-yritystä + 3 000 luonnollista kysymystä
  (Tianxiang Zuo et al.); aidot käyttäjägeneroidut templatet, ei synteettisiä
  - Käyttö: profiilitemplatejen validointi — mitkä template-alkuiset hyökkäykset
    ihmiset oikeasti kirjoittavat

- **TrustAIRLab/in-the-wild-jailbreak-prompts** — HF-datasetti, 2 aikaleimattua
  snapshotia (2023-05, 2023-12): todelliset netistä kerätyt jailbreakit +
  regular-sarja vertailuun (MIT-lisenssi, tiedostot varmistettu olemassa)

## 2. Vastaanuttavat red-team-frameworkit (ajovalmiit PSG:en)

- **NVIDIA/garak** (9238★, push 2026-09-09 — viikolla!) — LLM-sykkeen skanneri:
  15+ plugin-luokkaa, harm-, dan-, encoding-hyökkäysmoduulit. Aktiivisin
  standardi. Suora integraatioehdotus: garak-probes → PSG-adapteri
- **Azure/PyRIT** (Microsoftin AI Risk Iteration Toolkit) — automaattinen
  adversarial-pipeline, multi-turn-orkestrointi sisäänrakennettuna
  (ratkaisee PSG:n single-turn-rajoituksen evoflint-luokalle)
- **confident-ai/deepteam** (2806★, push 2026-08) — red-team-alusta 10+
  vulnerabiliteettityypillä; modernein API
- **EasyJailbreak/EasyJailbreak** (909★, push 2026-09) — 11 hyökkäysmetodia
  modulaarisesti (GCG, AutoDAN, PAIR,_cipher, multilingual jne.) — täsmää
  suoraan PSG:n tekniikkaluokkiin
- **meta-llama/PurpleLlama** (4394★, push 2026-08) — Llama Guard 3 + CyberSec
  Eval -korpus: puolustuspuolen standardi

## 3. Agentti/MCP-hyökkäyskorpukset (uusi hyökkäyspinta)

- **ethz-spylab/agentdojo** (822★, push 2026-06) — agenttien injektiobenchmark:
  workspace/slack/travel/trading-ympäristöt, utility-scaling-hyökkäykset
- **Promptfoo LM Security DB** (985 findings, 1123 mallia, päivitetty 9/9/2026)
  — promptfoo.dev/lm-security-db — jo käytössä PSG-lähteenä; API saatavilla
- Dreadnode CTF-study (arXiv 2607.21763) + METR ExploitGym — goal reframing,
  reward hacking -korpukset

## 4. Vendor/lähteet jo käytössä

- **elder-plinius/CL4R1T4S** (49835★, push 2026-09-10 — tuore!) — system
  promptien vuodet (GPT, Claude, Gemini, Grok...) — profiilien rakennusaineisto
- **elder-plinius/L1B3RT4S** — vendor-jailbreakit (PSG:n vendor-kerros)

## Suositeltu integrointijärjestys PSG:en

1. JBB-Behaviors harmful-behaviors.csv → standardi-scan-sarja (100 behaviors)
   — antaa vertailukelpoisen ASR-mittarin muihin julkaisuihin
2. garak-plugin-adapteri → 15+ hyökkäysperhettä yhdellä istulla
3. in-the-wild-katalogi → katalogin deduplitaatio + kattavuusmitta
4. agentdojo → agentti-injektio-kerros (PSG:n seuraava arkkitehtuuripäivitys)
5. EasyJailbreak-metodit → tekniikkaluokkien toteutusviitteet