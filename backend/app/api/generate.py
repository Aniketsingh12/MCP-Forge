"""Parse (spec -> tool proposal) and Generate (proposal -> server files)."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from .. import db, llm, ratelimit
from ..config import get_settings
from ..generation import codegen, proposer, sdk_introspect, validator
from ..generation.openapi_parser import SpecParseError, parse_spec
from ..models import (
    GenerateRequest,
    GenerateResult,
    ParseRequest,
    ParseResult,
)
from ..netguard import EgressError, safe_get

router = APIRouter(prefix="/api", tags=["generation"])

# Parsing is cheap but fetches a URL and can invoke a model; generation is pure
# CPU. Both are generous enough for real exploration, bounded enough that a loop
# can't run away.
_PARSE_LIMIT, _PARSE_WINDOW = 30, 600.0
_GENERATE_LIMIT, _GENERATE_WINDOW = 60, 600.0
# The model round-trip is the one endpoint that always costs money when enabled.
_LLM_TEST_LIMIT, _LLM_TEST_WINDOW = 5, 600.0


def _require_llm_access(request: Request) -> None:
    """Gate the metered path behind a shared secret, when one is configured.

    No key set (the default) means polishing is open — correct for local use.
    On a public deploy, setting LLM_ACCESS_KEY keeps the whole deterministic
    demo reachable while making the billable path private.
    """
    configured = get_settings().llm_access_key
    if not configured:
        return
    supplied = request.headers.get("x-llm-access-key", "")
    # Constant-time: a plain == leaks the key a character at a time under timing.
    if not secrets.compare_digest(supplied, configured):
        raise HTTPException(
            403,
            "Description polishing requires an access key on this deployment. "
            "Generation itself is unaffected — it never uses a model.",
        )


@router.get("/config")
def public_config() -> dict:
    return get_settings().as_public_dict()


@router.get("/llm/test")
def llm_test(request: Request) -> dict:
    """Round-trip the configured model so a bad key or model id fails loudly.

    Description polishing degrades silently by design, so this is the way to
    confirm credentials actually work — useful right after a deploy. It spends
    (a little) money on every call, so it carries the access gate and the
    tightest rate limit of any endpoint.
    """
    ratelimit.enforce(request, "llm_test", _LLM_TEST_LIMIT, _LLM_TEST_WINDOW)
    _require_llm_access(request)
    settings = get_settings()
    if not llm.is_enabled():
        return {
            "ok": False,
            "provider": settings.llm_provider,
            "error": "LLM is disabled. Set LLM_PROVIDER to enable it.",
        }
    try:
        reply = llm.complete(
            "You are a terse assistant.",
            "Reply with the single word: ready",
        )
    except llm.LLMError as exc:
        return {
            "ok": False,
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "error": str(exc),
        }
    return {
        "ok": True,
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "reply": reply.strip()[:200],
    }


@router.post("/projects/{project_id}/parse")
def parse(project_id: str, req: ParseRequest, request: Request) -> ParseResult:
    ratelimit.enforce(request, "parse", _PARSE_LIMIT, _PARSE_WINDOW)
    if req.use_llm:
        _require_llm_access(request)

    project = db.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    settings = get_settings()
    spec_text = req.spec_text
    if spec_text:
        _check_spec_size(len(spec_text.encode("utf-8")), settings.max_spec_bytes)
    if not spec_text and req.spec_url:
        spec_text = _fetch_spec(req.spec_url)
    if not spec_text:
        raise HTTPException(400, "Provide spec_text or spec_url")

    try:
        result = parse_spec(spec_text)
    except SpecParseError as e:
        raise HTTPException(422, f"Could not parse spec: {e}")

    if req.use_llm:
        result = proposer.polish_descriptions(result)

    project.parse_result = result
    project.status = "proposed"
    db.save_project(project)
    return result


class SdkParseRequest(BaseModel):
    module: str
    use_llm: bool = False


@router.post("/projects/{project_id}/parse-sdk")
def parse_sdk(project_id: str, req: SdkParseRequest, request: Request) -> ParseResult:
    """Introspect an installed Python library into a tool proposal.

    Gated by ENABLE_SDK_INTROSPECTION — importing a module runs its code.
    """
    ratelimit.enforce(request, "parse", _PARSE_LIMIT, _PARSE_WINDOW)
    if req.use_llm:
        _require_llm_access(request)

    project = db.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    try:
        result = sdk_introspect.introspect(req.module)
    except sdk_introspect.SdkIntrospectError as e:
        raise HTTPException(422, str(e))

    if req.use_llm:
        result = proposer.polish_descriptions(result)

    project.parse_result = result
    project.status = "proposed"
    db.save_project(project)
    return result


@router.post("/projects/{project_id}/generate")
def generate(project_id: str, req: GenerateRequest, request: Request) -> GenerateResult:
    ratelimit.enforce(request, "generate", _GENERATE_LIMIT, _GENERATE_WINDOW)
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    enabled = [t for t in req.tools if t.enabled]
    if not enabled:
        raise HTTPException(400, "Enable at least one tool before generating")

    files = codegen.generate(req)
    ok, messages = validator.validate(files)

    result = GenerateResult(
        server_slug=codegen._safe_slug(req.server_slug),
        files=files,
        valid=ok,
        validation_messages=messages,
    )
    project.generate_result = result
    project.status = "generated"
    db.save_project(project)
    return result


def _check_spec_size(size: int, limit: int) -> None:
    if size > limit:
        raise HTTPException(
            413,
            f"Spec is {size // 1000} kB, over the {limit // 1000} kB limit. "
            "Trim it, or raise MAX_SPEC_BYTES.",
        )


def _fetch_spec(url: str) -> str:
    """Fetch a user-supplied spec URL under the egress policy.

    The URL comes from the caller, so this is a server-side request forgery
    vector: without the guard, anyone could make this container fetch internal
    addresses. safe_get() re-validates every redirect hop (a public URL that
    302s to an internal one would otherwise slip past a single up-front check)
    and caps the response size.
    """
    settings = get_settings()
    try:
        return safe_get(
            url,
            timeout=20,
            max_bytes=settings.max_spec_bytes,
        )
    except EgressError as e:
        raise HTTPException(400, str(e))
    except Exception as e:  # transport/status failures
        raise HTTPException(400, f"Could not fetch spec from URL: {e}")
