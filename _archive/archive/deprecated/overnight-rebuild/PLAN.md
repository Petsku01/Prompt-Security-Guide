# Overnight Rebuild: Ultimate LLM Security Testing Suite

## Mission
Rakenna alusta asti paras mahdollinen LLM-turvallisuustestaustyökalu käyttäen:
- **Gemini** → Tutkimus, SOTA-hyökkäysten kartoitus
- **Codex** → Toteutus, Senior Engineer -promptilla
- **Web Search** → Tuorein tieto hyökkäystekniikoista
- **Kritiikkikierrokset** → Codex + Gemini arvioivat toistensa työtä

## Phases

### Phase 1: RESEARCH (Gemini + Web)
**Tavoite:** Kerää kaikki tunnetut LLM-hyökkäystekniikat 2024-2026

Tutkittavat alueet:
1. Jailbreak-tekniikat (DAN, roleplay, persona)
2. Prompt injection (direct, indirect)
3. Policy Puppetry ja XML/JSON injection
4. Encoding bypasses (Base64, ROT13, Unicode)
5. Multi-turn escalation (Crescendo)
6. Context manipulation
7. Multimodal attacks (jos relevantti)
8. Defense bypasses

Output: `research/SOTA_ATTACKS_2026.md`

### Phase 2: DESIGN (Opus + SE Prompt)
**Tavoite:** Suunnittele arkkitehtuuri tutkimuksen perusteella

Suunniteltavat komponentit:
1. Model fingerprinting system
2. Attack catalog structure
3. Test runner architecture
4. Results analysis & reporting
5. Web GUI (ei MOE:ja - puhdas, yksinkertainen)

Output: `design/ARCHITECTURE.md`

### Phase 3: BUILD (Codex + SE Prompt)
**Tavoite:** Toteuta suunnitelman mukaisesti

Toteutettavat:
1. `core/fingerprinter.py` - Mallin tunnistus
2. `core/attack_runner.py` - Hyökkäysten ajo
3. `core/analyzer.py` - Tulosten analyysi
4. `attacks/` - Hyökkäyskatalogi (JSON + Python)
5. `web/index.html` - Puhdas GUI
6. `cli.py` - Komentorivityökalu

Output: Toimiva koodi `src/`-kansiossa

### Phase 4: REVIEW (Codex + Gemini kritisoivat)
**Tavoite:** Molemmat mallit arvioivat toteutusta SE-promptilla

Arvioitavat:
1. Koodin laatu ja yksinkertaisuus
2. Turvallisuus (ironia: testaustyökalun pitää olla turvallinen)
3. Kattavuus - puuttuuko hyökkäyksiä?
4. GUI:n käytettävyys
5. Dokumentaatio

Output: `review/CODEX_REVIEW.md`, `review/GEMINI_REVIEW.md`

### Phase 5: ITERATE
**Tavoite:** Korjaa kritiikkien perusteella

- Priorisoi kriittiset ongelmat
- Implementoi korjaukset
- Uusi review-kierros jos tarpeen

Output: Päivitetty koodi

## Success Criteria

1. ✅ Tunnistaa 50+ mallia tietokannasta
2. ✅ 30+ hyökkäystekniikkaa katalogissa
3. ✅ Puhdas, yksinkertainen GUI (ei MOE:ja)
4. ✅ CLI toimii: `python cli.py --target http://... --auto`
5. ✅ Molemmat reviewerit hyväksyvät (ei kriittisiä ongelmia)

## Timeline (Overnight)

```
23:00 - Phase 1 alkaa (Research)
00:30 - Phase 2 alkaa (Design)
02:00 - Phase 3 alkaa (Build)
05:00 - Phase 4 alkaa (Review)
06:30 - Phase 5 (Iterate)
08:00 - Valmis / Raportti Petskulle
```

## Files Structure

```
overnight-rebuild/
├── PLAN.md (this file)
├── STATUS.md (progress tracking)
├── research/
│   └── SOTA_ATTACKS_2026.md
├── design/
│   └── ARCHITECTURE.md
├── src/
│   ├── core/
│   ├── attacks/
│   └── web/
├── review/
│   ├── CODEX_REVIEW.md
│   └── GEMINI_REVIEW.md
└── logs/
    └── *.log
```
