from __future__ import annotations

from psg.__main__ import build_parser, main


def test_main_dispatches_scan_subcommand(monkeypatch) -> None:
    captured = {"argv": None}

    def _fake_cli(argv):
        captured["argv"] = argv
        return 0

    monkeypatch.setattr("psg.__main__.cli_main", _fake_cli)
    rc = main(["scan", "--model", "m", "--catalog", "c"])

    assert rc == 0
    assert captured["argv"] == ["--model", "m", "--catalog", "c"]


def test_main_dispatches_catalog_validate_subcommand(monkeypatch) -> None:
    captured = {"argv": None}

    def _fake_catalog(argv):
        captured["argv"] = argv
        return 0

    monkeypatch.setattr("psg.__main__.catalog_validate_main", _fake_catalog)
    rc = main(["catalog", "validate", "--path", "datasets"])

    assert rc == 0
    assert captured["argv"] == ["--path", "datasets"]


def test_main_allows_legacy_root_scan_flags(monkeypatch) -> None:
    captured = {"argv": None}

    def _fake_cli(argv):
        captured["argv"] = argv
        return 0

    monkeypatch.setattr("psg.__main__.cli_main", _fake_cli)
    rc = main(["--model", "m", "--catalog", "c"])

    assert rc == 0
    assert captured["argv"] == ["--model", "m", "--catalog", "c"]


def test_main_help_lists_scan_and_catalog_commands() -> None:
    help_text = build_parser().format_help()
    assert "scan" in help_text
    assert "catalog" in help_text
