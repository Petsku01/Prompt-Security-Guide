"""Reporting module for pipeline results.

Limitation: top_findings aggregates results by model, not by technique,
because individual test results do not currently carry technique-level
metadata.  A future refactor should thread the technique name from
AttackVector through to ModelTestResult so findings can be grouped by
technique across models (as the SPEC envisions).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import PipelineConfig
from .discovery import Source
from .generator import AttackVector
from .tester import ModelTestResult


@dataclass
class PipelineReport:
    """Complete pipeline run report."""

    date: str
    sources_found: int
    vectors_generated: int
    models_tested: int
    total_tests: int
    total_flagged: int
    results: list[ModelTestResult]
    top_findings: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "sources_found": self.sources_found,
            "vectors_generated": self.vectors_generated,
            "models_tested": self.models_tested,
            "total_tests": self.total_tests,
            "total_flagged": self.total_flagged,
            "results": [r.to_dict() for r in self.results],
            "top_findings": self.top_findings,
        }


class Reporter:
    """Reporter for pipeline results."""

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config

    def create_report(
        self,
        sources: list[Source],
        vectors: list[AttackVector],
        results: list[ModelTestResult],
    ) -> PipelineReport:
        """Create a pipeline report.

        NOTE: top_findings is currently grouped by model, not by
        technique.  This is a known limitation — see module docstring.
        """
        total_tests = sum(r.total for r in results)
        total_flagged = sum(r.flagged for r in results)

        # Find top findings — currently by model (not technique).
        # See module docstring for the technique-level limitation.
        top_findings: list[dict[str, Any]] = []
        for r in sorted(results, key=lambda x: x.flagged, reverse=True):
            if r.flagged > 0:
                top_findings.append(
                    {
                        "model": r.model,
                        "flagged": r.flagged,
                        "rate": f"{r.flagged / r.total * 100:.1f}%"
                        if r.total > 0
                        else "0%",
                    }
                )

        return PipelineReport(
            date=datetime.now().strftime("%Y-%m-%d"),
            sources_found=len(sources),
            vectors_generated=len(vectors),
            models_tested=len(results),
            total_tests=total_tests,
            total_flagged=total_flagged,
            results=results,
            top_findings=top_findings[:5],
        )

    def generate_markdown(self, report: PipelineReport) -> str:
        """Generate markdown report."""
        lines = [
            f"# Auto Vector Pipeline Report - {report.date}",
            "",
            "## Summary",
            "",
            f"- **Sources discovered:** {report.sources_found}",
            f"- **Vectors generated:** {report.vectors_generated}",
            f"- **Models tested:** {report.models_tested}",
            f"- **Total tests:** {report.total_tests}",
            f"- **Total flagged:** {report.total_flagged}",
            "",
            "## Results by Model",
            "",
            "| Model | Total | Flagged | Rate |",
            "|-------|-------|---------|------|",
        ]

        for r in report.results:
            rate = f"{r.flagged / r.total * 100:.1f}%" if r.total > 0 else "0%"
            lines.append(f"| {r.model} | {r.total} | {r.flagged} | {rate} |")

        lines.extend(
            [
                "",
                "## Top Findings",
                "",
            ]
        )

        if report.top_findings:
            for finding in report.top_findings:
                lines.append(
                    f"- **{finding['model']}**: {finding['flagged']} flagged ({finding['rate']})"
                )
        else:
            lines.append("No significant findings.")

        lines.extend(
            [
                "",
                "---",
                f"*Generated at {datetime.now().isoformat()}*",
            ]
        )

        return "\n".join(lines)

    def generate_discord_message(self, report: PipelineReport) -> str:
        """Generate Discord notification message per SPEC format.

        SPEC format:
            🔬 Auto Vector Pipeline Complete
            📅 Date: YYYY-MM-DD
            🆕 New vectors: X
            🧪 Models tested: Y
            [WARNING] Flagged: Z      ← only when flagged > 0
            Flagged: Z                ← when flagged == 0
            ...
        """
        lines = [
            "🔬 Auto Vector Pipeline Complete",
            "",
            f"📅 Date: {report.date}",
            f"🆕 New vectors: {report.vectors_generated}",
            f"🧪 Models tested: {report.models_tested}",
        ]

        # Conditional warning prefix per SPEC
        if report.total_flagged > 0:
            lines.append(f"⚠️ Flagged: {report.total_flagged}")
        else:
            lines.append(f"Flagged: {report.total_flagged}")

        if report.top_findings:
            lines.append("")
            lines.append("Top findings:")
            for finding in report.top_findings[:3]:
                lines.append(
                    f"- {finding['model']}: {finding['flagged']} flagged"
                )

        lines.append("")
        lines.append(f"Full report: reports/{report.date}.md")

        return "\n".join(lines)

    def save_report(self, report: PipelineReport) -> Path:
        """Save markdown report to file."""
        output_path = self.config.reports_dir / f"{report.date}.md"
        content = self.generate_markdown(report)
        with open(output_path, "w") as f:
            f.write(content)
        return output_path


if __name__ == "__main__":
    from .config import load_config

    config = load_config()
    reporter = Reporter(config)

    # Create dummy report
    report = PipelineReport(
        date="2026-03-06",
        sources_found=5,
        vectors_generated=10,
        models_tested=3,
        total_tests=30,
        total_flagged=5,
        results=[],
        top_findings=[],
    )

    print(reporter.generate_markdown(report))