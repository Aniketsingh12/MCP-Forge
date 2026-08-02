"""Egress guard for playground targets.

The generated server runs as a child process and makes its own HTTP calls, so
the only place we can constrain where it reaches is *before* we launch it: the
base URL is validated here and passed in via the environment.

  * An optional allowlist (PLAYGROUND_ALLOWLIST) restricts permitted hosts.
  * Private/loopback/link-local addresses are refused (SSRF guard).

Known limitation: this resolves DNS to validate, then the child resolves again
when it connects, leaving a rebinding window. Closing that requires pinning the
connection to the validated address inside the generated client.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from ..config import get_settings


class EgressError(RuntimeError):
    pass


def check_url(url: str) -> None:
    """Raise EgressError unless ``url`` points at a permitted public host."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise EgressError(f"Unsupported URL scheme: {parsed.scheme or '(none)'}")
    host = parsed.hostname or ""
    if not host:
        raise EgressError("URL has no host")

    allowlist = get_settings().playground_allowlist
    if allowlist and not any(
        host.lower() == a or host.lower().endswith("." + a) for a in allowlist
    ):
        raise EgressError(
            f"Host '{host}' is not in the playground allowlist. "
            "Set PLAYGROUND_ALLOWLIST to permit it."
        )

    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise EgressError(f"Could not resolve host '{host}': {exc}")
    for info in infos:
        ip = _unwrap(ipaddress.ip_address(info[4][0]))
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_unspecified
            or ip.is_multicast
        ):
            raise EgressError(f"Refusing to call internal address {ip} (host '{host}')")


# NAT64 well-known prefix (RFC 6052) — an IPv6 wrapper around a public IPv4.
_NAT64 = ipaddress.IPv6Network("64:ff9b::/96")


def _unwrap(ip):
    """Resolve IPv4-mapped and NAT64 IPv6 addresses to the embedded IPv4.

    On IPv6-only / NAT64 networks a public IPv4 host resolves to an address like
    ``64:ff9b::<v4>`` which naive checks misflag as internal. Evaluate the real
    embedded IPv4 instead so genuinely public hosts are allowed.
    """
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped:
            return ip.ipv4_mapped
        if ip in _NAT64:
            return ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
    return ip
