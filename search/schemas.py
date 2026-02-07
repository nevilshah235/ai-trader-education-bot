"""Pydantic models shared across ingestion, query, and API layers."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ── API request / response ───────────────────────────────────────────


class PromptOverrides(BaseModel):
    """Optional knobs an upstream agent can set to control prompt assembly.

    Every field maps to a ``build_system_prompt()`` parameter so that the
    calling agent (or a middleware) can tailor the prompt at request time.
    """

    difficulty: str | None = Field(
        default=None,
        description=(
            "If known ahead of time, only include response-depth row and "
            "few-shot examples for this level (beginner / intermediate / advanced)."
        ),
    )
    sections: list[str] | None = Field(
        default=None,
        description=(
            "Which prompt sections to include. "
            "None = all.  Example: ['role', 'rules', 'output_schema']."
        ),
    )
    include_examples: bool = Field(
        default=True,
        description="Whether to attach few-shot examples to the prompt.",
    )
    extra_rules: list[str] | None = Field(
        default=None,
        description="Additional rules injected after the base rules list.",
    )
    extra_instructions: str | None = Field(
        default=None,
        description="Free-form text appended at the end of the prompt.",
    )


class QueryRequest(BaseModel):
    """Incoming query from the upstream agent."""

    question: str = Field(..., description="Knowledge question to answer")
    trade_analysis: str = Field(
        default="none",
        description=(
            "Upstream agent's trade context: pre-trade chart analysis "
            "or post-trade review.  Pass 'none' if not applicable."
        ),
    )
    prompt_overrides: PromptOverrides | None = Field(
        default=None,
        description=(
            "Optional prompt-assembly overrides.  Omit entirely to use "
            "the default full prompt."
        ),
    )


class RagAnswer(BaseModel):
    """Structured answer returned by the RAG pipeline."""

    difficulty: Literal["beginner", "intermediate", "advanced", "unknown"] = Field(
        description="Difficulty level inferred from the question"
    )
    answer: str = Field(
        description="Knowledge-grounded answer or 'INSUFFICIENT_CONTEXT'"
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description="Confidence based on context coverage"
    )
    sources: list[str] = Field(
        default_factory=list,
        description="Source URLs (or filenames when URL unavailable)",
    )


class QuerySubmitResponse(BaseModel):
    """Returned by POST /query — contains the stream URL for the client."""

    job_id: str = Field(description="Unique job identifier")
    stream_url: str = Field(description="GET this URL to receive the SSE stream")


# ── Ingestion metadata (will move to DB later) ──────────────────────


class DocumentMeta(BaseModel):
    """Metadata for a single ingested document."""

    filename: str
    source_url: str = ""
    source_category: str = ""
    char_count: int = 0
    chunk_count: int = 0
