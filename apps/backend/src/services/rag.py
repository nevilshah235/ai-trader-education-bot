"""RAG service — wraps search.query.pipeline for Learn from trade."""

from __future__ import annotations

import logging
import re

log = logging.getLogger("agent_analysis.services.rag")

_LEARN_QUESTION = "What are the key learning points for this trade?"


def learn_from_trade(
    trade_analysis: str,
    question: str | None = None,
) -> dict:
    """Run RAG with trade context. Returns dict compatible with AnalysisResponse mapping.

    Raises FileNotFoundError if FAISS index is missing.
    """
    import os

    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

    from search.query.pipeline import answer_question

    q = question or _LEARN_QUESTION
    try:
        result = answer_question(
            question=q,
            trade_analysis=trade_analysis or "none",
        )
    except FileNotFoundError as e:
        log.warning("RAG index missing: %s", e)
        raise
    return result


def _extract_learning_points(answer: str) -> list[str]:
    """Parse answer into bullet/sentence list for learning_points."""
    if not answer or answer == "INSUFFICIENT_CONTEXT":
        return []
    # Split on numbered items, bullets, or newlines
    parts = re.split(r"\n *[-•*]\s+|\n\d+\.\s+", answer.strip())
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) <= 1:
        return [answer.strip()] if answer.strip() else []
    return parts[:5]  # cap at 5 points
