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
| **2. Convert** | Strips non-content tags (`<nav>`, `<footer>`, `<script>`, etc.) and converts to clean ATX-heading markdown via `markdownify`. Hyperlinks and images are preserved for curriculum references. |
| **3. Chunk** | Two-stage split: first by markdown headers (`#`, `##`, `###`), then by character limit (`chunk_size` / `chunk_overlap` from config). |
| **4. Embed** | Sends chunks to the configured embedding model (default: `baai/bge-m3` on NVIDIA). |
| **5. Persist** | Saves FAISS index (`index.faiss` + `index.pkl`) and a `documents.json` metadata file to the `INDEX_DIR`. |

---

## How to Re-Ingest (Update Content & Rebuild Vector Index)

Use this whenever you add/update/remove HTML files or want to refresh
from your scraped sources.

### Step 1 — Re-scrape content (if sources have new articles)

The scraper lives in the Jupyter notebook (`knowledge_search.ipynb`,
cell 5).  Run that cell to:
- Crawl index pages for each content source
- Download new article HTML into `data/html/<source>/`
- Update `data/url_map.json` with filename → URL mappings

```bash
# Option A: run the notebook cell interactively
jupyter notebook knowledge_search.ipynb
# → run cell 5 (Web Scraper)

# Option B: run just the scraper cell via CLI
jupyter nbconvert --to notebook --execute \
  --ExecutePreprocessor.timeout=300 \
  knowledge_search.ipynb
```

**Content sources currently configured:**

| Source | Seed URLs | Output dir |
|--------|-----------|------------|
| `blog` | `deriv.com/blog`, `/blog-categories/market-news`, `/blog-categories/trading-strategies` | `data/html/blog/` |
| `experts` | `experts.deriv.com/insights` | `data/html/experts/` |
| `guides` | `traders-academy.deriv.com/trading-guides` | `data/html/guides/` |

### Step 2 — (Optional) Add your own HTML files

Drop any `.html` files into `data/html/` (or a subfolder).  If you want
the original URL to appear in responses, add an entry to
`data/url_map.json`:

```json
{
  "my-article.html": {
    "url": "https://example.com/my-article",
    "source": "custom"
  }
}
```

### Step 3 — Run ingestion

This rebuilds everything from scratch — loads all HTML, converts to
markdown, chunks, embeds, and overwrites the FAISS index.

```bash
python -m search.ingestion
```

**What happens under the hood:**
1. Old `search_index/` files (`index.faiss`, `index.pkl`, `documents.json`) are **overwritten**
2. All `data/html/**/*.html` files are processed (new + existing)
3. Embeddings are re-computed for every chunk (API calls to NVIDIA)

### Step 4 — Verify

```bash
# Quick check: run test queries against the new index
python -m search.query
```

Or start the API and test via curl:

```bash
python -m search
# In another terminal:
curl -s -X POST http://localhost:8000/query/sync \
  -H "Content-Type: application/json" \
  -d '{"question": "What is RSI?"}' | python3 -m json.tool
```

### Step 5 — (If API is running) Restart the server

The FAISS index is loaded into memory on first query.  After
re-ingestion, **restart the API** so it picks up the new index:

```bash
# Kill the running server, then restart
python -m search
```

---

## Quick Reference: Common Re-Ingestion Scenarios

| Scenario | What to do |
|----------|-----------|
| **Added new HTML files manually** | Step 2 → Step 3 → Step 5 |
| **Want latest articles from deriv.com** | Step 1 → Step 3 → Step 5 |
| **Changed chunk_size or embedding model** | Step 3 → Step 5 (no re-scrape needed) |
| **Deleted some HTML files** | Remove them from `data/html/`, then Step 3 → Step 5 |
| **Changed .env config (API key, model)** | Step 3 → Step 5 |

---

## Run from CLI

```bash
# From the project root (where .env lives)
python -m search.ingestion
```

## Run as a Python function

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

## Example output

```
INFO | Loading HTML from /path/to/data/html
INFO | Loaded 34 documents
INFO | Built 561 chunks (avg 462 chars)
INFO | Embedding 561 chunks ...
INFO | FAISS index saved to /path/to/search_index (561 vectors)
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
| `html_to_clean_markdown(html)` | Strips non-content tags, converts HTML to markdown (preserves links + images) |
| `load_html_documents(path)` | Loads all HTML files as LangChain `Document` objects |
| `chunk_documents(docs)` | Two-stage header-aware + recursive splitting |
| `build_vectorstore(chunks)` | Creates and persists FAISS index |
| `save_doc_metadata(docs, chunks)` | Writes `documents.json` (future DB migration) |
| `run()` | Full CLI pipeline — calls all of the above |
