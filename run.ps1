# MCP Forge — one-command run (no Docker).
#   .\run.ps1
# Builds the frontend, bundles it into the backend, and serves everything
# from FastAPI on http://localhost:8000
#
# Requirements: Python 3.10+ and Node 18+ on PATH.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "==> Backend: virtualenv + deps" -ForegroundColor Yellow
Set-Location "$root\backend"
if (-not (Test-Path ".venv")) { python -m venv .venv }
& ".\.venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt

Write-Host "==> Frontend: install + build" -ForegroundColor Yellow
Set-Location "$root\frontend"
if (-not (Test-Path "node_modules")) { npm install --no-audit --no-fund }
npm run build

Write-Host "==> Bundling frontend into backend" -ForegroundColor Yellow
if (Test-Path "$root\backend\static") { Remove-Item -Recurse -Force "$root\backend\static" }
Copy-Item -Recurse "$root\frontend\dist" "$root\backend\static"

Write-Host "==> Serving on http://localhost:8000  (Ctrl+C to stop)" -ForegroundColor Green
Set-Location "$root\backend"
& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
