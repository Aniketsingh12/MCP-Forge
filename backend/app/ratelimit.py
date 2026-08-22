"""In-process, per-client rate limiting.

Deliberately dependency-free and in-memory: this ships as a single container, so
a shared store (Redis) would be infrastructure bought for no benefit. The
tradeoff is real and worth stating -- counters live per instance and reset on
redeploy, so this throttles casual abuse and runaway loops. It is NOT a spending
guarantee. That has to come from a cap at the model provider, which holds even
if this process restarts or a bug lets a request through.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from .config import get_settings

_lock = threading.Lock()
_hits: dict[str, deque[float]] = defaultdict(deque)
# A stream of one-off source addresses would otherwise grow this map forever.
_MAX_TRACKED_KEYS = 10_000


def client_ip(request: Request) -> str:
    """Best-effort client identity.

    Railway (like most PaaS proxies) terminates TLS and forwards the original
    address in X-Forwarded-For, so request.client.host alone would bucket every
    visitor together as the proxy. The left-most XFF entry is the client -- but
    it is caller-supplied, so treat this as a throttle, never as authentication.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


def enforce(request: Request, bucket: str, limit: int, window_seconds: float) -> None:
    """Raise 429 if this client exceeded ``limit`` calls to ``bucket`` in the window."""
    if not get_settings().rate_limit_enabled:
        return

    key = f"{bucket}:{client_ip(request)}"
    now = time.monotonic()
    cutoff = now - window_seconds

    with _lock:
        if len(_hits) > _MAX_TRACKED_KEYS:
            _hits.clear()
        stamps = _hits[key]
        while stamps and stamps[0] < cutoff:
            stamps.popleft()
        if len(stamps) >= limit:
            retry_after = max(1, int(stamps[0] + window_seconds - now))
            raise HTTPException(
                429,
                f"Rate limit reached ({limit} per {_human(window_seconds)}). "
                f"Try again in {retry_after}s.",
                headers={"Retry-After": str(retry_after)},
            )
        stamps.append(now)


def _human(seconds: float) -> str:
    if seconds >= 3600:
        return f"{int(seconds // 3600)}h"
    if seconds >= 60:
        return f"{int(seconds // 60)}min"
    return f"{int(seconds)}s"


def reset() -> None:
    """Clear all counters (tests)."""
    with _lock:
        _hits.clear()
