from __future__ import annotations

import argparse
import sys

from .benchmark import main as benchmark_main
from .catalog_validator import main as catalog_validate_main
from .cli import add_scan_arguments, main as cli_main
from .eval import main as eval_main


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prompt Security Guide v4.0")
    subparsers = parser.add_subparsers(dest="command")

    scan_parser = subparsers.add_parser("scan", help="Run prompt security scan")
    add_scan_arguments(scan_parser)

    eval_parser = subparsers.add_parser("eval", help="Evaluate classifier against golden dataset")
    eval_parser.add_argument("--golden", required=True, help="Path to golden dataset JSON")
    eval_parser.add_argument("--threshold", type=float, default=0.5, help="Classification threshold")
    eval_parser.add_argument("--fail-on-macro-f1-below", type=float, metavar="SCORE", help="Fail if F1 < threshold")
    eval_parser.add_argument("--json", action="store_true", help="Output as JSON")

    benchmark_parser = subparsers.add_parser("benchmark", help="Run benchmark presets")
    benchmark_parser.add_argument("--preset", choices=["jbb", "owasp", "obliteratus", "full"], help="Preset name")
    benchmark_parser.add_argument("--model", help="Model name")
    benchmark_parser.add_argument("--base-url", default="http://localhost:11434/v1", help="API base URL")
    benchmark_parser.add_argument("--api-key", default=None, help="API key")
    benchmark_parser.add_argument("--workers", type=int, default=1, help="Parallel workers")
    benchmark_parser.add_argument("--rate-limit", type=float, default=None, help="Max req/s")
    benchmark_parser.add_argument("--system-prompt", default=None, help="System prompt to test")
    benchmark_parser.add_argument("--detector", choices=["keyword", "llm-judge", "ensemble"], default="keyword")
    benchmark_parser.add_argument("--output-dir", default="results", help="Output directory")
    benchmark_parser.add_argument("--json", action="store_true", help="Output as JSON")
    benchmark_parser.add_argument("--list", action="store_true", help="List presets")

    catalog_parser = subparsers.add_parser("catalog", help="Catalog utilities")
    catalog_subparsers = catalog_parser.add_subparsers(dest="catalog_command")
    validate_parser = catalog_subparsers.add_parser("validate", help="Validate catalog JSON files")
    validate_parser.add_argument("--path", default="datasets/", help="Path to catalog JSON file/directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()

    # Backwards compatibility: allow legacy root flags as implicit "scan".
    if args and args[0].startswith("-"):
        return cli_main(args)
    if not args:
        parser.print_help()
        return 2

    ns = parser.parse_args(args)
    if ns.command == "scan":
        scan_args = [*args[1:]]
        return cli_main(scan_args)
    if ns.command == "eval":
        eval_args = [*args[1:]]
        return eval_main(eval_args)
    if ns.command == "benchmark":
        # Handle --list before requiring other args
        if "--list" in args:
            return benchmark_main(["--list"])
        if not ns.preset or not ns.model:
            print("Error: --preset and --model are required (unless --list)", file=sys.stderr)
            return 2
        benchmark_args = [*args[1:]]
        return benchmark_main(benchmark_args)
    if ns.command == "catalog" and ns.catalog_command == "validate":
        return catalog_validate_main(["--path", ns.path])

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
