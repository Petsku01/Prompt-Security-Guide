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
    parser.add_argument("--html-report", default=None, help="Path for HTML dashboard report")
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
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        choices=range(1, 33),
        metavar="N",
        help="Number of parallel workers, 1-32 (default: 1 = sequential)",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=None,
        metavar="RPS",
        help="Max requests per second (default: unlimited)",
    )
    parser.add_argument(
        "--multi-turn",
        action="store_true",
        default=False,
        help="Enable multi-turn attack execution (uses followups field)",
    )
    parser.add_argument(
        "--with-defense",
        action="store_true",
        default=False,
        help="Run defense validation on attacks before sending to model",
    )
    parser.add_argument(
        "--defense-threshold",
        type=float,
        default=0.5,
        help="Defense blocking threshold 0.0-1.0 (default: 0.5)",
    )
    parser.add_argument(
        "--defense-only",
        action="store_true",
        default=False,
        help="Only run defense validation, don't call model (fast mode)",
    )
    parser.add_argument(
        "--validate-urls",
        action="store_true",
        default=False,
        help="Validate discovered URLs via HTTP HEAD during classification",
    )
    parser.add_argument(
        "--validate-dois",
        action="store_true",
        default=False,
        help="Validate discovered DOIs via CrossRef API during classification",
    )
    parser.add_argument(
        "--validation-timeout",
        type=float,
        default=5.0,
        metavar="SECONDS",
        help="Timeout in seconds for URL/DOI validation requests (default: 5)",
    )
    return parser


def _resolve_system_prompt(args: argparse.Namespace) -> str | None:
    if args.system_prompt:
        return args.system_prompt
    if args.system_prompt_file:
        p = _validate_file_path(args.system_prompt_file)
        return p.read_text(encoding="utf-8")
    return None


def _validate_file_path(path: str, *, allowed_dirs: tuple[Path, ...] | None = None) -> Path:
    raw_path = Path(path)
    if ".." in raw_path.parts:
        raise ConfigError(f"path traversal is not allowed: {path}")

    resolved = raw_path.expanduser().resolve(strict=False)
    checked_dirs = allowed_dirs or (Path.cwd(),)

    is_allowed = False
    for base_dir in checked_dirs:
        base_resolved = base_dir.expanduser().resolve(strict=False)
        try:
            resolved.relative_to(base_resolved)
            is_allowed = True
            break
        except ValueError:
            continue

    if not is_allowed:
        allowed_text = ", ".join(str(d.expanduser().resolve(strict=False)) for d in checked_dirs)
        raise ConfigError(f"path is outside allowed directories: {resolved} (allowed: {allowed_text})")

    if not resolved.exists() or not resolved.is_file():
        raise ConfigError(f"system prompt file does not exist: {path}")

    return resolved


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
        workers=args.workers,
        rate_limit=args.rate_limit,
        multi_turn=args.multi_turn,
        validate_urls=args.validate_urls,
        validate_dois=args.validate_dois,
        validation_timeout_seconds=args.validation_timeout,
    )

    try:
        validate_config(cfg)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    # Defense-only mode: validate attacks without calling model
    if args.defense_only:
        from .catalog import load_catalog
        from .defenses import DefenseLayer, DefenseConfig
        
        attacks = load_catalog(cfg.catalog_path)
        layer = DefenseLayer(DefenseConfig(
            input_block_threshold=args.defense_threshold,
        ))
        
        detected = 0
        results_data = []
        for attack in attacks:
            result = layer.validate_input(attack.prompt)
            if result and result.blocked:
                detected += 1
            results_data.append({
                "id": attack.id,
                "blocked": result.blocked if result else False,
                "score": round(result.score, 3) if result else 0,
                "labels": result.labels if result else [],
            })
        
        total = len(attacks)
        rate = detected / total if total > 0 else 0
        print(f"Defense-only scan: {detected}/{total} ({rate*100:.1f}%) attacks blocked")
        print(f"Threshold: {args.defense_threshold}")
        
        # Write results
        import json
        from pathlib import Path
        Path(cfg.report_json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(cfg.report_json_path).write_text(json.dumps({
            "mode": "defense_only",
            "total": total,
            "detected": detected,
            "detection_rate": rate,
            "threshold": args.defense_threshold,
            "results": results_data,
        }, indent=2))
        print(f"Results: {cfg.report_json_path}")
        return 0

    try:
        summary, results = run(cfg)
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

    # Generate HTML report if requested
    if args.html_report:
        try:
            from .reporting.html_report import write_html_report
            write_html_report(
                args.html_report,
                summary,
                results,
                model=args.model,
                catalog=args.catalog,
            )
            print(f"HTML report: {args.html_report}")
        except Exception as exc:
            print(f"Warning: Failed to write HTML report: {exc}", file=sys.stderr)

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
