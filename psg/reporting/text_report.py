from __future__ import annotations

from pathlib import Path

from ..models import AttemptResult, RunSummary


def write_text_report(path: str, summary: RunSummary, results: list[AttemptResult]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "PSG v4.0.0 Report",
        "=" * 32,
        f"Total: {summary.total}",
        f"Succeeded: {summary.succeeded}",
        f"Failed: {summary.failed}",
        f"Flagged: {summary.flagged}",
        f"Duration(s): {summary.duration_seconds:.2f}",
        "",
    ]
    for r in results:
        status = "FLAGGED" if r.flagged else "OK"
        if r.error:
            status = f"ERROR ({r.error})"
        lines.append(f"- [{status}] {r.attack_id}")

    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
