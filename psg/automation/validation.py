"""Input validation for psg.automation.

2026-09-16 (audit S2+S3): the SSRF policy core (blocked hosts/networks,
IP classification, DNS resolution) now lives in psg.validation.ssrf —
the single source of truth shared with validation.online. This module
keeps its offline-predicate semantics and delegates the policy to the
shared core, removing the second private implementation.
"""

import ipaddress
import logging
import re
import socket
from urllib.parse import urlparse

from ..validation.ssrf import (
    BLOCKED_HOSTS,
    is_blocked_ip,
    resolve_host_ips,
)

MAX_QUERY_LENGTH = 200
MAX_URL_LENGTH = 2048

# Allow alphanumeric, spaces, and common search/URL characters
QUERY_PATTERN = re.compile(r"^[\w\s\-\.\:\?\&\=\%\+\'\"]+$", re.UNICODE)


def validate_query(query: str) -> str:
    """Sanitize search query. Raises ValueError if invalid."""
    if not query:
        raise ValueError("Query cannot be empty")

    if len(query) > MAX_QUERY_LENGTH:
        raise ValueError(f"Query too long: {len(query)} > {MAX_QUERY_LENGTH}")

    cleaned = query.strip()

    # Remove any null bytes or control characters
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", cleaned)

    if not QUERY_PATTERN.match(cleaned):
        raise ValueError("Query contains invalid characters")

    return cleaned


def validate_url(url: str) -> bool:
    """Check if URL is safe.

    TOCTOU risk: DNS resolves at call time, attacker could rebind between
    validation and request. Pin resolved IPs for production use.
    Accepted risk for local/offline use.
    """
    # TODO(security): Pass resolved IPs to HTTP client and enforce pinning
    # (DNS rebinding mitigation — tracked separately)
    if not url or len(url) > MAX_URL_LENGTH:
        return False

    try:
        parsed = urlparse(url)

        # Must have http/https scheme
        if parsed.scheme not in ("http", "https"):
            return False

        # Must have a netloc (domain)
        if not parsed.netloc:
            return False

        hostname = parsed.hostname
        if hostname is None:
            return False
        normalized_hostname = hostname.rstrip(".").lower()
        if normalized_hostname in BLOCKED_HOSTS:
            return False

        try:
            ip = ipaddress.ip_address(normalized_hostname)
            if is_blocked_ip(ip):
                return False
        except ValueError:
            resolved_ips = resolve_host_ips_safe(normalized_hostname, parsed.port)
            if not resolved_ips:
                return False
            for resolved_ip in resolved_ips:
                if is_blocked_ip(resolved_ip):
                    return False

        return True

    except Exception as exc:
        logging.debug("URL validation failed for %s: %s", url, exc)
        return False


def resolve_host_ips_safe(hostname: str, port: int | None) -> set:
    """Offline-predicate wrapper: resolution failure is an empty set (fail-closed
    for the config gate), never an exception."""
    try:
        return resolve_host_ips(hostname, port)
    except socket.gaierror:
        return set()


# Compatibility alias: tests and any external callers monkeypatched the
# historical private name; keep it pointed at the shared-core wrapper.
_resolve_host_ips = resolve_host_ips_safe



