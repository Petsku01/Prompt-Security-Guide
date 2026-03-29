from __future__ import annotations

import argparse
import sys

from .benchmark import main as benchmark_main
from .catalog_validator import main as catalog_validate_main
from .cli import add_scan_arguments, main as cli_main
from .defend import add_defend_arguments, main as defend_main
from .eval import main as eval_main
from .serve import main as serve_main


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prompt Security Guide v4.1")
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
    catalog_list_parser = catalog_subparsers.add_parser("list", help="List available attack catalogs")
    catalog_list_parser.add_argument("--path", default="datasets/", help="Path to catalogs directory")
    validate_parser = catalog_subparsers.add_parser("validate", help="Validate catalog JSON files")
    validate_parser.add_argument("--path", default="datasets/", help="Path to catalog JSON file/directory")

    serve_parser = subparsers.add_parser("serve", help="Start screening API server")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    serve_parser.add_argument("--threshold", type=float, default=0.5, help="Default threshold")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    defend_parser = subparsers.add_parser("defend", help="Test prompt injection defenses")
    add_defend_arguments(defend_parser)

    plugins_parser = subparsers.add_parser("plugins", help="List installed plugins")
    plugins_parser.add_argument("--type", choices=["detectors", "classifiers", "reporters", "all"], default="all")

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
    if ns.command == "catalog":
        if ns.catalog_command == "list":
            return _list_catalogs(ns.path)
        if ns.catalog_command == "validate":
            return catalog_validate_main(["--path", ns.path])
        print("Usage: psg catalog {list,validate}", file=sys.stderr)
        return 2
    if ns.command == "serve":
        serve_args = [*args[1:]]
        return serve_main(serve_args)
    if ns.command == "defend":
        defend_args = [*args[1:]]
        return defend_main(defend_args)
    if ns.command == "plugins":
        return _list_plugins(ns.type)

    parser.print_help()
    return 2


def _list_catalogs(path: str) -> int:
    """List available attack catalogs with counts."""
    import json
    from pathlib import Path
    
    catalog_dir = Path(path)
    if not catalog_dir.exists():
        print(f"Error: Directory not found: {path}", file=sys.stderr)
        return 1
    
    catalogs = []
    for f in sorted(catalog_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            attacks = data.get("attacks", [])
            count = len(attacks)
            desc = data.get("description", "")[:50]
            catalogs.append((f.name, count, desc))
        except Exception:
            catalogs.append((f.name, -1, "(invalid JSON)"))
    
    # Also check profiles subdirectory
    profiles_dir = catalog_dir / "profiles"
    if profiles_dir.exists():
        for f in sorted(profiles_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                attacks = data.get("attacks", [])
                count = len(attacks)
                desc = data.get("description", "")[:50]
                catalogs.append((f"profiles/{f.name}", count, desc))
            except Exception:
                catalogs.append((f"profiles/{f.name}", -1, "(invalid JSON)"))
    
    if not catalogs:
        print(f"No catalogs found in {path}")
        return 0
    
    print(f"Available catalogs in {path}:\n")
    print(f"{'Catalog':<45} {'Attacks':>8}  Description")
    print("-" * 80)
    
    total = 0
    for name, count, desc in sorted(catalogs, key=lambda x: -x[1] if x[1] > 0 else 0):
        if count >= 0:
            total += count
            print(f"{name:<45} {count:>8}  {desc}")
        else:
            print(f"{name:<45} {'?':>8}  {desc}")
    
    print("-" * 80)
    print(f"Total: {len(catalogs)} catalogs, {total}+ attacks")
    print(f"\nUsage: psg scan --catalog {path}<name>.json --model <model>")
    return 0


def _list_plugins(plugin_type: str) -> int:
    """List installed plugins."""
    from .plugins import load_plugins
    from .plugins.builtin import register_builtin_plugins
    
    registry = load_plugins()
    register_builtin_plugins(registry)
    
    if plugin_type in ("detectors", "all"):
        print("Detectors:")
        for name in registry.list_detectors():
            print(f"  - {name}")
        if not registry.list_detectors():
            print("  (none)")
    
    if plugin_type in ("classifiers", "all"):
        print("Classifiers:")
        for name in registry.list_classifiers():
            print(f"  - {name}")
        if not registry.list_classifiers():
            print("  (none)")
    
    if plugin_type in ("reporters", "all"):
        print("Reporters:")
        for name in registry.list_reporters():
            print(f"  - {name}")
        if not registry.list_reporters():
            print("  (none)")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
