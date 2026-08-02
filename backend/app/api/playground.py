"""Playground — drive the generated server over the real MCP protocol.

Every call here spawns the actual generated package as an MCP server and talks
to it over stdio, so the playground exercises the code the user downloads.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import db
from ..config import get_settings
from ..playground import mcp_runner
from ..playground.mcp_runner import McpRunError
from ..playground.netguard import EgressError, check_url

router = APIRouter(prefix="/api/playground", tags=["playground"])


class SessionRequest(BaseModel):
    base_url: str = ""
    credential: str = ""


class CallRequest(SessionRequest):
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)


def _files_for(project_id: str):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    if not project.generate_result:
        raise HTTPException(400, "Generate the server before opening the playground")
    return project, project.generate_result.files


@router.post("/{project_id}/tools")
async def list_tools(project_id: str, req: SessionRequest):
    """Start the generated server and return the tools it actually advertises."""
    project, files = _files_for(project_id)
    base_url = _resolve_target(project, req.base_url)
    try:
        tools = await mcp_runner.list_tools(
            files, base_url, req.credential, get_settings().playground_timeout
        )
    except McpRunError as e:
        raise HTTPException(400, str(e))
    return {"tools": tools}


@router.post("/{project_id}/call")
async def call_tool(project_id: str, req: CallRequest):
    """Invoke one tool on the running generated server."""
    project, files = _files_for(project_id)
    base_url = _resolve_target(project, req.base_url)
    try:
        result = await mcp_runner.call_tool(
            files,
            base_url,
            req.credential,
            req.tool,
            req.args,
            get_settings().playground_timeout,
        )
    except McpRunError as e:
        raise HTTPException(400, str(e))

    # A successful round-trip means the generated code ran end to end.
    if project.status != "tested" and not result["is_error"]:
        project.status = "tested"
        db.save_project(project)
    return result


def _resolve_target(project, requested: str) -> str:
    """Pick the base URL for this run and confirm we're allowed to reach it.

    The child process does its own networking, so this is the only chokepoint.
    SDK servers call a library in-process and have no URL to check.
    """
    parse = project.parse_result
    if parse and parse.kind == "python_sdk":
        return ""

    base_url = requested or (parse.base_url if parse else "")
    if not base_url:
        raise HTTPException(400, "No base URL configured for this server")
    try:
        check_url(base_url)
    except EgressError as e:
        raise HTTPException(400, str(e))
    return base_url
