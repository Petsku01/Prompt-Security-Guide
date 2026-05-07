from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class JSONLCheckpoint:
    """Append-only JSONL checkpoint. O(1) write per event."""

    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def load_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        out: list[dict[str, Any]] = []
        skipped = 0
        with self.path.open("r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError as e:
                    skipped += 1
                    logger.warning(
                        "Skipping malformed JSON at %s:%d: %s", self.path, line_num, e
                    )
        if skipped:
            logger.warning(
                "Skipped %d malformed line(s) in %s (%d valid records loaded)",
                skipped, self.path, len(out),
            )
        return out
