"""Playground tool execution.

Replicates exactly what a generated tool would do: builds the request from the
same auth config and parameter locations, fires it at the target API with the
user's session-scoped credential, and returns raw request + normalized response.

Safety:
  * Credentials are received per-call and never persisted.
  * An optional egress allowlist (PLAYGROUND_ALLOWLIST) restricts which hosts
    may be contacted, matching the spec's "egress limited to the target API".
  * Requests to private/loopback/link-local addresses are blocked (SSRF guard).
"""
from __future__ import annotations

import ipaddress
import socket
import time
from typing import Any
from urllib.parse import quote, urlparse

import httpx

from ..config import get_settings
from ..models import AuthConfig, TestToolRequest, TestToolResult


class PlaygroundError(RuntimeError):
    pass


def run_tool(req: TestToolRequest) -> TestToolResult:
    tool = req.tool
    base_url = (req.base_url or "").rstrip("/")
    if not base_url:
        raise PlaygroundError("No base URL configured for this server")

    path = tool.path
    path_params = {p.name: req.args.get(p.name) for p in tool.params if p.location == "path"}
    for key, value in path_params.items():
        if value is not None:
            # Percent-encode so a value cannot inject path segments or a query
            # string (and cannot slip the URL past the guard below).
            path = path.replace("{" + key + "}", quote(str(value), safe=""))

    url = base_url + path
    _guard_url(url)

    query: dict[str, Any] = {}
    headers: dict[str, str] = {"Accept": "application/json"}
    body: Any = None

    for p in tool.params:
        val = req.args.get(p.name)
        if val is None:
            continue
        if p.location == "query":
            query[p.name] = val
        elif p.location == "header":
            headers[p.name] = str(val)
        elif p.location == "body":
            body = val

    basic = _inject_auth(req.auth, req.credential, headers, query)
    # The auth header may carry any name from the spec, so redact that one too.
    sensitive = {req.auth.param_name.lower()} if req.auth.type != "none" else set()

    started = time.monotonic()
    try:
        with httpx.Client(timeout=get_settings().playground_timeout) as client:
            response = client.request(
                tool.method,
                url,
                params=query or None,
                json=body if body is not None else None,
                headers=headers,
                auth=basic,
            )
    except httpx.RequestError as exc:
        latency = int((time.monotonic() - started) * 1000)
        return TestToolResult(
            request_method=tool.method,
            request_url=url,
            request_headers=_redact(headers, sensitive),
            request_body=body,
            latency_ms=latency,
            normalized={"ok": False, "status": None, "error": f"network error: {exc}"},
            error=str(exc),
        )

    latency = int((time.monotonic() - started) * 1000)
    parsed_body, normalized = _normalize(response)

    return TestToolResult(
        request_method=tool.method,
        request_url=str(response.request.url),
        request_headers=_redact(headers, sensitive),
        request_body=body,
        status_code=response.status_code,
        response_headers=dict(response.headers),
        response_body=parsed_body,
        normalized=normalized,
        latency_ms=latency,
    )


# --------------------------------------------------------------------------- #
def _inject_auth(auth: AuthConfig, credential: str, headers: dict, query: dict):
    if not credential or auth.type == "none":
        return None
    if auth.type == "basic":
        if ":" in credential:
            user, _, pwd = credential.partition(":")
            return (user, pwd)
        return None
    if auth.type == "bearer":
        headers[auth.param_name] = (auth.value_prefix or "Bearer ") + credential
    else:  # api_key
        if auth.location == "query":
            query[auth.param_name] = credential
        else:
            headers[auth.param_name] = (auth.value_prefix or "") + credential
    return None


def _normalize(response: httpx.Response):
    ctype = response.headers.get("content-type", "")
    if "application/json" in ctype:
        try:
            data: Any = response.json()
        except Exception:
            data = response.text
    else:
        text = response.text
        data = text if len(text) <= 20000 else text[:20000] + "\n...[truncated]"

    if response.is_success:
        return data, {"ok": True, "status": response.status_code, "data": data}

    error = f"HTTP {response.status_code}"
    if isinstance(data, dict):
        for key in ("message", "error", "error_description", "detail"):
            if data.get(key):
                error = f"{error}: {data[key]}"
                break
    return data, {"ok": False, "status": response.status_code, "error": error, "data": data}


def _redact(headers: dict[str, str], extra: set[str] | None = None) -> dict[str, str]:
    always = {"authorization", "x-api-key", "api-key", "cookie"}
    sensitive = always | (extra or set())
    redacted = {}
    for k, v in headers.items():
        if k.lower() in sensitive:
            redacted[k] = _mask(v)
        else:
            redacted[k] = v
    return redacted


def _mask(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return value[:4] + "…" + value[-2:]


def _guard_url(url: str) -> None:
    """Enforce the egress allowlist and block SSRF to internal addresses."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise PlaygroundError(f"Unsupported URL scheme: {parsed.scheme}")
    host = parsed.hostname or ""
    if not host:
        raise PlaygroundError("URL has no host")

    allowlist = get_settings().playground_allowlist
    if allowlist and not any(host.lower() == a or host.lower().endswith("." + a) for a in allowlist):
        raise PlaygroundError(
            f"Host '{host}' is not in the playground allowlist. "
            "Set PLAYGROUND_ALLOWLIST to permit it."
        )

    # SSRF guard: resolve and reject private/loopback/link-local targets.
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise PlaygroundError(f"Could not resolve host '{host}': {exc}")
    for info in infos:
        ip = _unwrap(ipaddress.ip_address(info[4][0]))
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_unspecified or ip.is_multicast:
            raise PlaygroundError(
                f"Refusing to call internal address {ip} (host '{host}')"
            )


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
