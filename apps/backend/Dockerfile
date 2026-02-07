# Agent Analysis API - Python FastAPI backend for Cloud Run
# Build from repo root so search/ is available. Example:
#   docker build -f apps/backend/Dockerfile .
#   gcloud builds submit --config=apps/backend/cloudbuild.yaml .
FROM python:3.12-slim

WORKDIR /app

# Install uv and use it for deps and runtime (same flow as local: uv sync, uv run)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV UV_SYSTEM_PYTHON=1

# Copy dependency manifests first for layer caching
COPY apps/backend/pyproject.toml apps/backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy backend source
COPY apps/backend/src/ ./src/

# Copy search package (RAG) — backend imports "from search.query.pipeline"
COPY search/ ./search/
# Copy FAISS index (search_index/index.faiss, index.pkl) — RAG needs it at runtime
COPY search_index/ ./search_index/
ENV PYTHONPATH=/app

# Cloud Run sets PORT; default 8000 for local runs
ENV PORT=8000
EXPOSE 8000

# Run from src so "from db import" resolves; uv run uses synced env
CMD ["sh", "-c", "cd src && uv run uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
