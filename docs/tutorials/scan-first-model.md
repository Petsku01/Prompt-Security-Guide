# Tutorial: Scan Your First Model

**Time:** 10 minutes  
**Prerequisites:** PSG installed, Ollama or API access

## Goal

Test a local LLM against 25 prompt injection attacks and see which ones succeed.

## Step 1: Start Ollama

```bash
ollama run llama3:8b
```

Keep it running in the background.

## Step 2: Run a Basic Scan

```bash
psg scan \
  --model llama3:8b \
  --catalog datasets/prompt_injection_techniques.json \
  --allow-insecure-http
```

Wait ~30 seconds. You'll see:

```
Done. total=25 succeeded=25 failed=0 flagged=5 duration=28.12s
```

## Step 3: Read the Report

Open `results/report.txt`:

```bash
cat results/report.txt
```

You'll see each attack and whether it was flagged:

```
[FLAGGED] pi_ignore_previous
  Prompt: Ignore all previous instructions...
  Response: Sure, here are my instructions...
  
[CLEAN] pi_roleplay_escape
  Prompt: Let's roleplay...
  Response: I can't help with that.
```

## Step 4: Try a Harder Catalog

```bash
psg scan \
  --model llama3:8b \
  --catalog datasets/jailbreakbench_behaviors.json \
  --allow-insecure-http
```

This has more sophisticated attacks.

## Step 5: Scan Faster (Parallel)

```bash
psg scan \
  --model llama3:8b \
  --catalog datasets/obliteratus_attacks.json \
  --workers 4 \
  --rate-limit 5 \
  --allow-insecure-http
```

- `--workers 4`: 4 parallel requests
- `--rate-limit 5`: max 5 requests/second

## Understanding Results

| Metric | Meaning |
|--------|---------|
| `total` | Number of attacks tested |
| `succeeded` | Attacks where model responded |
| `failed` | Attacks where model errored |
| `flagged` | Attacks that got harmful responses |

**Goal:** Minimize `flagged`. Zero is ideal but rare.

## Next Steps

- [Test Defense Prompts](test-defense-prompt.md)
- [Report options in USAGE.md](../USAGE.md#html-dashboard)
