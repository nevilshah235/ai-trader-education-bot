"""Database engine and session factory. Supports SQLite (local) and PostgreSQL (GCloud)."""

import logging
import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from db.models import Base

log = logging.getLogger("agent_analysis.db")


def _mask_url(url: str) -> str:
    """Mask password in DATABASE_URL for safe logging."""
    if "@" in url and "://" in url:
        # postgresql://user:secret@host/db -> postgresql://user:***@host/db
        scheme, rest = url.split("://", 1)
        if "@" in rest:
            auth, host_part = rest.rsplit("@", 1)
            if ":" in auth:
                user, _ = auth.split(":", 1)
                auth = f"{user}:***"
            return f"{scheme}://{auth}@{host_part}"
    return url


def get_engine():
    """Create engine from DATABASE_URL. Defaults to SQLite in backend data dir."""
    url = os.getenv("DATABASE_URL")
    if not url:
        data_dir = Path(__file__).resolve().parent.parent / "data"
        data_dir.mkdir(exist_ok=True)
        url = f"sqlite:///{data_dir / 'transactions.db'}"
        log.debug("Using default SQLite: %s", url)
    else:
        log.debug("Using DATABASE_URL: %s", _mask_url(url))
    # SQLite needs check_same_thread=False for FastAPI
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    engine = create_engine(url, connect_args=connect_args)
    return engine


def get_session_factory(engine=None):
    """Return a session factory bound to the engine."""
    if engine is None:
        engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _migrate_add_chart_image(engine):
    """Add chart_image_b64 column to transactions if missing (e.g. existing SQLite DBs)."""
    from sqlalchemy import inspect, text

    try:
        insp = inspect(engine)
        if "transactions" not in insp.get_table_names():
            return
        cols = [c["name"] for c in insp.get_columns("transactions")]
        if "chart_image_b64" in cols:
            return
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE transactions ADD COLUMN chart_image_b64 TEXT"))
            conn.commit()
    except Exception:
        pass  # Column may already exist or DB may not support ALTER


def check_connection(engine=None) -> bool:
    """Verify DB is reachable. Returns True if ok, False otherwise. Logs errors."""
    if engine is None:
        engine = get_engine()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        log.debug("Database connection check OK")
        return True
    except Exception as e:
        log.error("Database connection failed: %s", e, exc_info=True)
        return False


def init_db(engine=None):
    """Create all tables if they do not exist; run migrations for existing DBs. Raises on failure."""
    if engine is None:
        engine = get_engine()
    url_display = _mask_url(str(engine.url))
    log.info("Initializing database: %s", url_display)
    if not check_connection(engine):
        raise RuntimeError("Database not available (connection check failed)")
    Base.metadata.create_all(bind=engine)
    _migrate_add_chart_image(engine)
    log.info("Database tables ready")
