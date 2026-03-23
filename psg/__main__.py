from __future__ import annotations

import sys

from .catalog_validator import main as catalog_validate_main
from .cli import main as cli_main


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if len(args) >= 2 and args[0] == "catalog" and args[1] == "validate":
        return catalog_validate_main(args[2:])

    return cli_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
