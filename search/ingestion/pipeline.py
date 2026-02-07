"""Ingestion pipeline — one-time process to build the search index.

Usage (CLI):
    python -m search.ingestion        # from project root

Steps:
    1. Load HTML files from data/html/ (recursively)
    2. Convert to clean markdown
    3. Two-stage chunking (header-aware + character-limit)
    4. Embed via configured provider
    5. Persist FAISS index + document metadata to disk

Later this will write documents & chunks to PostgreSQL/MySQL and
embeddings to Milvus.  For now everything lands on the filesystem.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import List

from bs4 import BeautifulSoup
from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from markdownify import markdownify as md

from search.config import settings
from search.schemas import DocumentMeta

logger = logging.getLogger(__name__)


# ── HTML → Markdown ──────────────────────────────────────────────────


def html_to_clean_markdown(html: str) -> str:
    """Strip non-content tags and convert HTML to ATX-heading markdown."""
    import warnings
    from bs4 import XMLParsedAsHTMLWarning

    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    # Convert relative image src to absolute where possible.
    # Images with data: URIs or empty src are dropped to avoid noise.
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src or src.startswith("data:"):
            img.decompose()
            continue
        # Keep alt text for context even if image can't render in text
        alt = img.get("alt", "")
        if alt:
            img["alt"] = alt

    # Preserve both hyperlinks and images for downstream curriculum use.
    markdown = md(str(soup), heading_style="ATX")
    return re.sub(r"\n{3,}", "\n\n", markdown).strip()


# ── Document loading ─────────────────────────────────────────────────


def _load_url_map() -> dict:
    if settings.url_map_path.exists():
        return json.loads(settings.url_map_path.read_text(encoding="utf-8"))
    return {}


def load_html_documents(html_root: Path | None = None) -> List[Document]:
    """Recursively load ``*.html`` from *html_root*, convert to markdown Documents."""
    html_root = html_root or settings.html_root
    url_map = _load_url_map()
    docs: List[Document] = []

    for path in sorted(html_root.rglob("*.htm*")):
        raw = path.read_text(encoding="utf-8", errors="ignore")
        text = html_to_clean_markdown(raw)
        if not text:
            continue

        source_url = ""
        entry = url_map.get(path.name)
        if entry:
            source_url = entry.get("url", "")

        docs.append(
            Document(
                page_content=text,
                metadata={
                    "source": str(path),
                    "filename": path.name,
                    "source_url": source_url,
                    "format": "html->markdown",
                },
            )
        )

    return docs


# ── Chunking ─────────────────────────────────────────────────────────


def chunk_documents(docs: List[Document]) -> List[Document]:
    """Two-stage split: markdown-header-aware, then recursive character."""
    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")],
        strip_headers=False,
    )
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    chunks: List[Document] = []
    for doc in docs:
        header_chunks = md_splitter.split_text(doc.page_content)
        for hc in header_chunks:
            hc.metadata = {**doc.metadata, **hc.metadata}
        sub_chunks = char_splitter.split_documents(header_chunks)
        chunks.extend(sub_chunks)

    return chunks


# ── Embedding + FAISS persistence ────────────────────────────────────


def build_vectorstore(chunks: List[Document]):
    """Create FAISS vectorstore from chunks and persist to disk."""
    from langchain_community.vectorstores import FAISS
    from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

    embeddings = NVIDIAEmbeddings(
        model=settings.embedding_model,
        api_key=settings.api_key,
        base_url=settings.binding_host,
    )

    logger.info("Embedding %d chunks ...", len(chunks))
    vectorstore = FAISS.from_documents(chunks, embeddings)

    # Persist
    index_path = settings.index_path
    index_path.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(index_path))
    logger.info("FAISS index saved to %s (%d vectors)", index_path, vectorstore.index.ntotal)

    return vectorstore


# ── Metadata dump (later → DB) ───────────────────────────────────────


def save_doc_metadata(docs: List[Document], chunks: List[Document]) -> Path:
    """Write document-level metadata to JSON (future: PostgreSQL/MySQL)."""
    chunk_counts: dict[str, int] = {}
    for c in chunks:
        fn = c.metadata.get("filename", "")
        chunk_counts[fn] = chunk_counts.get(fn, 0) + 1

    url_map = _load_url_map()
    records = []
    for doc in docs:
        fn = doc.metadata["filename"]
        entry = url_map.get(fn, {})
        records.append(
            DocumentMeta(
                filename=fn,
                source_url=entry.get("url", doc.metadata.get("source_url", "")),
                source_category=entry.get("source", ""),
                char_count=len(doc.page_content),
                chunk_count=chunk_counts.get(fn, 0),
            ).model_dump()
        )

    out = settings.index_path / "documents.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Document metadata saved to %s (%d docs)", out, len(records))
    return out


# ── CLI entrypoint ───────────────────────────────────────────────────


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    logger.info("Loading HTML from %s", settings.html_root)
    docs = load_html_documents()
    logger.info("Loaded %d documents", len(docs))

    chunks = chunk_documents(docs)
    logger.info(
        "Built %d chunks (avg %d chars)",
        len(chunks),
        sum(len(c.page_content) for c in chunks) // max(len(chunks), 1),
    )

    build_vectorstore(chunks)
    save_doc_metadata(docs, chunks)
    logger.info("Ingestion complete.")


if __name__ == "__main__":
    run()
