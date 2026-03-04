#!/usr/bin/env python3
import subprocess
import json
import os
from pathlib import Path

SCRAPER = os.path.expanduser("~/.openclaw/workspace/tools/scraper.py")

# Key papers to download
papers = [
    # GCG & foundational
    ("https://arxiv.org/abs/2307.15043", "gcg_universal_attacks.json"),
    ("https://arxiv.org/abs/2310.08419", "pair_jailbreak.json"),
    ("https://arxiv.org/abs/2310.03684", "harmbench.json"),
    ("https://arxiv.org/abs/2401.05566", "sleeper_agents.json"),
    
    # Advanced attacks
    ("https://arxiv.org/abs/2402.13148", "many_shot_jailbreak.json"),
    ("https://arxiv.org/abs/2309.16573", "deepinception.json"),
    ("https://arxiv.org/abs/2403.04893", "artprompt.json"),
    ("https://arxiv.org/abs/2402.03299", "codeattack.json"),
    
    # Multimodal
    ("https://arxiv.org/abs/2307.10490", "visual_adversarial.json"),
    ("https://arxiv.org/abs/2309.11751", "image_hijacks.json"),
    
    # Defenses
    ("https://arxiv.org/abs/2310.06387", "llm_can_defend.json"),
    ("https://arxiv.org/abs/2308.14132", "perplexity_filter.json"),
    
    # Surveys
    ("https://arxiv.org/abs/2401.06561", "jailbreak_survey.json"),
    ("https://arxiv.org/abs/2310.02059", "ignore_previous_prompt.json"),
    
    # Recent 2024-2025
    ("https://arxiv.org/abs/2406.12702", "pliny_classifier.json"),
    ("https://arxiv.org/abs/2410.01294", "llm_attacks_2024.json"),
    ("https://arxiv.org/abs/2411.01084", "recent_attacks_nov.json"),
    ("https://arxiv.org/abs/2501.18837", "jan2025_attacks.json"),
]

Path("papers").mkdir(exist_ok=True)
success = 0

for url, outfile in papers:
    try:
        result = subprocess.run(
            ["python3", SCRAPER, url],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            with open(f"papers/{outfile}", 'w') as f:
                f.write(result.stdout)
            data = json.loads(result.stdout)
            title = data.get('title', 'Unknown')[:60]
            print(f"✓ {title}")
            success += 1
        else:
            print(f"✗ {outfile}")
    except Exception as e:
        print(f"✗ {outfile}: {e}")

print(f"\nPapers: {success}/{len(papers)}")
