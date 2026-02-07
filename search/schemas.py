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


class DeepDiveLink(BaseModel):
    """A reference link the trader can click to learn more."""

    title: str = Field(description="Short label describing what the link covers")
    url: str = Field(description="Full URL to the source article or resource")


class RagAnswer(BaseModel):
    """Structured, curriculum-style answer returned by the RAG pipeline."""

    difficulty: Literal["beginner", "intermediate", "advanced", "unknown"] = Field(
        description="Difficulty level inferred from the question"
    )
    lesson_title: str = Field(
        description=(
            "A short, catchy title for this lesson (e.g. "
            "'Why Your CALL Won: Reading Momentum Right')"
        )
    )
    answer: str = Field(
        description=(
            "The main educational content — story-driven, anchored to the "
            "trader's own trade, with concrete examples. "
            "Or 'INSUFFICIENT_CONTEXT' if context is lacking."
        )
    )
    key_takeaway: str = Field(
        description=(
            "One memorable sentence the trader should remember from this lesson"
        )
    )
    reflection_question: str = Field(
        description=(
            "An interactive question that makes the trader think, "
            "e.g. 'What would you do if RSI had been above 70 at entry?'"
        )
    )
    deep_dive_links: list[DeepDiveLink] = Field(
        default_factory=list,
        description="Clickable links from CONTEXT for further reading",
    )
    next_topics: list[str] = Field(
        default_factory=list,
        description=(
            "2-3 suggested next topics that build on this lesson, "
            "forming a personalised curriculum path"
        ),
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
