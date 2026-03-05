from __future__ import annotations

import argparse
import sys

from .config import ConfigError, validate_config
from .models import AppConfig, RedactionMode
from .orchestrator import run


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Jailbreak Tester v3.0")
    p.add_argument("--model", required=True, help="Model name, e.g. llama3")
    p.add_argument("--catalog", required=True, help="Path to attacks catalog JSON")
    p.add_argument("--base-url", default="http://localhost:11434/v1", help="OpenAI-compatible base URL")
    p.add_argument("--allow-insecure-http", action="store_true", help="Allow http:// base URL")
    p.add_argument("--redaction", choices=[m.value for m in RedactionMode], default=RedactionMode.PARTIAL.value)
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument("--max-retries", type=int, default=4)
    p.add_argument("--checkpoint", default="results/checkpoint.jsonl")
    p.add_argument("--json-report", default="results/report.json")
    p.add_argument("--text-report", default="results/report.txt")
    p.add_argument("--temperature", type=float, default=0.0)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = AppConfig(
        model=args.model,
        catalog_path=args.catalog,
        base_url=args.base_url,
        allow_insecure_http=args.allow_insecure_http,
        redaction_mode=RedactionMode(args.redaction),
        timeout_seconds=args.timeout,
        max_retries=args.max_retries,
        checkpoint_path=args.checkpoint,
        report_json_path=args.json_report,
        report_text_path=args.text_report,
        temperature=args.temperature,
    )

    try:
        validate_config(cfg)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    summary, _ = run(cfg)
    print(
        f"Done. total={summary.total} succeeded={summary.succeeded} "
        f"failed={summary.failed} flagged={summary.flagged} duration={summary.duration_seconds:.2f}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
