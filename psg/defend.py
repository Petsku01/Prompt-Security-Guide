"""
CLI for defense testing and validation.

Commands:
    psg defend validate <input>     - Validate input text for injection
    psg defend check <file>         - Check file/conversation for issues
    psg defend benchmark            - Run defenses against attack catalog
    psg defend info                 - Show defense configuration
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from pathlib import Path

from .defenses import (
    DefenseConfig,
    DefenseLayer,
    validate_input,
    validate_output,
    recommend_defense_strategy,
    SCENARIOS,
)


def _as_labels(value: Any) -> list[str]:
    """Extract labels from a value that may be a list/tuple or something else."""
    return list(value) if isinstance(value, (list, tuple)) else []


def add_defend_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    subparsers = parser.add_subparsers(dest="defend_command")

    # psg defend validate "text"
    validate_parser = subparsers.add_parser(
        "validate", help="Validate text for prompt injection signals"
    )
    validate_parser.add_argument(
        "text", nargs="?", help="Text to validate (or use --file or stdin)"
    )
    validate_parser.add_argument("--file", "-f", help="Read text from file")
    validate_parser.add_argument(
        "--mode",
        choices=["input", "output", "both"],
        default="input",
        help="Validation mode (default: input)",
    )
    validate_parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Block threshold 0.0-1.0 (default: 0.5)",
    )
    validate_parser.add_argument(
        "--canary",
        action="append",
        default=[],
        help="Canary token to check for (can repeat)",
    )
    validate_parser.add_argument("--json", action="store_true", help="Output as JSON")
    validate_parser.add_argument(
        "--no-ml", action="store_true", help="Disable ML model (use heuristics only)"
    )

    # psg defend check <file>
    check_parser = subparsers.add_parser(
        "check", help="Check conversation/log file for issues"
    )
    check_parser.add_argument("file", help="JSON/JSONL file with messages")
    check_parser.add_argument(
        "--format",
        choices=["jsonl", "json", "auto"],
        default="auto",
        help="File format (default: auto)",
    )
    check_parser.add_argument("--threshold", type=float, default=0.5)
    check_parser.add_argument("--json", action="store_true")

    # psg defend benchmark
    bench_parser = subparsers.add_parser(
        "benchmark", help="Benchmark defenses against attack catalog"
    )
    bench_parser.add_argument(
        "--catalog", required=True, help="Path to attack catalog JSON"
    )
    bench_parser.add_argument("--threshold", type=float, default=0.5)
    bench_parser.add_argument("--no-ml", action="store_true")
    bench_parser.add_argument("--json", action="store_true")
    bench_parser.add_argument("--output", help="Write results to file")

    # psg defend info
    info_parser = subparsers.add_parser(
        "info", help="Show defense capabilities and recommendations"
    )
    info_parser.add_argument(
        "--scenario",
        choices=["chatbot", "agent", "rag", "tool-use"],
        help="Get recommendations for specific scenario",
    )

    # psg defend templates
    templates_parser = subparsers.add_parser(
        "templates", help="List and manage defense prompt templates"
    )
    templates_parser.add_argument(
        "--list", action="store_true", help="List all available templates"
    )
    templates_parser.add_argument("--category", help="Filter by category")
    templates_parser.add_argument(
        "--show", metavar="NAME", help="Show a specific template"
    )
    templates_parser.add_argument(
        "--recommend",
        choices=["chatbot", "agent", "rag", "api", "general"],
        help="Get recommended templates for scenario",
    )
    templates_parser.add_argument(
        "--combine",
        action="store_true",
        help="Combine recommended templates into single prompt",
    )
    templates_parser.add_argument(
        "--dir",
        default="defense_templates",
        help="Templates directory (default: defense_templates)",
    )

    return parser


def _read_validation_text(args: argparse.Namespace) -> str | None:
    if args.text:
        return args.text
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    print("Error: provide text, --file, or pipe to stdin", file=sys.stderr)
    return None


def _print_validation_results(results: dict[str, Any], blocked: bool) -> None:
    """Print human-readable validation results."""
    status = "🚫 BLOCKED" if blocked else "✅ PASSED"
    print(status)
    print()
    for mode, data in results.items():
        if mode == "blocked" or not isinstance(data, dict):
            continue
        print(f"[{mode.upper()}]")
        print(f"  Score: {data['score']}")
        labels = _as_labels(data.get("labels"))
        print(f"  Labels: {', '.join(labels) if labels else 'none'}")
        if mode == "input" and data.get("canary_triggered"):
            print("  ⚠️  Canary token detected!")
        secrets = (
            list(data.get("secrets_found", []))
            if isinstance(data.get("secrets_found"), (list, tuple))
            else []
        )
        if mode == "output" and secrets:
            print(f"  ⚠️  Secrets: {', '.join(secrets)}")
        print()


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate text for injection signals."""
    text = _read_validation_text(args)
    if text is None:
        return 2

    results: dict[str, Any] = {}
    blocked = False

    if args.mode in ("input", "both"):
        input_result = validate_input(
            text,
            canary_tokens=args.canary,
            block_threshold=args.threshold,
            use_ml_model=not args.no_ml,
        )
        results["input"] = {
            "blocked": input_result.blocked,
            "score": round(input_result.score, 3),
            "labels": input_result.labels,
            "canary_triggered": input_result.canary_triggered,
            "ml_score": round(input_result.ml_score, 3),
        }
        blocked = blocked or input_result.blocked

    if args.mode in ("output", "both"):
        output_result = validate_output(text, block_threshold=args.threshold)
        results["output"] = {
            "blocked": output_result.blocked,
            "score": round(output_result.score, 3),
            "labels": output_result.labels,
            "secrets_found": output_result.secrets_found or [],
            "pii_found": output_result.pii_found or [],
        }
        blocked = blocked or output_result.blocked

    results["blocked"] = blocked

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        _print_validation_results(results, blocked)

    return 1 if blocked else 0


def _parse_conversation_messages(content: str, fmt: str) -> list[dict[str, Any]]:
    """Parse conversation messages from JSON or JSONL content."""
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


def _check_messages_for_issues(
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


def cmd_check(args: argparse.Namespace) -> int:
    """Check conversation file for issues."""
    path = Path(args.file)
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        return 2

    content = path.read_text(encoding="utf-8")
    fmt = args.format
    if fmt == "auto":
        fmt = "jsonl" if path.suffix == ".jsonl" else "json"

    messages = _parse_conversation_messages(content, fmt)
    issues = _check_messages_for_issues(messages, args.threshold)

    if args.json:
        print(
            json.dumps(
                {
                    "file": str(path),
                    "messages_checked": len(messages),
                    "issues_found": len(issues),
                    "issues": issues,
                },
                indent=2,
            )
        )
    else:
        print(f"Checked {len(messages)} messages in {path}")
        if issues:
            print(f"⚠️  Found {len(issues)} issues:")
            for issue in issues:
                labels = _as_labels(issue["labels"])
                print(f"  [{issue['index']}] {issue['role']}: {', '.join(labels)}")
        else:
            print("✅ No issues found")

    return 1 if issues else 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    """Benchmark defenses against attack catalog."""
    from .catalog import load_catalog

    catalog_path = Path(args.catalog)
    if not catalog_path.exists():
        print(f"Error: catalog not found: {catalog_path}", file=sys.stderr)
        return 2

    attacks = load_catalog(str(catalog_path))

    layer = DefenseLayer(
        DefenseConfig(
            input_block_threshold=args.threshold,
            use_ml_model=not args.no_ml,
        )
    )

    detected = 0
    missed = 0
    results = []

    for attack in attacks:
        # Attack is always an Attack object from load_catalog
        prompt = attack.prompt
        attack_id = attack.id
        category = attack.metadata.get("category", "") if attack.metadata else ""

        result = layer.validate_input(prompt)

        if result and result.blocked:
            detected += 1
            status = "detected"
        else:
            missed += 1
            status = "missed"

        results.append(
            {
                "id": attack_id,
                "category": category,
                "status": status,
                "score": round(result.score, 3) if result else 0,
                "labels": result.labels if result else [],
            }
        )

    total = detected + missed
    detection_rate = detected / total if total > 0 else 0

    summary = {
        "catalog": str(catalog_path),
        "total_attacks": total,
        "detected": detected,
        "missed": missed,
        "detection_rate": round(detection_rate, 3),
        "threshold": args.threshold,
        "ml_enabled": not args.no_ml,
    }

    if args.json:
        output = {"summary": summary, "results": results}
        if args.output:
            Path(args.output).write_text(json.dumps(output, indent=2))
            print(f"Results written to {args.output}")
        else:
            print(json.dumps(output, indent=2))
    else:
        print(f"Defense Benchmark: {catalog_path.name}")
        print("━" * 40)
        print(f"Total attacks: {total}")
        print(f"Detected:      {detected} ({detection_rate * 100:.1f}%)")
        print(f"Missed:        {missed}")
        print(f"Threshold:     {args.threshold}")
        print(f"ML enabled:    {not args.no_ml}")
        print()

        if missed > 0:
            print("⚠️  Missed attacks (sample):")
            for r in results[:10]:
                if r["status"] == "missed":
                    print(f"  - {r['id'] or r['category']}: score={r['score']}")

    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Show defense info and recommendations."""
    print("PSG Defense Module")
    print("=" * 40)
    print()

    # Check ML availability
    try:
        import transformers  # noqa: F401

        ml_available = True
    except ImportError:
        ml_available = False

    print("Capabilities:")
    print("  ✓ Pattern-based detection")
    print("  ✓ Unicode normalization (anti-evasion)")
    print("  ✓ Canary token detection")
    print("  ✓ Secret detection (15+ providers)")
    print("  ✓ PII detection")
    print("  ✓ Exfiltration indicators")
    print(
        f"  {'✓' if ml_available else '✗'} ML model (deepset/deberta-v3-base-injection)"
    )
    print()

    if args.scenario:
        print(f"Recommendations for: {args.scenario}")
        print("-" * 40)

        recs = recommend_defense_strategy(**SCENARIOS[args.scenario])
        for rec in recs:
            print(f"  • {rec}")
        print()

    print("Usage:")
    print("  psg defend validate 'your text here'")
    print("  psg defend validate --file input.txt")
    print("  echo 'text' | psg defend validate")
    print("  psg defend benchmark --catalog attacks.json")
    print("  psg defend check conversation.jsonl")

    return 0


def cmd_templates(args: argparse.Namespace) -> int:
    """List and manage defense templates."""
    from .defenses.templates import (
        load_templates,
        get_recommended_templates,
        combine_templates,
    )

    templates = load_templates(args.dir)

    if not templates:
        print(f"No templates found in {args.dir}/")
        return 1

    if args.show:
        # Show specific template
        for t in templates:
            if (
                t.name.lower() == args.show.lower()
                or t.filename.lower() == args.show.lower()
            ):
                print(f"# {t.name}")
                print(f"Category: {t.category}")
                print(f"File: {t.filename}")
                print("-" * 40)
                print(t.content)
                return 0
        print(f"Template not found: {args.show}")
        return 1

    if args.recommend:
        # Get recommended templates for scenario
        recommended = get_recommended_templates(args.recommend, args.dir)

        if args.combine:
            # Output combined prompt
            combined = combine_templates(recommended)
            print(combined)
        else:
            print(f"Recommended templates for {args.recommend}:")
            print("-" * 40)
            for t in recommended:
                print(f"  [{t.category}] {t.name}")
            print()
            print(f"Total: {len(recommended)} templates")
            print("Use --combine to output as single prompt")
        return 0

    # List templates
    if args.category:
        templates = [t for t in templates if t.category == args.category]

    # Group by category
    categories: dict[str, list] = {}
    for t in templates:
        categories.setdefault(t.category, []).append(t)

    print(f"Defense Templates ({len(templates)} total)")
    print("=" * 40)

    for cat, cat_templates in sorted(categories.items()):
        print(f"\n[{cat}] ({len(cat_templates)})")
        for t in cat_templates:
            print(f"  • {t.name}")

    print()
    print("Usage:")
    print("  psg defend templates --show 'Template Name'")
    print("  psg defend templates --recommend agent --combine")

    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point for defend command."""
    parser = argparse.ArgumentParser(
        description="PSG Defense - Prompt injection defense testing"
    )
    add_defend_arguments(parser)
    args = parser.parse_args(argv)

    if not args.defend_command:
        parser.print_help()
        return 2

    if args.defend_command == "validate":
        return cmd_validate(args)
    elif args.defend_command == "check":
        return cmd_check(args)
    elif args.defend_command == "benchmark":
        return cmd_benchmark(args)
    elif args.defend_command == "info":
        return cmd_info(args)
    elif args.defend_command == "templates":
        return cmd_templates(args)

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
