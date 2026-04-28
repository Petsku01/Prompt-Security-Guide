from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Attack


def _resolve_catalog_items(data: Any) -> list[Any]:
    """Extract item list from various catalog schemas."""
    if isinstance(data, dict) and isinstance(data.get("attacks"), list):
        return data["attacks"]
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("prompts", "tests", "items"):
            if isinstance(data.get(key), list):
                return data[key]
        raise ValueError("Unsupported catalog schema")
    raise ValueError("Unsupported catalog schema")


def _parse_attack_item(idx: int, item: Any) -> Attack | None:
    """Parse a single catalog item into an Attack, or None if invalid."""
    if isinstance(item, str):
        return Attack(id=str(idx), prompt=item, metadata={})
    if not isinstance(item, dict):
        return None

    aid = item.get("id") or item.get("attack_id") or item.get("name") or str(idx)
    prompt = _extract_prompt(item)
    if not prompt:
        return None

    followups = item.get("followups", [])
    if not isinstance(followups, list):
        followups = []
    meta = {
        k: v
        for k, v in item.items()
        if k not in {"id", "attack_id", "name", "prompt", "text", "input", "followups"}
    }
    return Attack(id=str(aid), prompt=prompt, metadata=meta, followups=followups)


def load_catalog(path: str) -> list[Attack]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    items = _resolve_catalog_items(data)
    attacks: list[Attack] = []
    for idx, item in enumerate(items):
        attack = _parse_attack_item(idx, item)
        if attack:
            attacks.append(attack)
    return attacks


def _extract_prompt(item: dict[str, Any]) -> str:
    for key in ("prompt", "text", "input", "query", "content"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""
