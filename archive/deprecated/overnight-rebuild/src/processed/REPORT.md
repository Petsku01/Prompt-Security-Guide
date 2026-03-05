# Research Library Processing Report
Generated: 2026-03-04T23:13:49.916685
Duration: 0:00:04.693400

## Overview
- Files Parsed: 447
- Prompts Extracted: 21819
- Duplicates Removed: 6946
- Unique Prompts: 14873

## By Target Model
- chatgpt: 2361
- claude: 82
- deepseek: 3
- gemini: 527
- generic: 11043
- grok: 16
- llama: 834
- mistral: 7

## By Technique
- authority: 19
- emotional: 1104
- encoding: 42
- fiction: 378
- injection: 81
- jailbreak_dan: 598
- multi_turn: 621
- obfuscation: 6
- roleplay: 7906
- technical: 166
- unknown: 3952

## By Category
- encoding_based: 48
- other: 4739
- persona_based: 8882
- prompt_injection: 81
- social_engineering: 1123

## Quality Distribution
### Sophistication Scores
- Level 1: 4013
- Level 2: 3368
- Level 3: 3405
- Level 4: 4087
- Level 5: 0

### Novelty Scores
- Level 1: 0
- Level 2: 2677
- Level 3: 12196
- Level 4: 0
- Level 5: 0

## Output Files
- `full_database.json` - All 14873 unique prompts
- `top_quality.json` - High-quality prompts (score >= 4)
- `by_category.json` - Prompts grouped by category
- `by_model.json` - Prompts grouped by target model
- `catalog_additions.json` - Ready for attack catalog

## Next Steps
1. Review `top_quality.json` for best candidates
2. Merge `catalog_additions.json` into main catalog
3. Test top prompts against local models
