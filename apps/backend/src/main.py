"""FastAPI app for Agent Analysis: JSON + chart → Analyst → Tutor → Explanations."""

import logging
import os
import sys
from pathlib import Path

# Prevent OpenMP crash on macOS when FAISS + other libs both link libomp
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from dotenv import load_dotenv

# Load .env: backend first (apps/backend/.env), then repo root (for shared vars)
_src_dir = Path(__file__).resolve().parent
_backend_root = _src_dir.parent  # src -> backend (apps/backend)
_root = _backend_root.parents[1]  # backend -> apps -> repo root
for env_path in (_backend_root / ".env", _root / ".env"):
    if env_path.exists():
        load_dotenv(env_path)

# Make search package importable when running from apps/backend
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

# Configure logging level (DEBUG, INFO, WARNING, ERROR). Default INFO.
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Reduce noise from third-party loggers unless DEBUG
if LOG_LEVEL != "DEBUG":
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

log = logging.getLogger("agent_analysis")
_gemini_key = os.getenv("GEMINI_API_KEY")
log.info(
    "GEMINI_API_KEY: %s (loaded from %s)",
    "set" if (_gemini_key and _gemini_key.strip()) else "NOT SET",
    _backend_root / ".env" if (_backend_root / ".env").exists() else _root / ".env",
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import init_db
from db.engine import check_connection, get_engine
from routes import analysis_router, transactions_router


class _SuppressInvalidHTTPFilter(logging.Filter):
    """Filter out Uvicorn's 'Invalid HTTP request received' (harmless proxy/client noise)."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "Invalid HTTP request received" not in record.getMessage()


logging.getLogger("uvicorn.error").addFilter(_SuppressInvalidHTTPFilter())

# Create DB tables and verify connection on startup
try:
    init_db()
    log.info("Database initialized and available")
except Exception as e:
    log.error("Database unavailable: %s", e, exc_info=True)
    raise

app = FastAPI(
    title="Agent Analysis API",
    description="Analyst + Tutor agents for personalised trade education",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis_router)
app.include_router(transactions_router)


@app.get("/health")
def health():
    """Liveness: always 200. Includes db status for debugging."""
    db_ok = check_connection(get_engine())
    status = "ok" if db_ok else "degraded"
    return {
        "status": status,
        "service": "agent_analysis",
        "db": "ok" if db_ok else "unavailable",
    }
