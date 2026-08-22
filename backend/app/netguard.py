"""Egress guard for every outbound URL the platform fetches or hands to a child.

Two callers rely on this:

  * the playground, whose generated server runs as a child process and makes its
    own HTTP calls -- so the only chokepoint is *before* we launch it; and
  * spec fetching, where the user supplies a URL the backend itself retrieves.

Policy: an optional allowlist (PLAYGROUND_ALLOWLIST) restricts permitted hosts,
and private/loopback/link-local addresses are always refused.

Known limitation: this resolves DNS to validate, then the caller resolves again
when it connects, leaving a rebinding window. Closing that requires pinning the
connection to the validated address.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import httpx

from .config import get_settings


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


def safe_get(url: str, *, timeout: float, max_bytes: int, max_redirects: int = 5) -> str:
    """GET ``url`` with the egress policy enforced at *every* redirect hop.

    httpx's ``follow_redirects=True`` would quietly defeat check_url(): a public
    URL passes validation, then 302s the client to an internal one. So redirects
    are followed by hand and each hop is re-validated. The body is size-capped
    too, since the response comes from a host the caller chose, not us.
    """
    current = url
    for _ in range(max_redirects + 1):
        check_url(current)
        with httpx.stream(
            "GET", current, timeout=timeout, follow_redirects=False
        ) as response:
            if response.is_redirect:
                location = response.headers.get("location", "")
                if not location:
                    raise EgressError("Redirect response had no Location header")
                # Relative redirects are legal; resolve against the current URL.
                current = str(httpx.URL(current).join(location))
                continue
            response.raise_for_status()
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > max_bytes:
                    raise EgressError(
                        f"Spec is larger than the {max_bytes // 1_000_000} MB limit"
                    )
                chunks.append(chunk)
            return b"".join(chunks).decode("utf-8", errors="replace")
    raise EgressError(f"Too many redirects (more than {max_redirects})")
