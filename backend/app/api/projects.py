"""Project CRUD."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response

from .. import db, ratelimit
from ..models import ProjectCreate, ProjectState

router = APIRouter(prefix="/api/projects", tags=["projects"])

# Each project is a row plus a JSON blob, so unbounded creation is a disk
# and database-growth vector even though it costs no model credits.
_CREATE_LIMIT, _CREATE_WINDOW = 40, 600.0


@router.get("")
def list_projects() -> list[ProjectState]:
    return db.list_projects()


@router.post("", status_code=201)
def create_project(payload: ProjectCreate, request: Request) -> ProjectState:
    ratelimit.enforce(request, "create_project", _CREATE_LIMIT, _CREATE_WINDOW)
    return db.create_project(payload)


@router.get("/{project_id}")
def get_project(project_id: str) -> ProjectState:
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.delete("/{project_id}", status_code=204, response_class=Response)
def delete_project(project_id: str) -> Response:
    if not db.delete_project(project_id):
        raise HTTPException(404, "Project not found")
    return Response(status_code=204)
