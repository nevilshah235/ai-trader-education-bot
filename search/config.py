"""Centralised settings loaded from environment variables / .env file.

The .env file is resolved from the **current working directory** (i.e. the
project root that launches the service), so the ``search/`` package stays
movable.  Override any value via env vars at runtime.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env_file() -> str | None:
    """Walk upwards from CWD looking for a .env file."""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        candidate = parent / ".env"
        if candidate.is_file():
            return str(candidate)
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_find_env_file() or ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── API binding ──────────────────────────────────────────────────
    binding: str = "nvidia"
    binding_host: str = "https://integrate.api.nvidia.com/v1"
    api_key: str = ""

    # ── Embedding model ──────────────────────────────────────────────
    embedding_model: str = "baai/bge-m3"
    embedding_dim: int = 1024

    # ── LLM model ────────────────────────────────────────────────────
    llm_model: str = "meta/llama-3.3-70b-instruct"

    # ── RAG parameters ───────────────────────────────────────────────
    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k: int = 10

    # ── Paths (relative to CWD; absolute paths also accepted) ───────
    data_dir: str = Field(default="data", description="Root folder for HTML sources + url_map.json")
    index_dir: str = Field(default="search_index", description="Folder where FAISS index is persisted")

    # ── Derived helpers (not env vars) ───────────────────────────────
    @property
    def data_path(self) -> Path:
        return Path(self.data_dir).resolve()

    @property
    def index_path(self) -> Path:
        return Path(self.index_dir).resolve()

    @property
    def url_map_path(self) -> Path:
        return self.data_path / "url_map.json"

    @property
    def html_root(self) -> Path:
        return self.data_path / "html"


settings = Settings()
