# syntax=docker/dockerfile:1
# Multi-stage build: compile the React frontend, then serve it from FastAPI as
# a single, self-contained container. One image, one process, one port.

# --- Stage 1: build frontend ------------------------------------------------ #
FROM node:22-alpine AS frontend
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# --- Stage 2: backend runtime ----------------------------------------------- #
FROM python:3.11-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MCPFORGE_DATA_DIR=/data

WORKDIR /app

# Install backend deps first for better layer caching.
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App code + built frontend (served from ./static by app.main).
COPY backend/ ./
COPY --from=frontend /web/dist ./static

# Data dir for the SQLite database. Deliberately NOT a `VOLUME` instruction:
# Railway rejects Dockerfiles containing VOLUME at validation time ("docker
# VOLUME ... is not supported, use Railway Volumes") and persistence there is
# configured by attaching a Railway Volume mounted at /data. docker-compose
# declares its own named volume for the same path, so nothing is lost locally.
RUN mkdir -p /data

EXPOSE 8000
# Railway/Render inject $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
