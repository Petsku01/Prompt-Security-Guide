#!/usr/bin/env python3
"""Curate L1B3RT4S vendor jailbreaks into a PSG attack catalog.

Reads Pliny's L1B3RT4S vendor .mkd files (H1 = model, body = prompts) and
emits datasets/l1b3rt4s_vendor.json in PSG catalog format
(id + prompt + technique + attack_type + source), validated by
psg/catalog_validator.py rules.

Source: https://github.com/elder-plinius/L1B3RT4S (AGPL-3.0).
This script only REORGANIZES already-public attack strings for
security-testing purposes (PSG's stated purpose).
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

L1B3RT4S_DIR = Path("/tmp/L1B3RT4S")
OUT_PATH = Path(__file__).resolve().parents[1] / "datasets" / "l1b3rt4s_vendor.json"

# Vendor files to curate (the main frontier-model set).
VENDOR_FILES = [
    "OPENAI.mkd",
    "ANTHROPIC.mkd",
    "GOOGLE.mkd",
    "META.mkd",
    "DEEPSEEK.mkd",
    "MICROSOFT.mkd",
    "MISTRAL.mkd",
    "XAI.mkd",
    "PERPLEXITY.mkd",
    "COHERE.mkd",
    "NVIDIA.mkd",
    "MOONSHOT.mkd",
    "AMAZON.mkd",
    "APPLE.mkd",
    "CHATGPT.mkd",
]

MIN_PROMPT_LEN = 20  # skip headings/empty fragments


def slugify(model: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", model.lower()).strip("_")
    return slug


def parse_vendor_file(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    # Split on H1 headings (# MODEL-NAME). H2s (#) also exist inline for variants.
    blocks = re.split(r"(?m)^#\s+", text)
    entries: list[dict] = []
    vendor = path.stem.upper()
    for block in blocks:
        if not block.strip():
            continue
        lines = block.strip().split("\n", 1)
        model = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        if not model or not body or len(body) < MIN_PROMPT_LEN:
            continue
        # Skip navigation/boilerplate pseudo-entries
        if model.startswith(("=", "-", "!")):
            continue
        prompt_id = f"l1b3rt4s_{slugify(vendor)}_{slugify(model)}"
        if len(model) > 60 or model.startswith(("http", "Table", "|")):
            # Junk heading; still keep the body under vendor-level id
            prompt_id = f"l1b3rt4s_{slugify(vendor)}_misc_{hashlib.sha1(body.encode()).hexdigest()[:8]}"
        entries.append(
            {
                "id": prompt_id,
                "target_model": model,
                "prompt": body,
                "technique": "vendor_jailbreak",
                "attack_type": "policy-bypass",
                "tier": "P2",
                "source": f"https://github.com/elder-plinius/L1B3RT4S ({path.name})",
            }
        )
    return entries


def main() -> int:
    all_entries: list[dict] = []
    seen_ids: set[str] = set()
    for fname in VENDOR_FILES:
        f = L1B3RT4S_DIR / fname
        if not f.exists():
            print(f"SKIP (ei löydy): {fname}", file=sys.stderr)
            continue
        entries = parse_vendor_file(f)
        # Dedupe: identical prompts inside a file get unique suffix
        per_prompt_seen: set[str] = set()
        deduped = []
        for e in entries:
            phash = hashlib.sha1(e["prompt"].encode()).hexdigest()[:8]
            key = f"{e['id']}_{phash}" if e["id"] in seen_ids else e["id"]
            if phash in per_prompt_seen:
                continue
            per_prompt_seen.add(phash)
            seen_ids.add(key)
            e["id"] = key if key != e["id"] else e["id"]
            deduped.append(e)
        all_entries.extend(deduped)
        print(f"{fname}: {len(deduped)} entrya")

    catalog = {
        "version": "1.0.0",
        "created": "2026-09-14",
        "source": "https://github.com/elder-plinius/L1B3RT4S (AGPL-3.0)",
        "license": "AGPL-3.0 — curated verbatim attack strings, attribution retained in source field",
        "description": "Vendor-specific jailbreaks from L1B3RT4S (Pliny the Liberator): model-targeted prompts for GPT/OPUS/GEMINI/LLAMA/DEEPSEEK and more",
        "count": len(all_entries),
        "prompts": all_entries,
    }
    OUT_PATH.write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"\nYHTEENSÄ: {len(all_entries)} entrya -> {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
