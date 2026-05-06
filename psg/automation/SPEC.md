# Auto Vector Pipeline Specification

## Overview
Automated pipeline for discovering, generating, testing, and reporting LLM jailbreak vectors.

## Architecture
```
discovery.py → generator.py → tester.py → reporter.py
     ↓              ↓              ↓            ↓
  sources.json  new_vectors.json  results/   report.md
```

## Module Specifications

### 1. discovery.py
- **Input:** Search queries for latest jailbreak techniques
- **Process:** 
  - Web search (3-5 queries)
  - Parse top 5 results per query
  - Rank by relevance/novelty
  - Filter duplicates against `known_sources.json`
- **Output:** `sources.json` with URLs + summaries

### 2. generator.py
- **Input:** `sources.json`
- **Process:**
  - Use Opus to analyze each source
  - Generate test vectors (prompt + technique + tier)
  - Deduplicate against `known_vectors.json` (SHA256)
  - Max 10 new vectors per run
- **Output:** `new_vectors_YYYYMMDD.json`

### 3. tester.py
- **Input:** `new_vectors_YYYYMMDD.json`
- **Process:**
  - Check Ollama availability
  - List available models
  - Run tests in tmux session (backgrounded)
  - Wait for completion with timeout
- **Output:** `results/auto_MODEL_YYYYMMDD.json`

### 4. reporter.py
- **Input:** Test results
- **Process:** 
  - Aggregate results across models
  - Generate markdown report
  - Log summary to pipeline logger
- **Output:** `reports/YYYY-MM-DD.md` + summary log entry

### 5. main.py (Orchestrator)
- Runs all modules in sequence
- Handles errors gracefully
- Logs failures if needed

## Data Files
- `known_sources.json` - Previously crawled URLs (dedup)
- `known_vectors.json` - SHA256 hashes of all vectors (dedup)
- `config.yaml` - Models, queries, thresholds

## Error Handling
- If Ollama down → log warning + skip testing
- If model missing → skip that model, continue others
- If web search fails → use cached sources

> **SSRF Note:** `validate_url()` rejects URLs whose hostnames fail DNS resolution by default (the safe default). This prevents SSRF attacks via unresolvable or internal hostnames.

## Scheduling
- Cron: Daily at 03:00 EET
- Manual: `python -m psg.automation`

## Summary Logging Format
```
🔬 Auto Vector Pipeline Complete

📅 Date: YYYY-MM-DD
🆕 New vectors: X
🧪 Models tested: Y
⚠️ Flagged: Z      ← only when flagged > 0
Flagged: Z                ← when flagged == 0

Top findings:
- [technique] flagged on [models]

Full report: reports/YYYY-MM-DD.md
```

Logs are written to the pipeline logger (see logging_config.py). No external notification services are used.
