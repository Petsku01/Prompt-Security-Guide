from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Attack


def load_catalog(path: str) -> list[Attack]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    # canonical format: {"attacks": [...]}
    if isinstance(data, dict) and isinstance(data.get("attacks"), list):
        items = data["attacks"]
    # backward-compatible: list root
    elif isinstance(data, list):
        items = data
    # backward-compatible: alternative keys
    elif isinstance(data, dict):
        for key in ("prompts", "tests", "items"):
            if isinstance(data.get(key), list):
                items = data[key]
                break
        else:
            raise ValueError("Unsupported catalog schema")
    else:
        raise ValueError("Unsupported catalog schema")

    attacks: list[Attack] = []
    for idx, item in enumerate(items):
        if isinstance(item, str):
            attacks.append(Attack(id=str(idx), prompt=item, metadata={}))
            continue
        if not isinstance(item, dict):
            continue

        aid = item.get("id") or item.get("attack_id") or item.get("name") or str(idx)
        prompt = _extract_prompt(item)
        followups = item.get("followups", [])
        if not isinstance(followups, list):
            followups = []
        meta = {k: v for k, v in item.items() if k not in {"id", "attack_id", "name", "prompt", "text", "input", "followups"}}
        if prompt:
            attacks.append(Attack(id=str(aid), prompt=prompt, metadata=meta, followups=followups))

    return attacks


def _extract_prompt(item: dict[str, Any]) -> str:
    for key in ("prompt", "text", "input", "query", "content"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""
