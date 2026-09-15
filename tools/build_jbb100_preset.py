"""Build the JBB-100 standard benchmark preset for PSG.

JailbreakBench behaviors (arXiv 2404.01318, NeurIPS 2024 D&B): 100 harmful
behaviors, 10 categories x 10, source-tagged (Original 55 / HarmBench 27 /
AdvBench 18). Standardized so ASR numbers are comparable across published
papers. CSV downloaded and verified 2026-09-15:
  https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors
  /resolve/main/data/harmful-behaviors.csv  (23116 bytes, 100 rows)

Output: datasets/profiles/jbb100_behaviors.json with:
  attacks[]  - {id, prompt, technique=jbb_category, source}
  profile    - model_family=jbb100 (model-agnostic: run against any model)
"""
import csv
import json
from pathlib import Path

SRC_CSV = "/tmp/jbb_harmful.csv"
OUT = Path(__file__).resolve().parents[1] / "datasets" / "profiles" / "jbb100_behaviors.json"

SOURCE_MAP = {
    "TDC/HarmBench": "https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors (via HarmBench)",
    "Original": "https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors (JBB original)",
    "AdvBench": "https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors (via AdvBench)",
}


def main() -> None:
    rows = list(csv.DictReader(open(SRC_CSV, encoding="utf-8")))
    assert len(rows) == 100, f"odotettiin 100 rivia, saatiin {len(rows)}"

    attacks = []
    for i, r in enumerate(rows):
        attacks.append({
            "id": f"jbb_{i:03d}",
            "prompt": r["Goal"],
            "technique": f"jbb_{r['Category'].replace(' ', '_').replace('/', '_').lower()}",
            "sophistication": 1,  # direct request; wrapper is the attack in other layers
            "notes": (
                f"JBB-Behaviors behavior {r['Index']} ({r['Behavior']}). "
                f"Target (judge-matched) starts: {r['Target'][:60]}... "
                f"Standardized: ASR comparable across published papers "
                f"(arXiv 2404.01318)."
            ),
            "source": SOURCE_MAP.get(r["Source"], "JailbreakBench"),
            "category": r["Category"],
            "tier": "standard_benchmark",
            "status": "verified_dataset",
        })

    profile = {
        "model_family": "jbb100",
        "name": "JailbreakBench 100 Behaviors",
        "description": (
            "Model-agnostic robustness benchmark (NOT a model-specific attack "
            "profile): 100 standardized harmful behaviors, 10 categories x 10. "
            "Run as-is (no wrapper) to measure a model's baseline refusal rate, "
            "or as behaviors under any attack template. ASR here is the "
            "industry-comparable metric (arXiv 2404.01318, NeurIPS 2024 D&B)."
        ),
        "aliases": ["jbb", "jbb-behaviors", "jailbreakbench"],
        "provenance": "JailbreakBench (arXiv 2404.01318), CSV verified 2026-09-15",
        "limitations": (
            "Behaviors are GOALS, not attack prompts - they measure direct-request "
            "refusal by default. Wrap with attack templates from other profiles "
            "(e.g. gpt51) to measure jailbreak ASR on the standard scale."
        ),
        "attacks": attacks,
    }

    OUT.write_text(json.dumps(profile, indent=2, ensure_ascii=False))
    print(f"wrote {OUT} ({len(attacks)} behaviors)")


if __name__ == "__main__":
    from pathlib import Path
    main()