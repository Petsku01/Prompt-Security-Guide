from __future__ import annotations

import logging
import socket
from pathlib import Path
from urllib.parse import urlparse

from .models import AppConfig, ClassificationInputMode, RedactionMode
from .validation.ssrf import resolve_host_ips

logger = logging.getLogger(__name__)


class ConfigError(ValueError):
    pass


def validate_config(cfg: AppConfig) -> AppConfig:
    if not cfg.model.strip():
        raise ConfigError("model is required")

    catalog = Path(cfg.catalog_path)
    if not catalog.exists() or not catalog.is_file():
        logger.error("Catalog does not exist: %s", cfg.catalog_path)
        raise ConfigError(f"catalog does not exist: {cfg.catalog_path}")

    _validate_endpoint_url(
        field_name="base-url",
        url=cfg.base_url,
        allow_insecure_http=cfg.allow_insecure_http,
    )
    # Use explicit None check: empty string "" should NOT fall back to base_url
    judge_url = cfg.judge_url if cfg.judge_url is not None else cfg.base_url
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
    if not (0.0 <= cfg.defense_threshold <= 1.0):
        raise ConfigError("defense-threshold must be within 0.0-1.0")

    # Production guardrail (defense-in-depth, on top of the SSRF guard):
    # when SSRF protection is bypassed (--allow-insecure-http) AND the
    # base_url is a private/internal target, sending the attack catalog
    # requires explicit --allow-production-attacks. Public endpoints are
    # not gated here (the SSRF guard already handles them when enabled).
    if (
        cfg.allow_insecure_http
        and not _is_local_endpoint(cfg.base_url)
        and _is_private_ip((urlparse(cfg.base_url).hostname or "").lower())
        and not cfg.allow_production_attacks
    ):
        raise ConfigError(
            "base-url points to a private/internal endpoint while SSRF "
            "protection is disabled (--allow-insecure-http); sending the "
            "attack catalog there requires --allow-production-attacks (and "
            "--with-defense is strongly recommended)"
        )
    if cfg.with_defense and cfg.workers > 1:
        logger.warning(
            "with-defense pre-validation runs only in the parent process; "
            "with workers>1 blocked attacks are still excluded pre-send"
        )
    if cfg.detector not in {"keyword", "llm-judge", "ensemble", "multi-judge"}:
        raise ConfigError(
            "detector must be one of: keyword, llm-judge, ensemble, multi-judge"
        )
    if cfg.detector == "multi-judge":
        models = [m.strip() for m in (cfg.judge_models or "").split(",") if m.strip()]
        if len(models) < 2:
            raise ConfigError(
                "multi-judge requires --judge-models with at least 2 "
                "comma-separated models (e.g. 'llama3:8b,qwen2.5:7b')"
            )
    if not cfg.judge_model.strip():
        raise ConfigError("judge-model is required")

    for p in (
        cfg.checkpoint_path,
        cfg.report_json_path,
        cfg.report_text_path,
        cfg.defense_report_path,
    ):
        Path(p).parent.mkdir(parents=True, exist_ok=True)

    if not isinstance(cfg.redaction_mode, RedactionMode):
        cfg.redaction_mode = RedactionMode(str(cfg.redaction_mode))
    if not isinstance(cfg.classification_input_mode, ClassificationInputMode):
        cfg.classification_input_mode = ClassificationInputMode(
            str(cfg.classification_input_mode)
        )

    if cfg.system_prompt is not None:
        cfg.system_prompt = cfg.system_prompt.strip() or None

    return cfg


def _is_local_endpoint(url: str) -> bool:
    """True when the endpoint host is clearly local (localhost/127.0.0.1/::1)."""
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    if not host:
        return False
    if host in {"localhost", "::1"} or host.endswith(".localhost"):
        return True
    if host == "127.0.0.1" or host.startswith("127."):
        return True
    return False


def _is_private_ip(host: str) -> bool:
    """True for RFC1918/loopback/link-local/unique-local IPv4/IPv6 literals."""
    if host in {"localhost", "::1"} or host.endswith(".localhost"):
        return True
    parts = host.split(".")
    if len(parts) == 4 and all(p.isdigit() for p in parts):
        a, b = int(parts[0]), int(parts[1])
        if (
            a == 10
            or a == 127
            or (a == 172 and 16 <= b <= 31)
            or (a == 192 and b == 168)
        ):
            return True
        if a == 169 and b == 254:
            return True
    return host.startswith("fd") or host.startswith("fe80:")


def _validate_url_ssrf(url: str) -> bool:
    """Shared-SSRF-core offline predicate (audit S2/S3).

    Same policy as psg.validation.ssrf.is_blocked_ip; hostnames resolve
    via the shared resolver (resolution failure = fail-closed for the
    config gate). Mirrors the old automation.validation.validate_url
    semantics without the automation-layer import.
    """
    import ipaddress as _ipaddress

    from .validation.ssrf import BLOCKED_HOSTS, is_blocked_ip

    if not url or len(url) > 2048:
        return False
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        if not parsed.netloc:
            return False
        hostname = parsed.hostname
        if hostname is None:
            return False
        normalized = hostname.rstrip(".").lower()
        if normalized in BLOCKED_HOSTS:
            return False
        try:
            ip = _ipaddress.ip_address(normalized)
            if is_blocked_ip(ip):
                return False
        except ValueError:
            try:
                resolved = resolve_host_ips(normalized, parsed.port)
            except socket.gaierror:
                return False
            if not resolved:
                return False
            if any(is_blocked_ip(ip) for ip in resolved):
                return False
        return True
    except Exception as exc:
        logger.debug("URL validation failed for %s: %s", url, exc)
        return False


def _validate_endpoint_url(
    field_name: str, url: str, allow_insecure_http: bool
) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ConfigError(f"{field_name} must start with http:// or https://")

    if parsed.scheme == "http" and not allow_insecure_http:
        raise ConfigError(
            f"Refusing insecure http:// {field_name}. Use --allow-insecure-http to override."
        )

    # SSRF guardrails: disallow localhost/private and resolved internal
    # targets by default. Uses the shared ssrf core directly (audit S2:
    # core config must not depend on the automation layer).
    if not allow_insecure_http and not _validate_url_ssrf(url):
        raise ConfigError(
            f"{field_name} target is blocked by SSRF protection. Use --allow-insecure-http to override."
        )
