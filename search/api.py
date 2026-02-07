"""FastAPI application — exposes RAG query endpoints.

Flow:
    1.  POST /query        → submit job, get back {job_id, stream_url}
    2.  GET  /stream/{id}  → open stream URL, receive SSE tokens

Run:
    uvicorn search.api:app --reload --port 8000
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from threading import Lock

# Prevent OpenMP crash on macOS when FAISS + other libs both link libomp
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from search.query.pipeline import answer_question, answer_question_stream
from search.schemas import QueryRequest, QuerySubmitResponse, RagAnswer

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Trading Knowledge Search",
    description="RAG-powered trading knowledge assistant API",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── In-memory job store (replace with Redis later) ──────────────────

_JOB_TTL_SECS = 300  # jobs expire after 5 minutes
_jobs: dict[str, dict] = {}
_jobs_lock = Lock()


def _create_job(req: QueryRequest) -> str:
    """Store job params and return a new job_id."""
    job_id = uuid.uuid4().hex[:12]
    with _jobs_lock:
        _jobs[job_id] = {
            "request": req,
            "created_at": time.time(),
            "consumed": False,
        }
    return job_id


def _get_job(job_id: str) -> dict | None:
    """Retrieve and mark a job as consumed (single-use stream)."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return None
        if job["consumed"]:
            return None
        job["consumed"] = True
        return job


def _cleanup_expired() -> None:
    """Remove expired jobs (called lazily)."""
    now = time.time()
    with _jobs_lock:
        expired = [k for k, v in _jobs.items() if now - v["created_at"] > _JOB_TTL_SECS]
        for k in expired:
            del _jobs[k]


# ── Helpers ──────────────────────────────────────────────────────────


def _prompt_kwargs(req: QueryRequest) -> dict:
    """Extract prompt-override kwargs from the request (if any)."""
    if req.prompt_overrides is None:
        return {}
    return req.prompt_overrides.model_dump(exclude_none=True)


# ── Health ───────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Submit query → get stream URL ────────────────────────────────────


@app.post("/query", response_model=QuerySubmitResponse)
async def submit_query(req: QueryRequest, request: Request):
    """Accept a query and return a stream URL.

    The caller (frontend / upstream agent) should open the returned
    ``stream_url`` via GET to receive the answer as Server-Sent Events.
    """
    _cleanup_expired()

    job_id = _create_job(req)
    base_url = str(request.base_url).rstrip("/")
    stream_url = f"{base_url}/stream/{job_id}"

    logger.info("Job %s created for question: %s", job_id, req.question[:80])
    return QuerySubmitResponse(job_id=job_id, stream_url=stream_url)


# ── Stream endpoint (GET — EventSource-compatible) ───────────────────


@app.get("/stream/{job_id}")
async def stream(job_id: str):
    """Open an SSE stream for a previously submitted query.

    The frontend connects via ``new EventSource(stream_url)`` or a simple
    GET request.  Tokens arrive as ``data: <token>`` lines.  The final
    event is ``data: [DONE]``.

    Each stream URL is single-use; a second GET returns 410 Gone.
    """
    job = _get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=410,
            detail="Stream not found or already consumed. Submit a new /query.",
        )

    req: QueryRequest = job["request"]
    kwargs = _prompt_kwargs(req)

    async def _event_generator():
        async for token in answer_question_stream(
            question=req.question,
            trade_analysis=req.trade_analysis,
            **kwargs,
        ):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )


# ── Sync query (convenience / backward compat) ──────────────────────


@app.post("/query/sync", response_model=RagAnswer)
async def query_sync(req: QueryRequest):
    """Return a complete ``RagAnswer`` JSON response (no streaming).

    Use this for testing or when the caller does not need streaming.
    """
    return answer_question(
        question=req.question,
        trade_analysis=req.trade_analysis,
        **_prompt_kwargs(req),
    )
