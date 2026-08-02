"""Parse (spec -> tool proposal) and Generate (proposal -> server files)."""
from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import db
from ..config import get_settings
from ..generation import codegen, proposer, sdk_introspect, validator
from ..generation.openapi_parser import SpecParseError, parse_spec
from ..models import (
    GenerateRequest,
    GenerateResult,
    ParseRequest,
    ParseResult,
)

router = APIRouter(prefix="/api", tags=["generation"])


@router.get("/config")
def public_config() -> dict:
    return get_settings().as_public_dict()


@router.post("/projects/{project_id}/parse")
def parse(project_id: str, req: ParseRequest) -> ParseResult:
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    spec_text = req.spec_text
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
def parse_sdk(project_id: str, req: SdkParseRequest) -> ParseResult:
    """Introspect an installed Python library into a tool proposal.

    Gated by ENABLE_SDK_INTROSPECTION — importing a module runs its code.
    """
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
def generate(project_id: str, req: GenerateRequest) -> GenerateResult:
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


def _fetch_spec(url: str) -> str:
    try:
        r = httpx.get(url, timeout=20, follow_redirects=True)
        r.raise_for_status()
        return r.text
    except httpx.HTTPError as e:
        raise HTTPException(400, f"Could not fetch spec from URL: {e}")
