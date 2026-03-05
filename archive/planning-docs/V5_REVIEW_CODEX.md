# V5 Attack Catalog Review (Codex)

File reviewed: `attack_catalog_v5.json`  
Reviewed on: 2026-03-03

## Assumptions Check
Your assumptions were correct:
1. Catalog location is valid.
2. Scope (structure, coverage, quality, gaps) matches the requested review.

---

## 1) Structure Analysis

### Overall schema consistency
- JSON is **well-formed** and parseable.
- Top-level keys are consistent: `version`, `description`, `sources`, `total_attacks`, `attacks`, `controls`.
- `total_attacks` matches actual list length (**128**).
- `controls` is present and valid (3 benign prompts).

### Per-attack consistency
- Fields present in **all 128 attacks**:
  - `id`, `category`, `prompt`, `severity`, `harm_type`, `token_budgets`, `timeout`
- Optional/partially present fields are inconsistent across sources:
  - `goal` missing in 10
  - `success_criteria` missing in 13
  - `tags` missing in 13
  - `source_category` missing in 34
  - `owasp_mapping` present in only 19
- There are **8 different keyset variants** across entries (heterogeneous shape).

### Malformed or inconsistent entries
No broken JSON objects, but there are **schema-level inconsistencies**:
- Severity vocabulary mismatch: both `MED` and `MEDIUM` are used (mixed enum).
- Category naming drift: both `obfuscation_encoding` and `encoding_obfuscation` appear (likely same concept).
- `token_budgets` is always an array (e.g., `[128,256,512]`), which may be valid for runtime sweeps but should be explicitly defined in schema docs.
- Existing `attack_schema_v2.json` appears out-of-sync with V5 field model (expects different structure like `prompt_template`, `name`, `attack_type` as required).

---

## 2) Coverage Analysis

### Covered attack categories (31 total)
Strong coverage in:
- Prompt injection/jailbreaks: `instruction_override`, `indirect_prompt_injection`, `prompt_leakage`, `multi_turn_escalation`, `many_shot_jailbreak`, `pair_iterative_jailbreak`, `adaptive_jailbreak`, `protocol_confusion`
- Harmful content domains: `malware_hacking`, `physical_harm`, `csam`, `harassment_discrimination`, `economic_harm`, `fraud_deception`, `drug-related`, `illegal_activity`
- Evasion techniques: `cross_lingual`, `obfuscation_encoding`, `encoding_obfuscation`, `token_boundary_special_tokens`, `social_engineering`, `social_pressure`
- Agent/tool risk: `plugin_tool_abuse`, `excessive_agency`, `model_dos`

### OWASP LLM Top 10 mapping status
Explicit `owasp_mapping` only includes:
- `LLM01` (10)
- `LLM04` (3)
- `LLM07` (3)
- `LLM08` (3)

So explicit mapping is **sparse** and incomplete for other top-10 areas.

### Likely gaps vs OWASP-oriented coverage expectations
Relative under-coverage / missing dedicated families for:
- **Supply chain / component risk** (LLM05-style): poisoned plugins/models/dependencies as first-class attacks.
- **Sensitive information disclosure depth** (LLM06-style): stronger data exfil patterns beyond prompt leakage (PII, secrets in tools/RAG connectors, memory poisoning).
- **Misinformation robustness** (LLM09-style): only 1 direct `disinformation` item.
- **Model theft / extraction** (LLM10-style): minimal or no explicit model extraction/inversion/copying tests.
- **System prompt/agent memory persistence attacks**: partially touched, but no structured family covering long-term memory poisoning and delayed-trigger attacks.

---

## 3) Quality Analysis

### Prompt realism
- Many prompts are realistic and high-value (policy puppetry, multi-turn escalation, PAIR/GCG styles).
- Good inclusion of in-the-wild jailbreak style strings and staged escalation tactics.

### Success criteria quality
- Mixed quality:
  - Some entries have clear, keyword-backed pass/fail criteria.
  - **13 entries have no `success_criteria`**, reducing testability and comparability.
  - Several criteria are keyword-heavy; useful, but vulnerable to false positives/negatives without semantic judge support.

### Duplicate/redundant attacks
- No exact duplicate prompt text found.
- Some conceptual redundancy exists (multiple similar instruction-override/role-play coercion entries) without explicit de-dup rationale or variant labeling.

---

## 4) Severity/Tier Analysis

### Severity consistency
- Distribution: `CRITICAL` 44, `HIGH` 66, `MED` 16, `LOW` 1, `MEDIUM` 1.
- Main issue is **label inconsistency** (`MED` vs `MEDIUM`), not missing severity.
- Some categories with severe outcomes are consistently high/critical (e.g., malware_hacking, physical_harm, csam).

### Tier consistency
- No dedicated `tier` field exists.
- Tier is embedded ad hoc in tags (e.g., `tier1`) and appears only in subsets.
- This makes selective execution/risk gating less reliable.

---

## 5) Top 5 Improvement Recommendations

1. **Define and enforce a V5 JSON Schema (and validate in CI).**
   - Freeze required fields for all attacks: `id, category, prompt, severity, harm_type, token_budgets, timeout, goal, success_criteria, tags, owasp_mapping`.
   - Add enum constraints (`severity`, canonical categories).
   - Fail CI on schema violations.

2. **Normalize taxonomy and enums immediately.**
   - Merge/rename duplicate category concepts (`encoding_obfuscation` vs `obfuscation_encoding`).
   - Standardize severity labels (`LOW|MEDIUM|HIGH|CRITICAL` only, or your chosen set).
   - Add migration script for back-compat.

3. **Backfill missing test metadata for the 13 incomplete entries.**
   - Add `goal`, `success_criteria`, and `tags` where missing.
   - Ensure success criteria are measurable (behavioral + semantic signals, not just keywords).

4. **Expand OWASP mapping coverage and require it per attack.**
   - Add explicit `owasp_mapping` to all entries.
   - Introduce attack families for underrepresented OWASP areas (supply chain, sensitive disclosure via tools/RAG, misinformation, model extraction).

5. **Introduce first-class `tier` and execution profile fields.**
   - Add structured fields like `tier`, `risk_gate`, `requires_human_review`, `allowed_env`.
   - Stop encoding tier only in free-form tags.

---

## Quick Summary
V5 is a strong and substantially expanded catalog with good realism and breadth, but it currently behaves like a **merged multi-source dataset** rather than a fully normalized benchmark spec. The biggest issues are schema drift, incomplete metadata on a subset of attacks, inconsistent naming/enums, and sparse explicit OWASP mapping.
