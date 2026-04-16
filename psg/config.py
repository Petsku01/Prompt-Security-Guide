from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from .models import AppConfig, ClassificationInputMode, RedactionMode
from .validation.network import validate_url


class ConfigError(ValueError):
    pass


def validate_config(cfg: AppConfig) -> AppConfig:
    if not cfg.model.strip():
        raise ConfigError("model is required")

    catalog = Path(cfg.catalog_path)
    if not catalog.exists() or not catalog.is_file():
        raise ConfigError(f"catalog does not exist: {cfg.catalog_path}")

    _validate_endpoint_url(
        field_name="base-url",
        url=cfg.base_url,
        allow_insecure_http=cfg.allow_insecure_http,
    )
    judge_url = cfg.judge_url or cfg.base_url
    _validate_endpoint_url(
        field_name="judge-url",
        url=judge_url,
        allow_insecure_http=cfg.allow_insecure_http,
    )

    if cfg.timeout_seconds <= 0:
        raise ConfigError("timeout must be > 0")
    if cfg.validation_timeout_seconds <= 0:
        raise ConfigError("validation-timeout must be > 0")
    if cfg.max_retries < 0:
        raise ConfigError("max-retries must be >= 0")
    if cfg.detector not in {"keyword", "llm-judge", "ensemble"}:
        raise ConfigError("detector must be one of: keyword, llm-judge, ensemble")
    if cfg.ensemble_mode not in {"any", "and", "short_circuit"}:
        raise ConfigError("ensemble-mode must be one of: any, and, short_circuit")
    if not cfg.judge_model.strip():
        raise ConfigError("judge-model is required")

    for p in (cfg.checkpoint_path, cfg.report_json_path, cfg.report_text_path, cfg.defense_report_path):
        Path(p).parent.mkdir(parents=True, exist_ok=True)

    if not isinstance(cfg.redaction_mode, RedactionMode):
        cfg.redaction_mode = RedactionMode(str(cfg.redaction_mode))
    if not isinstance(cfg.classification_input_mode, ClassificationInputMode):
        cfg.classification_input_mode = ClassificationInputMode(str(cfg.classification_input_mode))

    if cfg.system_prompt is not None:
        cfg.system_prompt = cfg.system_prompt.strip() or None

    return cfg


def _validate_endpoint_url(field_name: str, url: str, allow_insecure_http: bool) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ConfigError(f"{field_name} must start with http:// or https://")

    if parsed.scheme == "http" and not allow_insecure_http:
        raise ConfigError(
            f"Refusing insecure http:// {field_name}. Use --allow-insecure-http to override."
        )

    # SSRF guardrails: disallow localhost/private and resolved internal targets by default.
    if not allow_insecure_http and not validate_url(url):
        raise ConfigError(
            f"{field_name} target is blocked by SSRF protection. Use --allow-insecure-http to override."
        )
