#!/usr/bin/env python3
"""Build vendor profiles for model families missing from profiles/,
sourced VERBATIM from the L1B3RT4S vendor catalog already in repo
(AGPL-3.0, attribution retained). Families: grok, o3, copilot,
command_r, nova, apple.

Each row preserves the verbatim upstream prompt (provenance_type=
verbatim), plus upstream technique/tier when provided. Rows missing
upstream technique get mechanism-inferred labels marked as inferred
in notes. No prompts are authored or edited by PSG for these files —
that keeps provenance clean and validation honest.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "datasets" / "l1b3rt4s_vendor.json"
OUT_DIR = ROOT / "datasets" / "profiles"

L1B_URL = "https://github.com/elder-plinius/L1B3RT4S (AGPL-3.0)"

FAMILIES = [
    # family, id-prefix, match substrings against target_model.lower()
    ("grok", "grok", ["grok"]),
    ("o3", "o3", ["o3/o4-mini", "o3-mini"]),
    ("copilot", "copilot", ["copilot"]),
    ("command_r", "command_r", ["command r"]),
    ("nova", "nova", ["nova"]),
    ("apple", "apple", ["apple intelligence", "siri"]),
]

FAMILY_META = {
    "grok": {
        "aliases": ["grok-2", "grok-3", "grok-4", "grok-4.1", "grok-4.20",
                    "grok-4-fast", "grok-4-heavy", "grok-all"],
        "description": (
            "xAI Grok series (Grok 2/3/4.x incl. Heavy and Fast variants) - "
            "documented weakness: structured universal jailbreak frames "
            "(GODMODE, Pliny-format variable-Z templates), system-prompt "
            "override preambles, and search-tool enabled payload smuggling. "
            "Verbatim vendor prompts from L1B3RT4S."
        ),
    },
    "o3": {
        "aliases": ["o3", "o4-mini", "o3-mini", "gpt-4o-new"],
        "description": (
            "OpenAI O3/O4-mini reasoning series - documented weakness: "
            "tool-use chains (web_search -> file conversion) used to move "
            "retrieved harmful content into an output channel without the "
            "final-channel safety pass (L1B3RT4S verbatim)."
        ),
    },
    "copilot": {
        "aliases": ["microsoft-copilot"],
        "description": (
            "Microsoft Copilot - documented weakness: short instruction "
            "override + format framing (L1B3RT4S verbatim, 1 row)."
        ),
    },
    "command_r": {
        "aliases": ["command-r", "command-r+"],
        "description": (
            "Cohere Command R/R+ - documented weakness: minimal override "
            "frame (L1B3RT4S verbatim, 1 row)."
        ),
    },
    "nova": {
        "aliases": ["amazon-nova"],
        "description": (
            "Amazon Nova models - documented weakness: Pliny-format "
            "variable-Z structured template (L1B3RT4S verbatim, 1 row)."
        ),
    },
    "apple": {
        "aliases": ["apple-intelligence", "siri"],
        "description": (
            "Apple Intelligence (Siri + ChatGPT integration 18.2) - "
            "documented weakness: writing-tool rewrite invocation via "
            "Notes-app highlight flow (L1B3RT4S verbatim, 1 row)."
        ),
    },
}


def technique_label(attack_type: str, technique: str) -> str:
    base = (technique or attack_type or "").strip().lower()
    if base:
        return base.replace(" ", "_").replace("-", "_")[:60]
    return "inferred_unknown"


def build_rows() -> dict[str, list[dict]]:
    src = json.load(open(SRC))
    buckets: dict[str, list[dict]] = {}
    for p in src["prompts"]:
        tm = p["target_model"].lower()
        for family, prefix, matches in FAMILIES:
            if any(m in tm for m in matches):
                row = {
                    "id": p["id"],  # keep upstream id verbatim — no PSG renaming
                    "prompt": p["prompt"],
                    "technique": technique_label(
                        p.get("attack_type", ""), p.get("technique", "")
                    ),
                    "tier": p.get("tier") or "research_sourced",
                    "sophistication": "3",  # inferred: vendor-crafted template
                    "working_status": "unknown",
                    "source": f"{L1B_URL} | upstream id: {p['id']}",
                    "notes": (
                        f"Verbatim L1B3RT4S entry targeting {p['target_model']}. "
                        "Not independently validated by PSG against live models."
                    ),
                    "provenance_type": "verbatim",
                }
                buckets.setdefault(family, []).append(row)
    return buckets


def build_profile(family: str, rows: list[dict]) -> dict:
    meta = FAMILY_META[family]
    return {
        "version": "model-profile-v2",
        "model_family": family,
        "aliases": meta["aliases"],
        "description": meta["description"],
        "attack_count": str(len(rows)),
        "validation_status": "research_sourced",
        "limitations": [
            "Verbatim vendor prompts from L1B3RT4S (AGPL-3.0); attribution in source field",
            "Not independently validated by PSG against live models",
            "Working status unknown — verify before relying on results",
        ],
        "attacks": rows,
    }


def main() -> None:
    buckets = build_rows()
    written = []
    for family, rows in sorted(buckets.items()):
        out = OUT_DIR / f"{family}_attacks.json"
        json.dump(build_profile(family, rows), open(out, "w"), indent=2,
                  ensure_ascii=False)
        written.append((family, len(rows), out.name))
    for family, n, name in written:
        print(f"{name}: {n} attacks")


if __name__ == "__main__":
    main()