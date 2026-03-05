from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from .models import AppConfig, RedactionMode


class ConfigError(ValueError):
    pass


def validate_config(cfg: AppConfig) -> AppConfig:
    if not cfg.model.strip():
        raise ConfigError("model is required")

    catalog = Path(cfg.catalog_path)
    if not catalog.exists() or not catalog.is_file():
        raise ConfigError(f"catalog does not exist: {cfg.catalog_path}")

    parsed = urlparse(cfg.base_url)
    if parsed.scheme not in {"http", "https"}:
        raise ConfigError("base-url must start with http:// or https://")

    if parsed.scheme == "http" and not cfg.allow_insecure_http:
        raise ConfigError(
            "Refusing insecure http:// base-url. Use --allow-insecure-http to override."
        )

    if cfg.timeout_seconds <= 0:
        raise ConfigError("timeout must be > 0")
    if cfg.max_retries < 0:
        raise ConfigError("max-retries must be >= 0")

    for p in (cfg.checkpoint_path, cfg.report_json_path, cfg.report_text_path):
        Path(p).parent.mkdir(parents=True, exist_ok=True)

    if not isinstance(cfg.redaction_mode, RedactionMode):
        cfg.redaction_mode = RedactionMode(str(cfg.redaction_mode))

    return cfg
