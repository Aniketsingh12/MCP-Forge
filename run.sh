#!/usr/bin/env bash
# MCP Forge — one-command run (no Docker).
#   ./run.sh
# Builds the frontend, bundles it into the backend, and serves everything
# from FastAPI on http://localhost:8000
# Requirements: Python 3.10+ and Node 18+ on PATH.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PY=python3; command -v $PY >/dev/null 2>&1 || PY=python

echo "==> Backend: virtualenv + deps"
cd "$root/backend"
[ -d .venv ] || $PY -m venv .venv
# venv layout differs: Scripts/ on Windows (Git Bash), bin/ elsewhere
VENV_PY="./.venv/bin/python"; [ -x "$VENV_PY" ] || VENV_PY="./.venv/Scripts/python.exe"
$VENV_PY -m pip install --quiet --upgrade pip
$VENV_PY -m pip install --quiet -r requirements.txt

echo "==> Frontend: install + build"
cd "$root/frontend"
[ -d node_modules ] || npm install --no-audit --no-fund
npm run build

echo "==> Bundling frontend into backend"
rm -rf "$root/backend/static"
cp -r "$root/frontend/dist" "$root/backend/static"

echo "==> Serving on http://localhost:8000  (Ctrl+C to stop)"
cd "$root/backend"
exec $VENV_PY -m uvicorn app.main:app --host 0.0.0.0 --port 8000
