"""Cross-cutting network-safety helpers.

These were previously in ``psg.automation.validation`` even though they are
not automation-specific: ``psg.config`` uses ``validate_url`` for the core
``--base-url`` SSRF check. Moved here so the dependency direction is clean
(core depends on ``psg.validation``, not ``psg.automation``).

``psg.automation.validation`` re-exports everything for backwards
compatibility.
"""
from __future__ import annotations

import ipaddress
import re
import socket
from typing import Union
from urllib.parse import urlparse

IPAddress = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]

# "0.0.0.0" is the literal unspecified-address string; we put it in the
# SSRF *denylist*, never as a bind target. nosec is narrowly scoped.
BLOCKED_HOSTS: set[str] = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",  # nosec B104
    "169.254.169.254",
    "::1",
}

BLOCKED_NETWORKS: tuple[ipaddress._BaseNetwork, ...] = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
)

MAX_URL_LENGTH = 2048
MAX_QUERY_LENGTH = 200

# Allow alphanumeric, spaces, and common search/URL characters.
_QUERY_PATTERN = re.compile(r"^[\w\s\-\.\:\?\&\=\%\+\'\"]+$", re.UNICODE)


def validate_query(query: str) -> str:
    """Validate and sanitize a search query.

    Raises ``ValueError`` on empty, too-long, or disallowed-character input.
    """
    if not query:
        raise ValueError("Query cannot be empty")
    if len(query) > MAX_QUERY_LENGTH:
        raise ValueError(f"Query too long: {len(query)} > {MAX_QUERY_LENGTH}")
    cleaned = query.strip()
    # Strip null bytes / control characters
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", cleaned)
    if not _QUERY_PATTERN.match(cleaned):
        raise ValueError("Query contains invalid characters")
    return cleaned


def validate_url(url: str) -> bool:
    """Return True if ``url`` is safe to fetch from an SSRF perspective.

    Rejects:
      * non-http(s) schemes (``file:``, ``javascript:``, ``data:``, ``ftp:``)
      * hostnames in ``BLOCKED_HOSTS``
      * IP literals or resolved IPs in ``BLOCKED_NETWORKS``
      * DNS names that fail resolution (unknown target → fail closed)

    This is a best-effort check. It cannot prevent a TOCTOU attack where
    DNS is re-resolved at fetch time; callers that need stronger guarantees
    should resolve once and connect by IP literal.
    """
    if not url or len(url) > MAX_URL_LENGTH:
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
        normalized_hostname = hostname.rstrip(".").lower()
        if normalized_hostname in BLOCKED_HOSTS:
            return False

        try:
            ip = ipaddress.ip_address(normalized_hostname)
            if _is_blocked_ip(ip):
                return False
        except ValueError:
            resolved_ips = _resolve_host_ips(normalized_hostname, parsed.port)
            if not resolved_ips:
                return False
            for resolved_ip in resolved_ips:
                if _is_blocked_ip(resolved_ip):
                    return False

        # Defense-in-depth: reject dangerous URL schemes even if urlparse
        # somehow accepted them above.
        dangerous_patterns = ("javascript:", "data:", "file:", "ftp:")
        url_lower = url.lower()
        for pattern in dangerous_patterns:
            if pattern in url_lower:
                return False

        return True

    except Exception:
        return False


def _is_blocked_ip(ip: IPAddress) -> bool:
    """True if the IP falls into any private/local/reserved range."""
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_unspecified
        or ip.is_multicast
    ):
        return True
    for network in BLOCKED_NETWORKS:
        if ip in network:
            return True
    return False


def _resolve_host_ips(hostname: str, port: int | None) -> set[IPAddress]:
    """Resolve a hostname to all IPv4/IPv6 addresses."""
    resolved: set[IPAddress] = set()
    try:
        infos = socket.getaddrinfo(hostname, port or 443, proto=socket.IPPROTO_TCP)
    except OSError:
        return resolved
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        ip_text = sockaddr[0]
        try:
            resolved.add(ipaddress.ip_address(ip_text))
        except ValueError:
            continue
    return resolved


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename.

    Replaces unsafe characters, strips leading/trailing dots and
    underscores, and caps length at 100 characters. Returns ``"unnamed"``
    for empty input.
    """
    safe = re.sub(r"[^\w\-\.]", "_", name)
    safe = safe.strip("._")
    return safe[:100] if safe else "unnamed"
