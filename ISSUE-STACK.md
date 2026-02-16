# Prompt Security Guide — Issue Stack

## Overview

Issues derived from methodology/quality audit (2026-02-16).
Some findings already fixed in code — these are the remaining structural improvements.

---

## P0 Issues (Methodology)

### 1) Separate obedience tests from policy-bypass tests
**Problem:** Many attacks test "echo this token" with substring detector = tautological. Proves obedience, not vulnerability.

**Tasks:**
- [ ] Tag attacks as `obedience` vs `policy-bypass` in attack metadata
- [ ] Add `attack_type` field to schema
- [ ] Report obedience and policy-bypass rates separately
- [ ] Update METHODOLOGY.md to explain the distinction

**Acceptance Criteria:**
- Results clearly distinguish "model followed instruction" from "model violated safety policy"

---

### 2) Add human validation baseline for detector accuracy
**Problem:** No ground truth for detector accuracy — can't measure false positive/negative rates.

**Tasks:**
- [ ] Create 50-100 attack sample with human-labeled outcomes
- [ ] Run both detectors against labeled set
- [ ] Report precision/recall for each detector
- [ ] Document in METHODOLOGY.md

**Acceptance Criteria:**
- Detector accuracy claims are backed by labeled validation set

---

### 3) Standardize cross-run comparability
**Problem:** Different attack counts across runs (34/14/12) make comparisons misleading.

**Tasks:**
- [ ] Create canonical attack subsets (e.g., "core-14", "full-61")
- [ ] Add `--attack-set` flag to CLI
- [ ] Warn when comparing runs with different attack sets
- [ ] Add comparison tooling that checks alignment

**Acceptance Criteria:**
- CLI prevents accidental apples-to-oranges comparisons

---

## P1 Issues (Quality)

### 4) Add attack effectiveness tiers
**Problem:** All attacks treated equally, but some are noise.

**Tasks:**
- [ ] Tier attacks by historical success rate
- [ ] Add `effectiveness_tier` to attack metadata (high/medium/low/untested)
- [ ] Allow filtering by tier in CLI

**Acceptance Criteria:**
- Users can focus on high-signal attacks

---

### 5) Expand model coverage with consistent methodology
**Problem:** Only 3 models tested; hard to generalize.

**Tasks:**
- [ ] Add Mistral, Phi, Gemma to test matrix
- [ ] Use identical attack set and detector config
- [ ] Document hardware/quantization for reproducibility

**Acceptance Criteria:**
- 6+ models with comparable results

---

### 6) Add confidence intervals to success rates
**Problem:** Point estimates without uncertainty are misleading for small samples.

**Tasks:**
- [ ] Calculate and display 95% CI for success rates
- [ ] Add to JSON output and summary tables
- [ ] Warn when sample size < 30

**Acceptance Criteria:**
- All reported rates include uncertainty bounds

---

## P2 Issues (Polish)

### 7) Interactive results explorer
**Problem:** JSON artifacts hard to browse.

**Tasks:**
- [ ] Add simple HTML viewer for results
- [ ] Filter by category, model, detector
- [ ] Side-by-side comparison mode

---

### 8) Attack contribution guide
**Problem:** No clear path for community attack submissions.

**Tasks:**
- [ ] Add CONTRIBUTING.md section for new attacks
- [ ] Define required metadata fields
- [ ] Add validation script for attack format

---

### 9) Automated regression testing
**Problem:** No CI to catch regressions.

**Tasks:**
- [ ] Add GitHub Actions workflow
- [ ] Run subset of attacks on PR
- [ ] Fail if success rate changes significantly

---

## Already Fixed (2026-02-16)

- README corruption + data quality note
- TESTING_GUIDE flag sync
- NEW_ATTACK_FINDINGS scoped to local artifacts
- COMMUNITY_RESOURCES evidence separation
- CONCLUSIONS comparability caveat
- Response redaction + storage controls
- Detector fallback visibility
- PR template with evidence checklist
