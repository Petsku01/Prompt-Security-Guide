from __future__ import annotations

from psg.config import ConfigError, validate_config
from psg.models import AppConfig


def _base_cfg() -> AppConfig:
    return AppConfig(
        model="llama3:8b",
        catalog_path="datasets/tiny_test.json",
        base_url="https://example.com/v1",
        judge_url="https://example.com/v1",
    )


def test_validate_config_blocks_private_judge_url_without_override() -> None:
    cfg = _base_cfg()
    cfg.judge_url = "https://127.0.0.1/v1"

    try:
        validate_config(cfg)
    except ConfigError as exc:
        assert "judge-url target is blocked by SSRF protection" in str(exc)
    else:
        raise AssertionError("Expected ConfigError for private judge-url")


def test_validate_config_blocks_private_base_url_without_override() -> None:
    cfg = _base_cfg()
    cfg.base_url = "https://localhost/v1"

    try:
        validate_config(cfg)
    except ConfigError as exc:
        assert "base-url target is blocked by SSRF protection" in str(exc)
    else:
        raise AssertionError("Expected ConfigError for private base-url")


def test_validate_config_allows_private_judge_url_with_override() -> None:
    cfg = _base_cfg()
    cfg.allow_insecure_http = True
    cfg.judge_url = "https://127.0.0.1/v1"
    validated = validate_config(cfg)

    assert validated.judge_url == "https://127.0.0.1/v1"
