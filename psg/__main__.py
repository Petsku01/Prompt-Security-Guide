from __future__ import annotations

import argparse
import sys

from .catalog_validator import main as catalog_validate_main
from .cli import add_scan_arguments, main as cli_main


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prompt Security Guide v4.0")
    subparsers = parser.add_subparsers(dest="command")

    scan_parser = subparsers.add_parser("scan", help="Run prompt security scan")
    add_scan_arguments(scan_parser)

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
    if ns.command == "catalog" and ns.catalog_command == "validate":
        return catalog_validate_main(["--path", ns.path])

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
