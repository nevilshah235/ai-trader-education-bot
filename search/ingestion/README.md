# search/ingestion — Document Ingestion Pipeline

One-time (or periodic) process that converts raw HTML content into an
embeddable, searchable vector index.

---

## Pipeline Steps

```
  data/html/**/*.html          ┌─────────────────┐    search_index/
  data/url_map.json   ──────▶  │  1. Load HTML    │ ─▶  index.faiss
                               │  2. HTML → MD    │     index.pkl
                               │  3. Chunk (2-stage)│   documents.json
                               │  4. Embed         │
                               │  5. Save FAISS    │
                               └─────────────────┘
```

| Step | What happens |
|------|-------------|
| **1. Load** | Recursively finds `*.html` files under `data/html/`. Resolves original URLs from `data/url_map.json`. |
| **2. Convert** | Strips non-content tags (`<nav>`, `<footer>`, `<script>`, etc.) and converts to clean ATX-heading markdown via `markdownify`. |
| **3. Chunk** | Two-stage split: first by markdown headers (`#`, `##`, `###`), then by character limit (`chunk_size` / `chunk_overlap` from config). |
| **4. Embed** | Sends chunks to the configured embedding model (default: `baai/bge-m3` on NVIDIA). |
| **5. Persist** | Saves FAISS index (`index.faiss` + `index.pkl`) and a `documents.json` metadata file to the `INDEX_DIR`. |

---

## Usage

### Run from CLI

```bash
# From the project root (where .env lives)
python -m search.ingestion
```

### Run as a Python function

```python
from search.ingestion.pipeline import (
    load_html_documents,
    chunk_documents,
    build_vectorstore,
    save_doc_metadata,
)

docs = load_html_documents()
chunks = chunk_documents(docs)
vs = build_vectorstore(chunks)
save_doc_metadata(docs, chunks)
```

### Output

```
INFO | Loading HTML from /path/to/data/html
INFO | Loaded 34 documents
INFO | Built 555 chunks (avg 457 chars)
INFO | Embedding 555 chunks ...
INFO | FAISS index saved to /path/to/search_index (555 vectors)
INFO | Document metadata saved to /path/to/search_index/documents.json (34 docs)
INFO | Ingestion complete.
```

---

## Configuration

All values are loaded from `.env` (see `search/config.py`):

| Variable          | Default   | Description |
|-------------------|-----------|-------------|
| `DATA_DIR`        | `data`    | Root folder containing `html/` and `url_map.json` |
| `INDEX_DIR`       | `search_index` | Where FAISS index is written |
| `EMBEDDING_MODEL` | `baai/bge-m3` | Embedding model name |
| `CHUNK_SIZE`      | `800`     | Max characters per chunk |
| `CHUNK_OVERLAP`   | `120`     | Overlap between consecutive chunks |

---

## Storage Roadmap

| Component   | Current (v1)        | Planned              |
|-------------|---------------------|----------------------|
| Documents   | Filesystem (HTML)   | PostgreSQL / MySQL   |
| Chunks      | In FAISS pickle     | PostgreSQL / MySQL   |
| Embeddings  | FAISS (local files) | Milvus / Qdrant      |
| Metadata    | `documents.json`    | Database table       |

---

## Key Functions

| Function | Description |
|----------|-------------|
| `html_to_clean_markdown(html)` | Strips tags, converts HTML to markdown |
| `load_html_documents(path)` | Loads all HTML files as LangChain `Document` objects |
| `chunk_documents(docs)` | Two-stage header-aware + recursive splitting |
| `build_vectorstore(chunks)` | Creates and persists FAISS index |
| `save_doc_metadata(docs, chunks)` | Writes `documents.json` (future DB migration) |
| `run()` | Full CLI pipeline — calls all of the above |
