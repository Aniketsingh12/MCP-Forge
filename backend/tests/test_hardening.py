"""Abuse-resistance checks for a publicly reachable deployment.

These cover the boundary rather than the pipeline: who may spend model credits,
where the server may be made to send requests, and how often. They are written
as regression tests because each one corresponds to a hole that was actually
open at some point.
"""
import json
import os
import pathlib
import sys
import tempfile

# The app builds its data dir and opens SQLite at import time, so point it at a
# throwaway directory *before* importing anything from app.
os.environ["MCPFORGE_DATA_DIR"] = tempfile.mkdtemp(prefix="mcpforge_tests_")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import netguard, ratelimit  # noqa: E402
from app.config import get_settings  # noqa: E402

get_settings.cache_clear()
from app.main import app  # noqa: E402

client = TestClient(app)

SPEC = json.dumps({
    "openapi": "3.0.0",
    "info": {"title": "T", "version": "1"},
    "servers": [{"url": "https://api.example.com"}],
    "paths": {"/things": {"get": {"operationId": "listThings", "summary": "List"}}},
})


@pytest.fixture(autouse=True)
def _clean():
    ratelimit.reset()
    get_settings.cache_clear()
    yield
    ratelimit.reset()
    get_settings.cache_clear()


def _project() -> str:
    return client.post("/api/projects", json={"name": "t"}).json()["id"]


@pytest.mark.parametrize("target", [
    "http://127.0.0.1:8000/x",
    "http://localhost/x",
    "http://169.254.169.254/latest/meta-data/",   # cloud metadata endpoint
    "http://10.0.0.1/x",
    "file:///etc/passwd",
])
def test_spec_url_cannot_reach_internal_addresses(target):
    """spec_url is fetched *by the server*, so it is an SSRF vector.

    This path was unguarded while the playground's identical risk was covered.
    """
    r = client.post(f"/api/projects/{_project()}/parse", json={"spec_url": target})
    assert r.status_code == 400, r.text


def test_redirect_hops_are_revalidated():
    """A public URL that 302s to an internal one must not slip through.

    Validating only the URL the user supplied is the classic bypass, so assert
    every hop reaches the guard — not just the first.
    """
    checked: list[str] = []
    real_check = netguard.check_url
    real_stream = netguard.httpx.stream

    class FakeResponse:
        def __init__(self, redirect_to=None):
            self.is_redirect = redirect_to is not None
            self.headers = {"location": redirect_to} if redirect_to else {}

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def raise_for_status(self):
            pass

        def iter_bytes(self):
            yield b'{"openapi": "3.0.0"}'

    hops = iter([FakeResponse("http://169.254.169.254/steal"), FakeResponse()])
    netguard.check_url = lambda url: (checked.append(url), real_check(url))[1]
    netguard.httpx.stream = lambda *a, **k: next(hops)
    try:
        with pytest.raises(netguard.EgressError):
            netguard.safe_get("https://example.com/s.json", timeout=5, max_bytes=1000)
    finally:
        netguard.check_url = real_check
        netguard.httpx.stream = real_stream

    assert len(checked) == 2, f"only validated {checked}"


def test_llm_access_key_gates_only_the_metered_path(monkeypatch):
    """Polishing is the sole feature that spends credits; everything else is free.

    So the key must gate that one path and leave the rest of the demo open.
    """
    monkeypatch.setenv("LLM_ACCESS_KEY", "s3cret")
    monkeypatch.setenv("LLM_PROVIDER", "together")
    get_settings.cache_clear()
    pid = _project()

    assert client.post(f"/api/projects/{pid}/parse",
                       json={"spec_text": SPEC, "use_llm": True}).status_code == 403
    assert client.post(f"/api/projects/{pid}/parse",
                       json={"spec_text": SPEC, "use_llm": True},
                       headers={"X-LLM-Access-Key": "wrong"}).status_code == 403
    assert client.get("/api/llm/test").status_code == 403

    free = client.post(f"/api/projects/{pid}/parse", json={"spec_text": SPEC})
    assert free.status_code == 200 and len(free.json()["tools"]) == 1


def test_access_key_is_never_exposed_to_clients(monkeypatch):
    monkeypatch.setenv("LLM_ACCESS_KEY", "s3cret")
    get_settings.cache_clear()
    for path in ("/api/config", "/api/health"):
        body = client.get(path).text
        assert "s3cret" not in body, path
    assert client.get("/api/config").json()["llm_requires_key"] is True


def test_oversized_spec_is_rejected():
    """Specs are parsed in memory, so an unbounded body is a memory DoS."""
    r = client.post(f"/api/projects/{_project()}/parse",
                    json={"spec_text": "x" * 2_500_000})
    assert r.status_code == 413


def test_rate_limit_trips_and_advertises_retry_after():
    pid = _project()
    codes = [client.post(f"/api/projects/{pid}/parse",
                         json={"spec_text": SPEC}).status_code for _ in range(32)]
    assert codes[:30] == [200] * 30, f"unexpected: {set(codes[:30])}"
    assert codes[30] == 429
    limited = client.post(f"/api/projects/{pid}/parse", json={"spec_text": SPEC})
    assert "retry-after" in {k.lower() for k in limited.headers}
