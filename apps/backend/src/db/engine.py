"""Database engine and session factory. Supports SQLite (local) and PostgreSQL (GCloud)."""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base


def get_engine():
    """Create engine from DATABASE_URL. Defaults to SQLite in backend data dir."""
    url = os.getenv("DATABASE_URL")
    if not url:
        data_dir = Path(__file__).resolve().parent.parent / "data"
        data_dir.mkdir(exist_ok=True)
        url = f"sqlite:///{data_dir / 'transactions.db'}"
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


def init_db(engine=None):
    """Create all tables if they do not exist."""
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(bind=engine)
