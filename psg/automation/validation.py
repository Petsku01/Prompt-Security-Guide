"""Input validation for psg.automation."""

import logging
import socket
import re
from urllib.parse import urlparse
import ipaddress
from typing import Union

IPAddress = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]

BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254", "::1"}
BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


MAX_QUERY_LENGTH = 200
MAX_URL_LENGTH = 2048

# Allow alphanumeric, spaces, and common search/URL characters
QUERY_PATTERN = re.compile(r"^[\w\s\-\.\:\?\&\=\%\+\'\"]+$", re.UNICODE)


def validate_query(query: str) -> str:
    """Validate and sanitize search query.

    Args:
        query: Raw search query string

    Returns:
        Sanitized query string

    Raises:
        ValueError: If query is invalid
    """
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
    """Check if URL is safe to process.

    validate_url resolves DNS at call time, which creates a TOCTOU window
    — an attacker could rebind DNS between validation and the actual HTTP
    request.  For production use, pin resolved IPs to the HTTP client.
    Accepted risk for local/offline tool.

    TODO: Pass resolved IPs to the HTTP client and enforce pinning so
    that the request goes to the same IP that was validated here.

    Args:
        url: URL string to validate

    Returns:
        True if URL is valid and safe, False otherwise
    """
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
            if _is_blocked_ip(ip):
                return False
        except ValueError:
            resolved_ips = _resolve_host_ips(normalized_hostname, parsed.port)
            if not resolved_ips:
                return False
            for resolved_ip in resolved_ips:
                if _is_blocked_ip(resolved_ip):
                    return False

        return True

    except Exception as exc:
        logging.debug("URL validation failed for %s: %s", url, exc)
        return False


def _is_blocked_ip(ip: IPAddress) -> bool:
    """Check whether an IP falls into any blocked private/local ranges."""
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
    """Resolve hostname to all IPv4/IPv6 addresses."""
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



