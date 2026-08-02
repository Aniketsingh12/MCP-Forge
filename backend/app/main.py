"""MCP Forge API entrypoint."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import db
from .api import export, generate, playground, projects
from .config import get_settings

app = FastAPI(title="MCP Forge", version="0.1.0")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


db.init_db()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", **settings.as_public_dict()}


app.include_router(projects.router)
app.include_router(generate.router)
app.include_router(playground.router)
app.include_router(export.router)


# --------------------------------------------------------------------------- #
# Serve the built frontend (single-container deploy). If the build isn't
# present (dev mode with a separate Vite server), these routes simply don't
# mount and CORS handles the split origin.
# --------------------------------------------------------------------------- #
_FRONTEND_DIST = (Path(__file__).resolve().parent.parent / "static").resolve()
if _FRONTEND_DIST.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=_FRONTEND_DIST / "assets"),
        name="assets",
    )

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        # Serve real files if they exist, else fall back to index.html (SPA routing).
        #
        # The requested path is untrusted: it must be confined to the static
        # directory, or a request like `/../../.env` would read arbitrary files
        # off the host. Resolve symlinks/`..` first, then verify containment.
        if full_path:
            candidate = (_FRONTEND_DIST / full_path).resolve()
            if candidate.is_file() and candidate.is_relative_to(_FRONTEND_DIST):
                return FileResponse(candidate)
        return FileResponse(_FRONTEND_DIST / "index.html")
