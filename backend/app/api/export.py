"""Export — download the generated server as a zip package."""
from __future__ import annotations

import io
import zipfile

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from .. import db

router = APIRouter(prefix="/api", tags=["export"])


@router.get("/projects/{project_id}/download")
def download(project_id: str):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    if not project.generate_result:
        raise HTTPException(400, "Nothing generated yet")

    slug = project.generate_result.server_slug
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in project.generate_result.files:
            zf.writestr(f"{slug}/{f.path}", f.content)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{slug}.zip"'},
    )
