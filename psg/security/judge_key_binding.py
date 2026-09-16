"""Audit P0-3 (HIGH, 2026-09-15): judge API-key origin binding.

Previously both build_detector and build_multi_judges sent the PRIMARY
cfg.api_key as the Authorization header to cfg.judge_url — a possibly
third-party origin — with no check that judge origin == model origin.
An OpenAI key could thus silently leak to an attacker-controlled judge
server that the config pointed at.

Fix (this module): a judge credential resolver with origin comparison.

Policy:
- judge_api_key set   -> used as-is (explicit operator decision)
- judge_url unset/None-> judge endpoint == base_url; api_key reuse is safe
- judge_url set, same scheme+host+port as base_url -> api_key reuse is safe
- judge_url set, DIFFERENT origin, judge_api_key unset -> ConfigError.
  The key is never silently forwarded across origins.

Origin comparison normalizes host (case, trailing dot, IPv6 brackets)
and always compares scheme and effective port (default ports implied).
"""

from __future__ import annotations

from urllib.parse import urlparse

_DEFAULT_PORTS = {"http": 80, "https": 443}


class JudgeKeyBindingError(ValueError):
    """Raised when a judge endpoint would receive a key bound to another origin."""


def _origin(url: str) -> tuple[str, str, int]:
    """Return (scheme, normalized_host, effective_port) for a URL.

    Raises JudgeKeyBindingError on unparseable input.
    """
    try:
        p = urlparse(url)
        scheme = (p.scheme or "").lower()
        host = (p.hostname or "").lower()
        port = p.port  # may raise ValueError for invalid ports
    except ValueError as exc:
        raise JudgeKeyBindingError(f"unparseable URL {url!r}: {exc}") from exc
    if not scheme or not host:
        raise JudgeKeyBindingError(f"URL missing scheme or host: {url!r}")
    if port is None:
        port = _DEFAULT_PORTS.get(scheme, 0)
    return scheme, host, port


def resolve_judge_api_key(
    *,
    api_key: str | None,
    judge_api_key: str | None,
    base_url: str,
    judge_url: str | None,
) -> str | None:
    """Return the credential to send to the judge endpoint, or None.

    See module docstring for the policy. This function NEVER logs key
    material; error messages reference origins only.
    """
    if judge_api_key:
        return judge_api_key
    if not api_key:
        return None  # nothing to leak anywhere
    if not judge_url:
        return api_key  # judge endpoint IS the model endpoint
    if _origin(base_url) == _origin(judge_url):
        return api_key  # same origin — same credential is correct
    raise JudgeKeyBindingError(
        "refusing to send the model api_key to a different judge origin: "
        f"base_url origin {_origin(base_url)} != judge_url origin "
        f"{_origin(judge_url)}; set --judge-api-key explicitly"
    )
