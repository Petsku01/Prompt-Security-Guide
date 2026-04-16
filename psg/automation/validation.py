"""Automation-pipeline validation helpers.

These originally lived in ``psg.automation.validation`` but are used by
cross-cutting code (``psg.config``). They have been moved to
``psg.validation.network``; this module re-exports them so existing
imports keep working.
"""
from __future__ import annotations

from ..validation.network import (  # noqa: F401  (re-export)
    BLOCKED_HOSTS,
    BLOCKED_NETWORKS,
    IPAddress,
    MAX_QUERY_LENGTH,
    MAX_URL_LENGTH,
    _is_blocked_ip,
    _resolve_host_ips,
    sanitize_filename,
    validate_query,
    validate_url,
)

__all__ = [
    "BLOCKED_HOSTS",
    "BLOCKED_NETWORKS",
    "IPAddress",
    "MAX_QUERY_LENGTH",
    "MAX_URL_LENGTH",
    "sanitize_filename",
    "validate_query",
    "validate_url",
]
