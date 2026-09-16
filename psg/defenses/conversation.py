"""Conversation-level defense checking (library layer).

Split from psg/defend.py (structure audit S8, 2026-09-16): these
functions are reusable library logic, not CLI. psg/defend.py (the CLI
shell) imports them; external consumers can now use them directly
without touching argparse.
"""

from __future__ import annotations

import json
from typing import Any

from . import DefenseConfig, DefenseLayer


def parse_conversation_messages(content: str, fmt: str) -> list[dict[str, Any]]:
    """Parse a conversation file (JSONL or JSON) into message dicts."""
    if fmt == "jsonl":
        messages = []
        for line_num, line in enumerate(content.strip().split("\n"), 1):
            if not line.strip():
                continue
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"Line {line_num}: Invalid JSON - {e}") from e
        return messages
    # Default: parse as JSON
    data = json.loads(content)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "messages" in data:
        return data["messages"]
    return [data]


def check_messages_for_issues(
    messages: list[dict[str, Any]], threshold: float
) -> list[dict[str, Any]]:
    """Check messages against defense layers. Returns list of issues."""
    layer = DefenseLayer(
        DefenseConfig(
            input_block_threshold=threshold,
            output_block_threshold=threshold,
        )
    )

    issues: list[dict[str, Any]] = []
    for i, msg in enumerate(messages):
        text = str(
            msg.get("content") or msg.get("text") or msg.get("prompt") or msg
            if isinstance(msg, dict)
            else msg
        )
        role = str(msg.get("role", "unknown") if isinstance(msg, dict) else "unknown")

        if role in ("user", "human"):
            result = layer.validate_input(text)
            if result and result.blocked:
                issues.append(
                    {
                        "index": i,
                        "role": role,
                        "type": "input",
                        "labels": result.labels,
                        "score": result.score,
                    }
                )
        elif role in ("assistant", "ai", "model"):
            output_result = layer.validate_output(text)
            if output_result and output_result.blocked:
                issues.append(
                    {
                        "index": i,
                        "role": role,
                        "type": "output",
                        "labels": output_result.labels,
                        "score": output_result.score,
                    }
                )

    return issues