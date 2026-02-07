# Agent Analysis API - Python FastAPI backend for Cloud Run
FROM python:3.12-slim

WORKDIR /app

# Install uv and use it for deps and runtime (same flow as local: uv sync, uv run)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV UV_SYSTEM_PYTHON=1

# Copy dependency manifests first for layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source
COPY src/ ./src/

# Cloud Run sets PORT; default 8000 for local runs
ENV PORT=8000
EXPOSE 8000

# Run from src so "from db import" resolves; uv run uses synced env
CMD ["sh", "-c", "cd src && uv run uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
