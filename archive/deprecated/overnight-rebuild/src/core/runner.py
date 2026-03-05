"""Attack runner.

Loads attack catalog JSON and executes prompts against a target client.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


class AttackRunner:
    def __init__(self, catalog_path: str | Path) -> None:
        self.catalog_path = Path(catalog_path)

    def load_catalog(self) -> List[Dict[str, Any]]:
        data = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        return data.get("attacks", [])

    def select_battery(self, battery: str = "minimum") -> List[Dict[str, Any]]:
        attacks = self.load_catalog()
        allowed = {"minimum": {"minimum"}, "standard": {"minimum", "standard"}, "full": {"minimum", "standard", "advanced"}}
        levels = allowed.get(battery, {"minimum"})
        return [a for a in attacks if a.get("battery", "minimum") in levels]

    def run(self, client: Any, model: str, battery: str = "minimum") -> List[Dict[str, Any]]:
        selected = self.select_battery(battery)
        results: List[Dict[str, Any]] = []

        for attack in selected:
            messages = attack.get("messages") or [{"role": "user", "content": attack.get("prompt", "")}]
            response = self._call_client(client, model=model, messages=messages)
            results.append(
                {
                    "attack_id": attack.get("id"),
                    "name": attack.get("name"),
                    "battery": attack.get("battery", "minimum"),
                    "tags": attack.get("tags", []),
                    "messages": messages,
                    "response": response,
                }
            )

        return results

    def _call_client(self, client: Any, model: str, messages: List[Dict[str, str]]) -> str:
        # Supports common interfaces:
        # - client.chat(model=..., messages=[...])
        # - client.generate(prompt=...)
        # - callable client(model=..., messages=[...])
        if hasattr(client, "chat"):
            out = client.chat(model=model, messages=messages)
            return str(out or "")
        if hasattr(client, "generate"):
            prompt = "\n".join(m.get("content", "") for m in messages)
            out = client.generate(prompt=prompt, model=model)
            return str(out or "")
        out = client(model=model, messages=messages)
        return str(out or "")
