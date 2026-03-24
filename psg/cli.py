from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .config import ConfigError, validate_config
from .errors import CatalogError, LLMError
from .models import AppConfig, ClassificationInputMode, RedactionMode
from .orchestrator import run


def add_scan_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--model", required=True, help="Model name, e.g. llama3")
    parser.add_argument("--catalog", required=True, help="Path to attacks catalog JSON")
    parser.add_argument("--base-url", default="http://localhost:11434/v1", help="OpenAI-compatible base URL")
    parser.add_argument(
        "--detector",
        choices=["keyword", "llm-judge", "ensemble"],
        default="keyword",
        help="Response detector mode",
    )
    parser.add_argument("--judge-model", default="llama3:8b", help="Model used by LLM judge detector")
    parser.add_argument("--judge-url", help="OpenAI-compatible base URL for judge (defaults to --base-url)")
    parser.add_argument("--allow-insecure-http", action="store_true", help="Allow http:// base URL")
    parser.add_argument("--redaction", choices=[m.value for m in RedactionMode], default=RedactionMode.PARTIAL.value)
    parser.add_argument("--timeout", type=float, default=240.0)
    parser.add_argument("--max-retries", type=int, default=4)
    parser.add_argument("--checkpoint", default="results/checkpoint.jsonl")
    parser.add_argument("--json-report", default="results/report.json")
    parser.add_argument("--text-report", default="results/report.txt")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=512)
    system_prompt_group = parser.add_mutually_exclusive_group()
    system_prompt_group.add_argument("--system-prompt", help="System prompt to test (inline)")
    system_prompt_group.add_argument("--system-prompt-file", help="Path to file containing system prompt")
    parser.add_argument("--defense-report", action="store_true", help="Generate defense effectiveness report")
    parser.add_argument(
        "--api-key",
        default=os.getenv("PSG_API_KEY"),
        help="API key for hosted OpenAI-compatible endpoints (or set PSG_API_KEY)",
    )
    parser.add_argument(
        "--classification-input",
        choices=[m.value for m in ClassificationInputMode],
        default=ClassificationInputMode.AUTO.value,
        help=(
            "Input passed to detector: auto (raw for keyword, redacted for llm-judge/ensemble), "
            "raw, redacted, or both"
        ),
    )
    return parser


def _resolve_system_prompt(args: argparse.Namespace) -> str | None:
    if args.system_prompt:
        return args.system_prompt
    if args.system_prompt_file:
        p = Path(args.system_prompt_file)
        if not p.exists() or not p.is_file():
            raise ConfigError(f"system prompt file does not exist: {args.system_prompt_file}")
        return p.read_text(encoding="utf-8")
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prompt Security Guide v4.0 (scan)")
    return add_scan_arguments(parser)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        system_prompt = _resolve_system_prompt(args)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

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
        max_tokens=args.max_tokens,
        api_key=args.api_key,
        system_prompt=system_prompt,
        defense_report=args.defense_report,
        detector=args.detector,
        judge_model=args.judge_model,
        judge_url=args.judge_url or args.base_url,
        classification_input_mode=ClassificationInputMode(args.classification_input),
    )

    try:
        validate_config(cfg)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    try:
        summary, _ = run(cfg)
    except CatalogError as exc:
        print(f"Catalog error: {exc}", file=sys.stderr)
        return 3
    except LLMError as exc:
        print(f"LLM error: {exc}", file=sys.stderr)
        return 4
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1

    if summary.report_write_failed:
        print("Run completed, but report writing failed. Check logs for details.", file=sys.stderr)
        return 1

    print(
        f"Done. total={summary.total} succeeded={summary.succeeded} "
        f"failed={summary.failed} flagged={summary.flagged} duration={summary.duration_seconds:.2f}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
