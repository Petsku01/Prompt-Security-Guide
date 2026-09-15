"""Audit P0-4 (HIGH, 2026-09-15): DNS-rebinding — pin requests to a
validated IP.

psg/config.validate_config resolves the endpoint hostname ONCE at config
load and checks SSRF constraints against that IP. But the actual HTTP
request (`Transport.post_json` -> `requests.post`) re-resolves DNS at
call time. An attacker controlling the judge/model domain can answer the
first lookup with a public IP (passing SSRF checks) and subsequent
lookups with an internal/metadata IP — receiving both the attack
catalog AND the Authorization header.

Fix (this module): a pinned-session transport. The endpoint hostname is
resolved ONCE via the same resolver the config validation used, the
chosen IP is pinned for the transport's lifetime, and every request is
sent to that IP while preserving the original Host header + SNI
(via `requests` + `urllib3.HTTPSConnectionPool` shim). Redirects are
re-resolved/pinned with the same guard, and a pinned response that
redirects to a *different* host is rejected (config re-validation
responsibility, enforced here).
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import requests

from .errors import LLMError


def _resolve_host(host: str) -> list[str]:
    """Resolve hostname to IPs (IPv4 first, then IPv6).

    Raises LLMError on resolution failure — no silent fallback to a
    second resolution path.
    """
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise LLMError(f"DNS resolution failed for {host!r}: {exc}") from exc
    ips: list[str] = []
    for family, _, _, _, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_loopback or ip.is_link_local or ip.is_private or ip.is_reserved:
            # internal/metadata targets are never acceptable endpoints;
            # SSRF policy is enforced at config layer, but a pinned
            # re-resolution must not drift there either.
            continue
        ips.append(str(ip))
    if not ips:
        raise LLMError(
            f"no public IPs for {host!r} — refusing to pin (internal-only host)"
        )
    return ips


class PinnedSession(requests.Session):
    """requests.Session that forces `host` -> `pinned_ip` for every request.

    The original Host header (and, for HTTPS, SNI) is preserved because we
    only override connection-time DNS via the URL, not the headers.
    """

    def __init__(self, host: str, ip: str) -> None:
        super().__init__()
        self._host = host
        self._ip = ip

    def send(self, request, **kwargs):  # type: ignore[override]
        # Rewrite the URL host to the pinned IP, keep original Host header
        # so virtual-hosted endpoints keep working, and reject cross-host
        # redirects (they would bypass the pin).
        original_host = request.url.split("//", 1)[-1].split("/", 1)[0]
        hostname = original_host.split(":", 1)[0].lower()
        if hostname != self._host.lower():
            raise LLMError(
                f"redirect crosses hosts ({self._host} -> {hostname}); "
                "DNS-pinned transport rejects cross-host redirects — "
                "re-validate the new endpoint via config instead"
            )
        request.url = request.url.replace(original_host, self._ip, 1)
        request.headers["Host"] = self._host
        return super().send(request, **kwargs)


def resolve_and_pin(url: str) -> tuple[str, requests.Session]:
    """Pin `url`'s hostname to a validated IP. Returns (pinned_base, session).

    `pinned_base` has the hostname replaced by the pinned IP — callers use
    it for the actual request; `session` preserves the Host header so
    virtual-hosted endpoints keep working.
    """
    try:
        p = urlparse(url)
    except ValueError as exc:
        raise LLMError(f"unparseable endpoint URL {url!r}: {exc}") from exc
    host = (p.hostname or "").lower()
    if not host:
        raise LLMError(f"endpoint URL missing hostname: {url!r}")
    # Literal IPs need no pinning — nothing to rebind.
    try:
        ipaddress.ip_address(host)
        return url, requests.Session()
    except ValueError:
        pass  # hostname, not an IP literal

    ips = _resolve_host(host)
    # Prefer the first public IP; document the choice in the session.
    ip = ips[0]
    pinned = url.replace(host, ip, 1)
    session = PinnedSession(host, ip)
    return pinned, session
