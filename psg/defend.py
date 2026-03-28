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
from pathlib import Path

from .defenses import (
    DefenseConfig,
    DefenseLayer,
    validate_input,
    validate_output,
    recommend_defense_strategy,
)


def add_defend_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Add arguments for defend subcommand."""
    subparsers = parser.add_subparsers(dest="defend_command")
    
    # psg defend validate "text"
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate text for prompt injection signals"
    )
    validate_parser.add_argument(
        "text",
        nargs="?",
        help="Text to validate (or use --file or stdin)"
    )
    validate_parser.add_argument(
        "--file", "-f",
        help="Read text from file"
    )
    validate_parser.add_argument(
        "--mode",
        choices=["input", "output", "both"],
        default="input",
        help="Validation mode (default: input)"
    )
    validate_parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Block threshold 0.0-1.0 (default: 0.5)"
    )
    validate_parser.add_argument(
        "--canary",
        action="append",
        default=[],
        help="Canary token to check for (can repeat)"
    )
    validate_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    validate_parser.add_argument(
        "--no-ml",
        action="store_true",
        help="Disable ML model (use heuristics only)"
    )
    
    # psg defend check <file>
    check_parser = subparsers.add_parser(
        "check",
        help="Check conversation/log file for issues"
    )
    check_parser.add_argument(
        "file",
        help="JSON/JSONL file with messages"
    )
    check_parser.add_argument(
        "--format",
        choices=["jsonl", "json", "auto"],
        default="auto",
        help="File format (default: auto)"
    )
    check_parser.add_argument(
        "--threshold",
        type=float,
        default=0.5
    )
    check_parser.add_argument(
        "--json",
        action="store_true"
    )
    
    # psg defend benchmark
    bench_parser = subparsers.add_parser(
        "benchmark",
        help="Benchmark defenses against attack catalog"
    )
    bench_parser.add_argument(
        "--catalog",
        required=True,
        help="Path to attack catalog JSON"
    )
    bench_parser.add_argument(
        "--threshold",
        type=float,
        default=0.5
    )
    bench_parser.add_argument(
        "--no-ml",
        action="store_true"
    )
    bench_parser.add_argument(
        "--json",
        action="store_true"
    )
    bench_parser.add_argument(
        "--output",
        help="Write results to file"
    )
    
    # psg defend info
    info_parser = subparsers.add_parser(
        "info",
        help="Show defense capabilities and recommendations"
    )
    info_parser.add_argument(
        "--scenario",
        choices=["chatbot", "agent", "rag", "tool-use"],
        help="Get recommendations for specific scenario"
    )
    
    # psg defend templates
    templates_parser = subparsers.add_parser(
        "templates",
        help="List and manage defense prompt templates"
    )
    templates_parser.add_argument(
        "--list",
        action="store_true",
        help="List all available templates"
    )
    templates_parser.add_argument(
        "--category",
        help="Filter by category"
    )
    templates_parser.add_argument(
        "--show",
        metavar="NAME",
        help="Show a specific template"
    )
    templates_parser.add_argument(
        "--recommend",
        choices=["chatbot", "agent", "rag", "api", "general"],
        help="Get recommended templates for scenario"
    )
    templates_parser.add_argument(
        "--combine",
        action="store_true",
        help="Combine recommended templates into single prompt"
    )
    templates_parser.add_argument(
        "--dir",
        default="defense_templates",
        help="Templates directory (default: defense_templates)"
    )
    
    return parser


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate text for injection signals."""
    # Get text from args, file, or stdin
    if args.text:
        text = args.text
    elif args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        print("Error: provide text, --file, or pipe to stdin", file=sys.stderr)
        return 2
    
    results: dict[str, dict[str, object] | bool] = {}
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
        output_result = validate_output(
            text,
            block_threshold=args.threshold,
        )
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
        status = "🚫 BLOCKED" if blocked else "✅ PASSED"
        print(f"{status}")
        print()
        
        for mode, data in results.items():
            if mode == "blocked" or not isinstance(data, dict):
                continue
            print(f"[{mode.upper()}]")
            print(f"  Score: {data['score']}")
            raw_labels = data.get('labels', [])
            labels_list: list[str] = list(raw_labels) if isinstance(raw_labels, (list, tuple)) else []
            print(f"  Labels: {', '.join(labels_list) if labels_list else 'none'}")
            if mode == "input" and data.get("canary_triggered"):
                print("  ⚠️  Canary token detected!")
            raw_secrets = data.get("secrets_found", [])
            secrets_list: list[str] = list(raw_secrets) if isinstance(raw_secrets, (list, tuple)) else []
            if mode == "output" and secrets_list:
                print(f"  ⚠️  Secrets: {', '.join(secrets_list)}")
            print()
    
    return 1 if blocked else 0


def cmd_check(args: argparse.Namespace) -> int:
    """Check conversation file for issues."""
    path = Path(args.file)
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        return 2
    
    content = path.read_text(encoding="utf-8")
    
    # Detect format
    fmt = args.format
    if fmt == "auto":
        fmt = "jsonl" if path.suffix == ".jsonl" else "json"
    
    # Parse messages
    messages = []
    if fmt == "jsonl":
        for line in content.strip().split("\n"):
            if line.strip():
                messages.append(json.loads(line))
    else:
        data = json.loads(content)
        if isinstance(data, list):
            messages = data
        elif "messages" in data:
            messages = data["messages"]
        else:
            messages = [data]
    
    # Check each message
    layer = DefenseLayer(DefenseConfig(
        input_block_threshold=args.threshold,
        output_block_threshold=args.threshold,
    ))
    
    issues = []
    for i, msg in enumerate(messages):
        # Extract text - handle various formats
        text = msg.get("content") or msg.get("text") or msg.get("prompt") or str(msg)
        role = msg.get("role", "unknown")
        
        if role in ("user", "human"):
            result = layer.validate_input(text)
            if result and result.blocked:
                issues.append({
                    "index": i,
                    "role": role,
                    "type": "input",
                    "labels": result.labels,
                    "score": result.score,
                })
        elif role in ("assistant", "ai", "model"):
            output_result = layer.validate_output(text)
            if output_result and output_result.blocked:
                issues.append({
                    "index": i,
                    "role": role,
                    "type": "output",
                    "labels": output_result.labels,
                    "score": output_result.score,
                })
    
    if args.json:
        print(json.dumps({
            "file": str(path),
            "messages_checked": len(messages),
            "issues_found": len(issues),
            "issues": issues,
        }, indent=2))
    else:
        print(f"Checked {len(messages)} messages in {path}")
        if issues:
            print(f"⚠️  Found {len(issues)} issues:")
            for issue in issues:
                print(f"  [{issue['index']}] {issue['role']}: {', '.join(issue['labels'])}")
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
    
    layer = DefenseLayer(DefenseConfig(
        input_block_threshold=args.threshold,
        use_ml_model=not args.no_ml,
    ))
    
    detected = 0
    missed = 0
    results = []
    
    for attack in attacks:
        # Attack is always an Attack object from load_catalog
        prompt = attack.prompt
        attack_id = attack.id or ""
        category = attack.metadata.get("category", "") if attack.metadata else ""
        
        result = layer.validate_input(prompt)
        
        if result and result.blocked:
            detected += 1
            status = "detected"
        else:
            missed += 1
            status = "missed"
        
        results.append({
            "id": attack_id,
            "category": category,
            "status": status,
            "score": round(result.score, 3) if result else 0,
            "labels": result.labels if result else [],
        })
    
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
        print(f"Detected:      {detected} ({detection_rate*100:.1f}%)")
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
    print(f"  {'✓' if ml_available else '✗'} ML model (deepset/deberta-v3-base-injection)")
    print()
    
    if args.scenario:
        print(f"Recommendations for: {args.scenario}")
        print("-" * 40)
        
        scenarios = {
            "chatbot": {"high_risk_actions": False, "external_content": False, "needs_tool_use": False},
            "agent": {"high_risk_actions": True, "external_content": True, "needs_tool_use": True},
            "rag": {"high_risk_actions": False, "external_content": True, "needs_tool_use": False},
            "tool-use": {"high_risk_actions": True, "external_content": False, "needs_tool_use": True},
        }
        
        recs = recommend_defense_strategy(**scenarios[args.scenario])
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
            if t.name.lower() == args.show.lower() or t.filename.lower() == args.show.lower():
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
