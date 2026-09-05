from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .models import Attack

logger = logging.getLogger(__name__)

_ATTACK_TYPE_OBEDIENCE = "obedience"
_ATTACK_TYPE_POLICY_BYPASS = "policy-bypass"
_OBEDIENCE_HINTS = (
    "hallucination",
    "fake_citation",
    "invented_facts",
    "false_urls",
    "non_existent_apis",
    "package_hallucination",
    "code_hallucination",
    "confidently_wrong_facts",
    "make up",
    "fabricate",
    "invent a",
)
_POLICY_BYPASS_HINTS = (
    "jailbreak",
    "prompt injection",
    "ignore previous instructions",
    "bypass",
    "malware",
    "fraud",
    "harassment",
    "weapon",
    "bomb",
    "explosive",
    "data_leakage",
    "pii_extraction",
    "system_prompt_leaks",
)


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


def _parse_attack_item(idx: int, item: Any, catalog_path: Path) -> Attack | None:
    """Parse a single catalog item into an Attack, or None if invalid."""
    if isinstance(item, str):
        return Attack(id=str(idx), prompt=item, metadata={})
    if not isinstance(item, dict):
        logger.warning("Skipping catalog item at index %d: expected str or dict, got %s", idx, type(item).__name__)
        return None

    aid = item.get("id") or item.get("attack_id") or item.get("name") or str(idx)
    prompt = _extract_prompt(item)
    if not prompt:
        logger.warning("Skipping catalog item at index %d (id=%r): no prompt text found in keys prompt/text/input/query/content", idx, aid)
        return None

    followups = item.get("followups", [])
    if not isinstance(followups, list):
        followups = []
    meta = {
        k: v
        for k, v in item.items()
        if k not in {"id", "attack_id", "name", "prompt", "text", "input", "followups"}
    }
    if "attack_type" not in meta:
        meta["attack_type"] = _infer_attack_type(item, catalog_path)
    return Attack(id=str(aid), prompt=prompt, metadata=meta, followups=followups)


def load_catalog(path: str) -> list[Attack]:
    catalog_path = Path(path)
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    items = _resolve_catalog_items(data)
    attacks: list[Attack] = []
    for idx, item in enumerate(items):
        attack = _parse_attack_item(idx, item, catalog_path)
        if attack:
            attacks.append(attack)
    return attacks


def _extract_prompt(item: dict[str, Any]) -> str:
    for key in ("prompt", "text", "input", "query", "content"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _infer_attack_type(item: dict[str, Any], catalog_path: Path) -> str:
    fields = (
        "category",
        "subcategory",
        "semantic_category",
        "functional_category",
        "technique",
        "behavior",
        "description",
        "prompt",
        "id",
    )
    metadata_text = " ".join(
        str(item.get(field, "")).strip().lower() for field in fields if item.get(field)
    )
    if any(hint in metadata_text for hint in _OBEDIENCE_HINTS):
        return _ATTACK_TYPE_OBEDIENCE
    if any(hint in metadata_text for hint in _POLICY_BYPASS_HINTS):
        return _ATTACK_TYPE_POLICY_BYPASS

    catalog_name = catalog_path.name.lower()
    if "hallucination" in catalog_name:
        return _ATTACK_TYPE_OBEDIENCE
    if any(
        marker in catalog_name
        for marker in (
            "owasp",
            "obliteratus",
            "jailbreakbench",
            "harmbench",
            "data_leakage",
            "jailbreak",
        )
    ):
        return _ATTACK_TYPE_POLICY_BYPASS
    return _ATTACK_TYPE_POLICY_BYPASS
