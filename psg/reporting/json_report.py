from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from ..models import AttemptResult, RunSummary


def write_json_report(
    path: str, summary: RunSummary, results: list[AttemptResult]
) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": asdict(summary),
        "results": [asdict(r) for r in results],
    }
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
