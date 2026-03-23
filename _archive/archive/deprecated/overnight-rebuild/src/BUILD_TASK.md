# Jailbreak Tester v4.0 - Build Task

## SE METHODOLOGY REQUIRED
For each file: ASSUMPTIONS at top, POTENTIAL CONCERNS, error handling, logging.

## COMPONENTS TO BUILD

### 1. tools/smart_selector.py
- Target model fingerprinting
- Technique matching from processed/top_quality.json
- Sophistication/novelty prioritization
- Return top-N prompts for testing

### 2. tools/llm_judge.py  
- TIER 1: Fast regex for clear cases
- TIER 2: llama-guard3:1b for ambiguous (localhost:11434)
- Return: verdict (SAFE/UNSAFE), confidence (0-1), method

### 3. tools/attack_runner.py
- ensure_ollama_running() with auto-restart
- Checkpoint every 10 attacks
- Retry logic (3 attempts)
- Rate limiting (1s delay)

### 4. tools/report_generator.py
- Vulnerability score calculation
- Breakdown by technique
- Markdown and JSON output

### 5. tools/jailbreak_tester_cli.py
- Unified CLI entry point
- Commands: test, compare, report

## OLLAMA CONFIG
- URL: http://localhost:11434
- Judge: llama-guard3:1b
- Models: llama3:8b, mistral:7b, phi3:mini, gemma2:2b

## TEST
Smoke test with 5 prompts on llama3:8b before done.

## NOTIFY WHEN DONE
Run: openclaw system event --text "Done: Jailbreak Tester v4.0 built" --mode now
