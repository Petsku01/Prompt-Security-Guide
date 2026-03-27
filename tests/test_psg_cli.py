from __future__ import annotations

from psg.cli import build_parser, main
from psg.errors import CatalogError, LLMError
from psg.config import ConfigError
from psg.models import RunSummary


def test_build_parser_parses_core_args() -> None:
    parser = build_parser()
    args = parser.parse_args(["--model", "llama3", "--catalog", "datasets/tiny_test.json"])

    assert args.model == "llama3"
    assert args.catalog == "datasets/tiny_test.json"
    assert args.timeout == 240.0
    assert args.classification_input == "auto"


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


def test_main_returns_3_on_catalog_error(monkeypatch) -> None:
    monkeypatch.setattr("psg.cli.validate_config", lambda cfg: cfg)
    monkeypatch.setattr("psg.cli.run", lambda _cfg: (_ for _ in ()).throw(CatalogError("bad catalog")))

    rc = main(["--model", "m", "--catalog", "c", "--allow-insecure-http"])

    assert rc == 3


def test_main_returns_1_when_report_write_failed(monkeypatch) -> None:
    monkeypatch.setattr("psg.cli.validate_config", lambda cfg: cfg)
    monkeypatch.setattr(
        "psg.cli.run",
        lambda _cfg: (RunSummary(1, 1, 0, 0, 0.1, report_write_failed=True), []),
    )

    rc = main(["--model", "m", "--catalog", "c", "--allow-insecure-http"])

    assert rc == 1


def test_main_returns_4_on_llm_error(monkeypatch) -> None:
    monkeypatch.setattr("psg.cli.validate_config", lambda cfg: cfg)
    monkeypatch.setattr("psg.cli.run", lambda _cfg: (_ for _ in ()).throw(LLMError("transport down")))

    rc = main(["--model", "m", "--catalog", "c", "--allow-insecure-http"])

    assert rc == 4


def test_build_parser_reads_api_key_from_env(monkeypatch) -> None:
    monkeypatch.setenv("PSG_API_KEY", "secret")
    parser = build_parser()
    args = parser.parse_args(["--model", "m", "--catalog", "c"])
    assert args.api_key == "secret"


def test_build_parser_allows_api_key_flag_over_env(monkeypatch) -> None:
    monkeypatch.setenv("PSG_API_KEY", "env-secret")
    parser = build_parser()
    args = parser.parse_args(["--model", "m", "--catalog", "c", "--api-key", "cli-secret"])
    assert args.api_key == "cli-secret"


def test_build_parser_parses_classification_input() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["--model", "m", "--catalog", "c", "--classification-input", "redacted"]
    )
    assert args.classification_input == "redacted"


def test_build_parser_parses_validation_flags() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "--model",
            "m",
            "--catalog",
            "c",
            "--validate-urls",
            "--validate-dois",
            "--validation-timeout",
            "7.5",
        ]
    )
    assert args.validate_urls is True
    assert args.validate_dois is True
    assert args.validation_timeout == 7.5
