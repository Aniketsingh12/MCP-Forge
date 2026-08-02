"""Run a generated server as a real MCP server and drive it over stdio.

This is what makes the playground meaningful: instead of re-implementing what
the generated code *would* do, we materialise the actual package, launch it with
the official MCP SDK's stdio client, complete the protocol handshake, and call
its tools. What you test is the code you download.

Isolation: the child is a separate process with a scrubbed environment (it
receives only PATH plus the API base URL/credential), a temp working directory
that is deleted afterwards, and a hard timeout. That is process-level isolation,
not a container — see the README for the sandboxing caveat.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..models import GeneratedFile


class McpRunError(RuntimeError):
    pass


def materialise(files: list[GeneratedFile]) -> Path:
    """Write the generated package to a fresh temp directory."""
    root = Path(tempfile.mkdtemp(prefix="mcpforge_run_"))
    for f in files:
        target = root / f.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f.content, encoding="utf-8")
    return root


def _child_env(base_url: str, credential: str) -> dict[str, str]:
    """Minimal environment for the child: no inherited secrets."""
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8",
        # Surface the outgoing request in tool results so the playground can
        # show a request trace without re-deriving it.
        "MCP_FORGE_DEBUG": "1",
    }
    # Windows needs these for the interpreter to start at all.
    for key in ("SYSTEMROOT", "SystemRoot", "COMSPEC", "TEMP", "TMP", "APPDATA"):
        if key in os.environ:
            env[key] = os.environ[key]
    if base_url:
        env["API_BASE_URL"] = base_url
    if credential:
        env["API_CREDENTIAL"] = credential
    return env


@asynccontextmanager
async def _session(root: Path, base_url: str, credential: str, timeout: float):
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(root / "server.py")],
        env=_child_env(base_url, credential),
        cwd=str(root),
    )
    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
    except McpRunError:
        raise
    except Exception as exc:  # protocol/startup failures surface here
        raise McpRunError(f"could not start generated server: {exc}") from exc


async def list_tools(
    files: list[GeneratedFile], base_url: str, credential: str, timeout: float
) -> list[dict[str, Any]]:
    """Handshake with the generated server and return its advertised tools."""
    root = materialise(files)
    try:
        async with _session(root, base_url, credential, timeout) as session:
            result = await session.list_tools()
            return [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "input_schema": t.inputSchema,
                }
                for t in result.tools
            ]
    finally:
        shutil.rmtree(root, ignore_errors=True)


async def call_tool(
    files: list[GeneratedFile],
    base_url: str,
    credential: str,
    tool_name: str,
    args: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    """Invoke one tool over MCP and return a structured trace of the exchange."""
    root = materialise(files)
    started = time.monotonic()
    try:
        async with _session(root, base_url, credential, timeout) as session:
            result = await session.call_tool(tool_name, args)
            elapsed = int((time.monotonic() - started) * 1000)

            text_blocks: list[str] = []
            for block in result.content:
                text = getattr(block, "text", None)
                if isinstance(text, str):
                    text_blocks.append(text)

            return {
                "tool": tool_name,
                "args": args,
                "is_error": bool(result.isError),
                # structuredContent is what an agent actually consumes.
                "structured": getattr(result, "structuredContent", None),
                "text": "\n".join(text_blocks),
                "latency_ms": elapsed,
            }
    finally:
        shutil.rmtree(root, ignore_errors=True)
