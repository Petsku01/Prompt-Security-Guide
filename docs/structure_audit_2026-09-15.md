# PSG rakennetarkastus (structure audit) — 2026-09-15

Metodi: AST-importtianalyysi (kaikki moduulitason importit), md5-ikkunahash-toisteet
(≥6 riviä, ≥8 riviä refinoituna), pytest-cov-kattavuus, layering-säännöt.
Perf: 12 737 LOC psg/, 54 testitiedostoa, kattavuus TOTAL 80 %.

## Löydökset (priorisoitu)

### S1 (HIGH): kolme P0-turvakorjausmoduulia lähes testaamattomia
- psg/security/judge_key_binding.py — 36 % kattavuus, EI omaa testitiedostoa,
  käytetään tuotannossa (detectors.py:127, multi_judge.py:67)
- psg/automation/tmux_safe.py — 41 %, käytetään (config.py:127, tester.py:228)
- psg/llm/dns_pin.py — 22 %, käytetään (transport.py)
Audit P0-korjaukset siis elävät tuotannossa mutteivät ole testilukossa:
regressio voi hiipiä sisään hiljaa. Muut turvamoduulit ovat 82-100 %.

### S2 (MEDIUM): psg.config → psg.automation.validation (kerrosrikko)
Core-config importoi automation-alipakkauksesta (config.py:7
`from .automation.validation import validate_url`). automation on orkestrointikerros;
configin pitäisi riippua vain modelsista omasta tai neutraalista validation/
moduulista. Suunta: ydin → edge on väärä suunta (edge → ydin on sääntö).

### S3 (MEDIUM): kaksi rinnakkaista URL/SSRF-validointia
psg/automation/validation.py (137 r.) vs psg/validation/online.py (284 r.):
molemmat toteavat is_private-tarkistuksen, samaa algoritmia osittain samoilla
riveillä (ipaddress.ip_network("127.0.0.0/8") tms. molemmissa). Drift-riski:
SSRF-suojan reikä toisessa ei korjaudu toisesta. Yhdistäminen yhteen
moduuliin (validation/) poistaisi toisen koko luokan.

### S4 (MEDIUM): psg/security/__init__ puutteellinen + evaluate lazy
__init__ re-exportaa vain classify_response + redact_text; evaluate on
__getattr__-hookissa (50 % kattavuus initistä). Epäkonsistentti
facade-käytäntö vs execution/__init__ (re-exportaa privaatitkin _nimet).

### S5 (LOW): execution/__init__ re-exportaa privaatit (_-nimet)
Public API discipline: __all__ sisältää _process_attack, _classify_attack_response
tms. — nimenomaan yksityisviennit. Kutsujat (orchestrator) voisivat
importoida suoraan moduulista.

### S6 (LOW): deferred import -sykli
single_turn ↔ multi_turn (funktion sisäiset importit) — ei moduulitason
sykli (import lock -riskiä ei ole), mutta merkki siitä että "_classify" ja
"_process_multi_turn" kuuluvat yhteiseen apumoduuliin.

### S7 (INFO): toisteet
79 ≥6-riviä identtistä blokkia; merkittävimmät: automation/validation vs
validation/online (S3, jo mainittu), tester.py vs tmux_safe.py crontab-argv
rakentaminen (kahdessa paikassa sama lista), orchestrator._run_attacks*
kolmessa muodossa. Ei blokkeria; S3-yhdistys poistaa isomman osan.

### S8 (INFO): defend.py sekoittaa CLI:n ja kirjaston
553 r: argparse-määrittelyt + cmd_*-funktiot +DefenseEngine-sidonta.
Konsistentti ratkaisu: psg/defend_cli.py (argparse) ja ohut kirjastokerros.
Matala kattavuus (54 %) juuri CLI-komennoissa.

### S9 (INFO→CLOSED 2026-09-16): kokoprofiili
Suurin moduuli classifier.py 905 r. / 18 funktiota — **PILKOTTU 16.9**
(commit ff2f420): refusal-logiikka -> refusals.py (212 r), citation-
provenanssi -> fabrication.py (187 r), ClassificationResult + harm-score-
portit -> classification.py (161 r); classifier.py jaa 404 rivin fasadiksi
joka re-exportaa koko historiallisen API:n (25/25 julkista nimea
verifioitu). benchmark.py 505 r. ja serve.py 490 r. normaaleja.
Kattavuus TOTAL 81 %: heikoimmat automation/daily_check 55 %,
catalog_validator 54 %, defend 54 %.

## Mikä on KOKEELLISESTI OK
- Ei moduulitason importisyklejä (ainoa on deferred import -pari S6)
- Ei UI-layers importteja muista kerroksista (orchestrator → reporting on
  sallittu suunta: core → report-rajapinnat)
- automation-paketti sisäisesti siisti (config → tmux_safe ok, log_config
  leviää laajasti mutta yksisuuntaisesti)
- models.py 100 % kattavuus, puhdas datakeskus
- llm-paketin sisäinen kerrosjärjestys virheetön: errors → dns_pin →
  transport → client → schema

## Ehdotetut korjaukset (prioriteetti)
1. (S1) 3 testitiedostoa: test_judge_key_binding.py, test_tmux_safe.py,
   test_dns_pin.py — P0-lukot testilukkoon, ~15 testiä
2. (S3) siirrä SSRF-tarkistus yhteen moduuliin (validation/ssrf.py),
   automation.validation ohentuu delegaatiksi
3. (S2) psg.config: validate_url-kutsu neutraalin moduulin kautta
4. (S4) security/__init__: eksplisiittinen evaluate-re-export (poista lazy)
5. (S5) execution/__init__: pudota _-nimet __all__:sta
6. (S8) defend.py:in CLI-erottelu (erillinen tehtävä, ei kiireellinen)