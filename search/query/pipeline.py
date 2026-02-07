"""Query pipeline — load persisted FAISS index, retrieve, generate, parse.

Usage (CLI):
    python -m search.query            # interactive test queries

This module exposes ``answer_question()`` which is called by the FastAPI
endpoint as well as any other caller.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import AsyncIterator, List

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from langchain_openai import ChatOpenAI

from search.config import settings
from search.prompt import build_system_prompt
from search.schemas import RagAnswer

logger = logging.getLogger(__name__)


# ── Singleton loaders ────────────────────────────────────────────────


@lru_cache(maxsize=1)
def _get_embeddings() -> NVIDIAEmbeddings:
    return NVIDIAEmbeddings(
        model=settings.embedding_model,
        api_key=settings.api_key,
        base_url=settings.binding_host,
    )


@lru_cache(maxsize=1)
def _get_vectorstore() -> FAISS:
    idx = settings.index_path
    if not (idx / "index.faiss").exists():
        raise FileNotFoundError(
            f"FAISS index not found at {idx}. "
            "Run ingestion first: python -m search.ingestion"
        )
    return FAISS.load_local(
        str(idx), _get_embeddings(), allow_dangerous_deserialization=True
    )


@lru_cache(maxsize=1)
def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.api_key,
        base_url=settings.binding_host,
        temperature=0,
    )


# ── Parser ───────────────────────────────────────────────────────────

parser = PydanticOutputParser(pydantic_object=RagAnswer)


# ── Prompt builder ───────────────────────────────────────────────────


def _build_prompt(
    *,
    sections: list[str] | None = None,
    difficulty: str | None = None,
    include_examples: bool = True,
    extra_rules: list[str] | None = None,
    extra_instructions: str | None = None,
) -> ChatPromptTemplate:
    """Build a ChatPromptTemplate using selected prompt sections.

    All parameters are forwarded to ``build_system_prompt()``.
    The returned template already has ``{format_instructions}`` filled in.
    """
    system_text = build_system_prompt(
        sections=sections,
        difficulty=difficulty,
        include_examples=include_examples,
        extra_rules=extra_rules,
        extra_instructions=extra_instructions,
    )
    return ChatPromptTemplate.from_messages(
        [
            ("system", system_text),
            (
                "human",
                "TRADE_ANALYSIS:\n{trade_analysis}\n\n"
                "QUESTION:\n{question}\n\n"
                "CONTEXT:\n{context}",
            ),
        ]
    ).partial(format_instructions=parser.get_format_instructions())


# ── Helpers ──────────────────────────────────────────────────────────


def _format_docs(docs: List[Document]) -> str:
    """Build a labelled context string with URLs the LLM can cite.

    Each chunk is tagged with its source URL (preferred) or filename,
    plus any header metadata, so the LLM can produce ``deep_dive_links``
    and ``sources`` from real references.
    """
    parts: list[str] = []
    seen: set[str] = set()  # deduplicate exact-same chunk text
    for doc in docs:
        sig = doc.page_content[:200]
        if sig in seen:
            continue
        seen.add(sig)

        url = doc.metadata.get("source_url", "")
        filename = doc.metadata.get("filename", "unknown")
        label = url or filename

        # Include header trail if present (gives section context)
        headers = " > ".join(
            v for k, v in sorted(doc.metadata.items()) if k.startswith("h")
        )
        header_line = f"  Section: {headers}\n" if headers else ""

        parts.append(f"[{label}]\n{header_line}{doc.page_content}")
    return "\n\n".join(parts)


def _default_answer() -> dict:
    return RagAnswer(
        difficulty="unknown",
        answer="INSUFFICIENT_CONTEXT",
        confidence="low",
        sources=[],
    ).model_dump()


# ── Public API ───────────────────────────────────────────────────────


def answer_question(
    question: str,
    trade_analysis: str = "none",
    *,
    difficulty: str | None = None,
    sections: list[str] | None = None,
    include_examples: bool = True,
    extra_rules: list[str] | None = None,
    extra_instructions: str | None = None,
) -> dict:
    """Synchronous RAG query -> parsed ``RagAnswer`` dict.

    Parameters
    ----------
    question : str
        Knowledge question.
    trade_analysis : str
        Upstream trade context or ``"none"``.
    difficulty : str | None
        If known ahead of time, filters response-depth & examples.
    sections : list[str] | None
        Restrict which prompt sections are included.
    include_examples : bool
        Whether to attach few-shot examples.
    extra_rules : list[str] | None
        Additional rules injected at runtime.
    extra_instructions : str | None
        Free-form text appended to the prompt.
    """
    try:
        vs = _get_vectorstore()
    except FileNotFoundError:
        logger.warning("No FAISS index; returning default answer.")
        return _default_answer()

    retriever = vs.as_retriever(search_kwargs={"k": settings.top_k})
    docs = retriever.invoke(question)

    if not docs:
        return _default_answer()

    context_str = _format_docs(docs)

    prompt = _build_prompt(
        sections=sections,
        difficulty=difficulty,
        include_examples=include_examples,
        extra_rules=extra_rules,
        extra_instructions=extra_instructions,
    )

    chain = prompt | _get_llm() | parser
    result: RagAnswer = chain.invoke(
        {
            "question": question,
            "trade_analysis": trade_analysis,
            "context": context_str,
        }
    )
    return result.model_dump()


async def answer_question_stream(
    question: str,
    trade_analysis: str = "none",
    *,
    difficulty: str | None = None,
    sections: list[str] | None = None,
    include_examples: bool = True,
    extra_rules: list[str] | None = None,
    extra_instructions: str | None = None,
) -> AsyncIterator[str]:
    """Streaming variant — yields partial JSON tokens via SSE.

    Accepts the same prompt-override kwargs as ``answer_question()``.
    The final concatenated output is a valid ``RagAnswer`` JSON string.
    """
    try:
        vs = _get_vectorstore()
    except FileNotFoundError:
        yield json.dumps(_default_answer())
        return

    retriever = vs.as_retriever(search_kwargs={"k": settings.top_k})
    docs = retriever.invoke(question)

    if not docs:
        yield json.dumps(_default_answer())
        return

    prompt = _build_prompt(
        sections=sections,
        difficulty=difficulty,
        include_examples=include_examples,
        extra_rules=extra_rules,
        extra_instructions=extra_instructions,
    )

    chain = prompt | _get_llm()  # no parser — stream raw tokens
    async for chunk in chain.astream(
        {
            "question": question,
            "trade_analysis": trade_analysis,
            "context": _format_docs(docs),
        }
    ):
        yield chunk.content


# ── CLI test runner ──────────────────────────────────────────────────


def run() -> None:
    """Run a few test queries from the command line."""
    import os

    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    test_cases = [
        {
            "question": "What are CALL options and when should they be used?",
            "trade_analysis": (
                "CALL option trade on Volatility 75 Index: $10 investment, "
                "$19.50 payout. Entry tick 250.50, closed at 251.00 within "
                "5-minute timeframe."
            ),
        },
        {
            "question": "What is RSI and how do I use it?",
            "trade_analysis": "none",
        },
        {
            "question": "What is the best crypto exchange?",
            "trade_analysis": "none",
        },
    ]

    for i, tc in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"TEST {i}: {tc['question']}")
        print(f"{'='*60}")
        result = answer_question(**tc)
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run()
