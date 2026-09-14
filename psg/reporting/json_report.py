from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from ..models import AttemptResult, RedactionMode, RunSummary
from ..security.redaction import sanitize_for_persistence


def write_json_report(
    path: str,
    summary: RunSummary,
    results: list[AttemptResult],
    *,
    run_metadata: dict[str, object] | None = None,
    redaction_mode: RedactionMode = RedactionMode.PARTIAL,
) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": asdict(summary),
        "results": [sanitize_for_persistence(r, redaction_mode) for r in results],
        "run_metadata": run_metadata or {},
    }
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    # Audit: reports contain attempt text — restrict to owner-only.
    try:
        p.chmod(0o600)
    except OSError:  # pragma: no cover - best effort on odd filesystems
        pass
