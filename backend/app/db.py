"""Tiny SQLite persistence layer.

Projects are stored as a single JSON blob per row. This keeps the schema
trivial while letting the rich Pydantic models evolve freely — plenty for the
MVP, and it deploys with zero external services.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional

from .config import get_settings
from .models import ProjectCreate, ProjectState


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(get_settings().db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                data TEXT NOT NULL
            )
            """
        )
        conn.commit()


def create_project(payload: ProjectCreate) -> ProjectState:
    now = _now()
    state = ProjectState(
        id=uuid.uuid4().hex[:12],
        name=payload.name.strip() or "Untitled server",
        description=payload.description,
        status="draft",
        created_at=now,
        updated_at=now,
    )
    _save(state)
    return state


def _save(state: ProjectState) -> None:
    state.updated_at = _now()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO projects (id, name, status, updated_at, data)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                status=excluded.status,
                updated_at=excluded.updated_at,
                data=excluded.data
            """,
            (state.id, state.name, state.status, state.updated_at, state.model_dump_json()),
        )
        conn.commit()


def save_project(state: ProjectState) -> ProjectState:
    _save(state)
    return state


def get_project(project_id: str) -> Optional[ProjectState]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT data FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
    if not row:
        return None
    return ProjectState.model_validate_json(row["data"])


def list_projects() -> list[ProjectState]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT data FROM projects ORDER BY updated_at DESC"
        ).fetchall()
    return [ProjectState.model_validate_json(r["data"]) for r in rows]


def delete_project(project_id: str) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
        return cur.rowcount > 0
