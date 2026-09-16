"""Audit S2+S3 (2026-09-16): the shared SSRF policy core.

Two independent implementations had drifted into the codebase
(psg/automation/validation.py and psg/validation/online.py): both encode
"which IPs may never be an HTTP endpoint". A drift in one would not fix
the other — the classic split-brain security bug. This module is the
single source of truth for:

  - blocked host strings (metadata endpoints, loopback names)
  - blocked IP networks (private/loopback/link-local/reserved)
  - IP classification (is_blocked_ip)
  - hostname resolution (resolve_host_ips)

Callers keep their own semantics: automation.validation is the offline
config-gate predicate, validation.online adds HTTP HEAD + redirect walk
+ rate limiting on top of this core, and llm.dns_pin keeps its
request-time fail-closed resolution (it must remain a separate network
layer — see structure audit S3 discussion).
"""

from __future__ import annotations

import ipaddress
import socket
from typing import Union

IPAddress = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]

#: Hostname strings that must never be accepted as an endpoint host.
BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254", "::1"}

#: Networks that must never be accepted as an endpoint target.
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


def is_blocked_ip(ip: IPAddress) -> bool:
    """Check whether an IP falls into any blocked private/local range."""
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


def resolve_host_ips(hostname: str, port: int | None = None) -> set[IPAddress]:
    """Resolve hostname to all IPv4/IPv6 addresses.

    Raises socket.gaierror on resolution failure — callers decide whether
    that is fail-open (offline predicate) or fail-closed (request-time).
    """
    resolved: set[IPAddress] = set()
    infos = socket.getaddrinfo(
        hostname, port if port is not None else None, proto=socket.IPPROTO_TCP
    )
    for family, _, _, _, sockaddr in infos:
        resolved.add(ipaddress.ip_address(sockaddr[0]))
    return resolved