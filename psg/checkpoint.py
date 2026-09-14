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
        # Audit: checkpoints contain model responses — restrict to owner-only.
        if self.path.exists():
            try:
                self.path.chmod(0o600)
            except OSError:  # pragma: no cover - best effort on odd filesystems
                logger.debug("chmod 0600 failed for %s", self.path)

    def append(self, record: dict[str, Any]) -> None:
        # Audit: first write creates the file — ensure owner-only permissions
        # before/after creating it (umask-independent).
        created = not self.path.exists()
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        if created:
            try:
                self.path.chmod(0o600)
            except OSError:  # pragma: no cover - best effort on odd filesystems
                logger.debug("chmod 0600 failed for %s", self.path)

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
                skipped,
                self.path,
                len(out),
            )
        return out
