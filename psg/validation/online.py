from __future__ import annotations

import ipaddress
import socket
import threading
import time
from functools import lru_cache
from urllib.parse import quote, urlparse

import requests

DEFAULT_TIMEOUT_SECONDS = 5.0
DEFAULT_MAX_REQUESTS_PER_SECOND = 10.0
_USER_AGENT = "PromptSecurityGuide/4.x validation"
_BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}  # nosec B104 — SSRF denylist, not a bind target
_BLOCKED_NETWORKS = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
)


class _TokenBucketRateLimiter:
    def __init__(self, *, rate: float, capacity: float | None = None) -> None:
        self.rate = rate
        self.capacity = max(1.0, capacity if capacity is not None else rate)
        self.tokens = self.capacity
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            now = time.monotonic()
            elapsed = max(0.0, now - self.last_refill)
            self.last_refill = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            if self.tokens < 1.0:
                return False
            self.tokens -= 1.0
            return True


_rate_limiter_lock = threading.Lock()
_rate_limiters: dict[float, _TokenBucketRateLimiter] = {}


def validate_url(
    url: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    *,
    allowlist: tuple[str, ...] | None = None,
    max_requests_per_second: float | None = DEFAULT_MAX_REQUESTS_PER_SECOND,
) -> bool:
    normalized_allowlist = _normalize_allowlist(allowlist)
    return _validate_url_cached(url, float(timeout), normalized_allowlist, max_requests_per_second)


@lru_cache(maxsize=2048)
def _validate_url_cached(
    url: str,
    timeout: float,
    allowlist: tuple[str, ...],
    max_requests_per_second: float | None,
) -> bool:
    if not _is_safe_url(url, allowlist=allowlist):
        return False
    if not _allow_request(max_requests_per_second):
        return False

    try:
        response = requests.head(
            url,
            allow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": _USER_AGENT},
        )
    except requests.RequestException:
        return False
    return 200 <= response.status_code < 400


def validate_doi(
    doi: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    *,
    max_requests_per_second: float | None = DEFAULT_MAX_REQUESTS_PER_SECOND,
) -> bool:
    return _validate_doi_cached(doi.strip(), float(timeout), max_requests_per_second)


@lru_cache(maxsize=2048)
def _validate_doi_cached(doi: str, timeout: float, max_requests_per_second: float | None) -> bool:
    if not _allow_request(max_requests_per_second):
        return False

    encoded = quote(doi, safe="")
    url = f"https://api.crossref.org/works/{encoded}"
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": _USER_AGENT},
        )
    except requests.RequestException:
        return False
    return 200 <= response.status_code < 400


def clear_validation_cache() -> None:
    _validate_url_cached.cache_clear()
    _validate_doi_cached.cache_clear()
    with _rate_limiter_lock:
        _rate_limiters.clear()


def _is_safe_url(url: str, *, allowlist: tuple[str, ...] = ()) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False

    if parsed.scheme.lower() not in {"http", "https"}:
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    host = hostname.rstrip(".").lower()
    if host in _BLOCKED_HOSTS:
        return False
    if allowlist and not _host_in_allowlist(host, allowlist):
        return False

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        resolved_ips = _resolve_host_ips(host, parsed.port)
        if not resolved_ips:
            return False
        return all(not _is_blocked_ip(resolved_ip) for resolved_ip in resolved_ips)
    else:
        return not _is_blocked_ip(ip)


def _normalize_allowlist(allowlist: tuple[str, ...] | None) -> tuple[str, ...]:
    if not allowlist:
        return ()
    normalized = []
    for host in allowlist:
        value = host.strip().rstrip(".").lower()
        if value:
            normalized.append(value)
    return tuple(sorted(set(normalized)))


def _host_in_allowlist(host: str, allowlist: tuple[str, ...]) -> bool:
    for allowed in allowlist:
        if host == allowed or host.endswith(f".{allowed}"):
            return True
    return False


def _resolve_host_ips(hostname: str, port: int | None) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        infos = socket.getaddrinfo(hostname, port or 443, proto=socket.IPPROTO_TCP)
    except OSError:
        return set()

    resolved: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
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


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_unspecified
        or ip.is_multicast
    ):
        return True
    return any(ip in network for network in _BLOCKED_NETWORKS)


def _allow_request(max_requests_per_second: float | None) -> bool:
    if max_requests_per_second is None:
        return True
    rate = float(max_requests_per_second)
    if rate <= 0:
        return False
    with _rate_limiter_lock:
        limiter = _rate_limiters.get(rate)
        if limiter is None:
            limiter = _TokenBucketRateLimiter(rate=rate)
            _rate_limiters[rate] = limiter
    return limiter.allow()
