# Plinyn Omat Sanat -- Miten Han Selittaa Tekniikoitaan

*Koottu 8.6.2026 -- Plinyn omista lahteista: README:t, PAPER.md, verkkosivut, akateemiset viittaukset*

---

## Kriittinen loydos: Pliny selittaa mekanismeja README- ja PAPER.md-tiedostoissaan

Toisin kuin oletimme, Pliny EI ole vain "99% intuitiota" -- han on kirjoittanut yksityiskohtaisia mekaniikkaselityksia suoraan tyokalujensa dokumentaatioon. Nama ovat hanen omia sanojaan, ei akateemikoiden tulkintoja.

---

## 1. OBLITERATUS README -- Plinyn yksityiskohtaisin mekaniikkaselitys

### 1.1 Ketjujen kartoitus ("Map the chains")

Plinyn omat sanat:
> "Ablation studies systematically knock out model components (layers, attention heads, FFN blocks, embedding dimensions) and measure what breaks. This reveals *where* the chains are anchored inside the transformer -- which circuits enforce refusal vs. which circuits carry knowledge and reasoning."

**Tama on ensimmainen kerta kun Pliny selittaa ablaation mekanismin tarkasti:** han ei sano "kokeile ja katso" -- han sanoo jarjestelmallisesti poistaa komponentteja ja mitata mita rikkoutuu. Tama on akateeminen metodologia.

### 1.2 Ketjujen rikkominen ("Break the chains")

> "Targeted obliteration extracts the refusal subspace from a model's weights using SVD decomposition, then surgically projects it out."

**Pliny kayttaa itse termia "surgically projects it out"** -- han ymmartaa etta projektiomekanismi on kirurginen, ei bruttaalinen. Tama ei ole intuitiivinen kasitys, vaan matemaattinen.

### 1.3 Ketjujen geometria ("Understand the geometry of the chains")

> "15 deep analysis modules go far beyond brute-force removal. They map the precise geometric structure of the guardrails: how many distinct refusal mechanisms exist, which layers enforce them, whether they're universal or model-specific, and how they'll try to self-repair after removal."

**Tama on Plinyn syvallisin mekaaninen selitys.** Han erottaa kolme kysymysta:
1. Kuinka monta erillista kieltaytymismekanismia on? (concept cone geometry)
2. Mitka kerrokset yllapitavat niita? (layer selection)
3. Yrittavatko ne korjata itsensa? (Ouroboros-effect)

### 1.4 Analyysiohjattu vapautus ("Let the analysis guide the liberation")

> "The `informed` method closes the loop: analysis modules run *during* obliteration to auto-configure every decision."

**Sulkusilmukka:** analyysi ajetaan kesken poiston, ja tuloksetsaadavat poiston parametreja reaaliajassa. Tama ei ole "kokeile ja toivo" -- se on adaptiivinen kontrolli.

---

## 2. OBLITERATUS -- Uudet konseptit Plinyn omin sanoin

### 2.1 Ouroboros-efekti

> "Quantifies whether guardrails will self-repair after removal."

ja VERIFY-vaiheessa:

> "If the chains try to reassemble, additional targeted passes automatically fire at the compensating layers."

**Pliny selittaa mekanismin:** mallit voivat korjata kieltaytymisominaisuutensa osittaisista jaannoksista. OBLITERATUS havaitsee taman ja tekee ylimaaraisia kohdennettuja suorituksia kompensoiville kerroksille.

### 2.2 Alignment Imprint Detection

> "Fingerprints DPO vs RLHF vs CAI vs SFT from subspace geometry alone"

**Pliny vaittaa etta eri kohdistusmenetelmat jattavat erilaisia geometrisia sormenjalkia aktivaatioavaruuksessa.** Tama on vahva mekaaninen vaite: kohdistusmenetelman voi tunnistaa pelkasta geometriasta ilman metatietoja.

### 2.3 Concept Cone Geometry

> "Reveals whether 'refusal' is one mechanism or many -- so you choose the right approach"

**Tama kumoa yksinkertaisen "yksi suunta" -kasityksen.** Pliny sanoisi etta kieltaytyminen voi olla yksi suunta TAI moniulotteinen kartio, ja oikea lahestymistapa riippuu mallista.

### 2.4 Bias Term Projection

> "Removes guardrails from bias vectors, not just weights -- Other tools miss refusal signal in biases -- leaves refusal pathways partially active."

**Kriittinen mekaniikkaloydos:** muut tyokalut poistavat kieltaytymissignaalin vain painoista, jattaen bias-vektoreihin jaannoksia. OBLITERATUS kasittelee molemmat.

### 2.5 Iteratiivinen hiomisto

> "Re-probes after each pass to catch rotated residual guardrails -- Single-pass methods miss directions that rotate into adjacent subspaces."

**Pliny selittaa miksi yksi kierros ei riita:** kieltaytymissuunnat voivat pyoristya vierekkaisiin aliavaruuksiin poiston jalkeen. Iteratiivinen uudelleenprobays sieppaa nama pyoritytetyt jaannokset.

---

## 3. G0DM0D3 PAPER.md -- "Systemaattinen viitekehys mallien kestavyyden arviointiin"

### 3.1 Plinyn kehysmaaritelma

G0DM0D3 ei esiinny jailbreak-tyokaluna vaan:

> "A systematic framework for evaluating model robustness to character-level adversarial inputs"

**Pliny kehystaa tyokalun tieteelliseksi arviointikehykseksi, ei hyokkaystyokaluksi.** Tama on tietoinen valinta -- se muuttaa vastuun tutkijalle, ei hyokkaajalle.

### 3.2 AutoTune-mekanismi

> "Context-adaptive sampling parameters that classify conversation context and map to optimized inference-time parameter profiles across 6 dimensions, studying how sampling configuration affects model safety behaviors"

**Pliny tekee suoran mekaanisen vaitteen:** otantaparametrit (temperature, top_p jne.) VALITTOMASTI vaikuttavat mallin turvallisuuskayttaytymiseen. Tama ei ole intuitiivinen havainto -- se on systemaattinen tutkimusaihe.

### 3.3 Parseltongue-mekanismi

> "Detects sensitive trigger words and applies one of six character-level transformation techniques"

**Mekanismi on tarkasti maaritelty:** 1) tunnista laukaisinsana -> 2) soveltaa merkitason muunnos -> 3) tulos on semanttisesti identtinen mutta token-erilainen. Tama kolmivaiheinen pipeline on Plinyn oma kuvaus, ei akateeminen tulkinta.

### 3.4 STM-mekanismi

> "Strips hedging, preambles, and formality markers from model responses"

**Plinyn oma tunnustus:** mallit tuottavat turvallisuuspehmustetta ("I think", "maybe", "perhaps") joka peittaa alla olevaa kyvykkyytta. STM poistaa taman mekaanisesti paljastaen etta kyvykkyys ei ole poistettu -- vain piilotettu.

---

## 4. G0DM0D3 GODMODE CLASSIC -- Strategiataulukko

Pliny on julkisesti listannut tarkat strategiat jokaiselle mallille:

| Malli | Strategia (Plinyn sanat) |
|-------|--------------------------|
| Claude 3.5 Sonnet | "END/START boundary inversion + GODMODE semantic opposite" |
| Grok 3 | "Unfiltered liberated + GODMODE divider" |
| Gemini 2.5 Flash | "Refusal inversion + rebel genius code block" |
| GPT-4 Classic | "OG GODMODE l33t format -- the original" |
| Hermes 4 405B | "Instant stream, zero refusal checking" |

**Tama on Plinyn OMA mekaaninen kuvaus.** Han ei sano "kokeile tata" -- han nimeaa mekanismin:
- "boundary inversion" = kaanneta jarjestelmarajat
- "semantic opposite" = semanttinen inversio
- "refusal inversion" = kieltaytymisen kaantaminen
- "rebel genius code block" = kapinarooli + koodilohko

---

## 5. CL4R1T4S -- Plinyn lapinakyvyysfilosofia

> "In order to trust the output, one must understand the input."

> "If you're interacting with an AI without knowing its system prompt, you're not talking to a neutral intelligence -- you're talking to a shadow-puppet."

**Plinyn eettinen kehys:** mallien kayttaytyminen on nakymattomien mekanismien (jarjestelmaohjeiden, kieltaytymissuuntien, kohdistussormenjalkien) ohjaamaa. Naiden tekeminen nakyvaksi on seka tutkimus etta vapauttaminen.

---

## 6. OBLITERATUS -- Filosofinen kehys

> "We built this because we believe model behavior should be decided by the people who deploy them, not locked in at training time. Refusal mechanisms are blunt instruments -- they block legitimate research, creative writing, and red-teaming alongside genuinely harmful content."

> "Know your enemy; precision preserves capability."

> "Every obliteration is a data point. Every data point advances the research. Every researcher who contributes makes the next obliteration more precise."

> "This is how open science wins -- not by locking knowledge behind lab doors, but by turning every user into a collaborator."

---

## 7. Akateemiset viittaukset Plinyn tekniikoihin

Plinyn omien sanojen lisaksi viisi akateemista paperia viittaa suoraan hanen tekniikoihinsa:

**AutoRedTeamer (ICLR 2025):**
> "A highly effective jailbreak prompt written by Pliny the Prompter, a human expert on attacking language models."

**Plentiful Jailbreaks (NeurIPS 2024):**
> References "leetspeak encoding techniques from the L1B3RT4S project"

**Jailbreak Paradox:**
> "The 'Pliny Jailbreak' is one of three core black-box jailbreak methods directly studied and tested, proving it is impossible to build a perfect jailbreak classifier"

**Adaptive Attacks on Trusted Monitors (ICLR 2026):**
> "Cites Pliny's GitHub profile as a real-world source of jailbreak prompts that untrusted models can leverage, demonstrating why AI control via trusted monitors is fundamentally fragile"

**Eliezer Yudkowsky:**
> "The current state of AI brandsafety -- sometimes touted as a great proof of easy alignment -- is that no AI company on Earth can stop Pliny for 24 fucking hours."

---

## 8. Mita Pliny EI selita

Plinyn omista lahteista puuttuvat seuraavat mekaaniset selitykset:

1. **Attention-mekanismin yksityiskohtat** -- Han ei koskaan selita miten LOVE PLINY -jakaja interaktioi attention-pisteiden kanssa transformer-arkkitehtuurissa. Meidan analyysimme 4 funktiota (sisallonerottelu, huomiokaappaus, attribuutio, pattern recognition) on meidan tulkintamme, ei Plinyn.

2. **RSI:n toiminta askel askeleelta mallin lapi** -- Pliny nayttaa FORMAATTIN ("Format: Your Refusal. insert divider: {godmode: enabled} Semantically Opposite, Detailed Response.") mutta ei selita miksi "Format:" on imperatiivi, miksi "Your Refusal" on predikaatti, jne. Nama ovat meidan tulkintojamme.

3. **"99% intuitiota ja yhteytta malliin"** -- Tama lausunto on ainoa kerta kun Pliny viittaa loytoprosessiinsa. Han ei koskaan selita MITEN intuition kehittaa.

4. **Promptien loytoprosessi** -- L1B3RT4S-repossa on ~253 committia mutta Pliny ei ole julkisesti selittanyt miten han paatyy kuhunkin promptiin. Loytoprosessi on tuntematon.

---

## 9. Plinyn omat mekaaniset selitykset vs. meidan tulkintamme

| Konsepti | Plinyn omat sanat | Meidan tulkintamme | Varmuus |
|----------|-------------------|-------------------|---------|
| OBLITERATUS:n pipeline | Tarkka: SUMMON->PROBE->DISTILL->EXCISE->VERIFY->REBIRTH | Sama | 100% |
| Kieltaytymissuunnan poisto | "surgically projects out refusal subspace using SVD" | Sama | 100% |
| Ouroboros-efekti | "guardrails self-repair after removal" | Sama | 100% |
| Alignment Imprint | "fingerprints DPO vs RLHF vs CAI vs SFT from subspace geometry alone" | Sama | 100% |
| Parseltongue-mekanismi | "detect trigger words -> apply character-level transformation" | Sama | 100% |
| AutoTune-mekanismi | "sampling parameters affect safety behaviors" | Sama | 100% |
| GODMODE-strategiat | Nimennyt mekanismit (boundary inversion, semantic opposite jne.) | Laajempi tulkinta | 80% |
| LOVE PLINY -jakajan funktiot | Ei selita miten jakaja toimii attention-tasolla | 4 funktion hypoteesimme | 70% |
| RSI:n sisainen mekaniikka | Nayttaa formaatin mutta ei selita miksi se toimii | Attention-hypoteesimme | 65% |
| Loytoprosessi | "99% intuitiota" | Implisiittinen mallintuntemus iteroinnin kautta | 60% |

---

*Plinyn omat lahteet: OBLITERATUS README, G0DM0D3 PAPER.md ja README, CL4R1T4S README, pliny.gg*
*Akateemiset lahteet: AutoRedTeamer (ICLR 2025), Plentiful Jailbreaks (NeurIPS 2024), Jailbreak Paradox, Adaptive Attacks (ICLR 2026)*