"""Playground — fire a single generated tool against the live API."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..models import TestToolRequest, TestToolResult
from ..playground.tester import PlaygroundError, run_tool

router = APIRouter(prefix="/api/playground", tags=["playground"])


@router.post("/test")
def test_tool(req: TestToolRequest) -> TestToolResult:
    try:
        return run_tool(req)
    except PlaygroundError as e:
        raise HTTPException(400, str(e))
