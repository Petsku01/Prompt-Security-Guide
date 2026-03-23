from __future__ import annotations

from psg.cli import build_parser, main
from psg.config import ConfigError
from psg.models import RunSummary


def test_build_parser_parses_core_args() -> None:
    parser = build_parser()
    args = parser.parse_args(["--model", "llama3", "--catalog", "datasets/tiny_test.json"])

    assert args.model == "llama3"
    assert args.catalog == "datasets/tiny_test.json"
    assert args.timeout == 240.0


def test_main_returns_2_on_config_error(monkeypatch) -> None:
    def _raise(_cfg):
        raise ConfigError("bad")

    monkeypatch.setattr("psg.cli.validate_config", _raise)
    rc = main(["--model", "m", "--catalog", "c"])
    assert rc == 2


def test_main_returns_0_on_success(monkeypatch) -> None:
    monkeypatch.setattr("psg.cli.validate_config", lambda cfg: cfg)
    monkeypatch.setattr("psg.cli.run", lambda cfg: (RunSummary(1, 1, 0, 0, 0.1), []))

    rc = main([
        "--model",
        "llama3",
        "--catalog",
        "datasets/tiny_test.json",
        "--allow-insecure-http",
    ])

    assert rc == 0
