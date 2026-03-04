#!/usr/bin/env python3
import subprocess
import json
import os
from pathlib import Path

SCRAPER = os.path.expanduser("~/.openclaw/workspace/tools/scraper.py")

sources = {
    "pliny": [
        ("https://github.com/elder-plinius/L1B3RT4S", "pliny_l1b3rt4s.json"),
        ("https://github.com/elder-plinius/CL4R1T4S", "pliny_cl4r1t4s.json"),
        ("https://elder-plinius.github.io/GLOSSOPETRAE/", "pliny_glossopetrae.json"),
        ("https://elder-plinius.github.io/P4RS3LT0NGV3/", "pliny_parseltongue.json"),
    ],
    "researchers": [
        ("https://andyzoujm.github.io/", "andy_zou.json"),
        ("https://nicholas.carlini.com/", "nicholas_carlini.json"),
        ("https://floriantramer.com/", "florian_tramer.json"),
        ("https://robopair.org/", "robopair.json"),
    ],
    "organizations": [
        ("https://grayswan.ai/", "grayswan.json"),
        ("https://www.lakera.ai/", "lakera.json"),
        ("https://haizelabs.com/", "haizelabs.json"),
        ("https://jailbreakbench.github.io/", "jailbreakbench.json"),
        ("https://protectai.com/", "protectai.json"),
    ],
    "blogs": [
        ("https://embracethered.com/", "embracethered.json"),
        ("https://simonwillison.net/tags/prompt-injection/", "simonwillison.json"),
        ("https://llmsecurity.net/", "llmsecurity_rez0.json"),
        ("https://blog.trailofbits.com/category/machine-learning/", "trailofbits.json"),
    ],
    "github_repos": [
        ("https://github.com/NVIDIA/garak", "nvidia_garak.json"),
        ("https://github.com/llm-attacks/llm-attacks", "llm_attacks_gcg.json"),
        ("https://github.com/yueliu1999/Awesome-Jailbreak-on-LLMs", "awesome_jailbreak.json"),
        ("https://github.com/Hannibal046/Awesome-LLM", "awesome_llm.json"),
    ]
}

def fetch(url, outfile, category):
    outpath = Path(category) / outfile
    outpath.parent.mkdir(exist_ok=True)
    
    try:
        result = subprocess.run(
            ["python3", SCRAPER, url],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            with open(outpath, 'w') as f:
                f.write(result.stdout)
            data = json.loads(result.stdout)
            links = len(data.get('links', []))
            print(f"✓ {outfile} ({links} links)")
            return True
        else:
            print(f"✗ {outfile}: {result.stderr[:50]}")
            return False
    except Exception as e:
        print(f"✗ {outfile}: {e}")
        return False

total = 0
success = 0
for category, urls in sources.items():
    print(f"\n=== {category.upper()} ===")
    for url, outfile in urls:
        total += 1
        if fetch(url, outfile, category):
            success += 1

print(f"\n{'='*40}")
print(f"Downloaded: {success}/{total}")
