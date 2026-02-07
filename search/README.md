# search/ — Trading Knowledge RAG Service

A portable, self-contained RAG (Retrieval-Augmented Generation) package that
powers the trading knowledge assistant.  Drop this folder into any project and
point it at your data.

---

## Architecture

```
search/
├── __init__.py              # Package marker
├── __main__.py              # python -m search → starts API server
├── config.py                # pydantic-settings — loads .env automatically
├── schemas.py               # Shared Pydantic models (request / response / metadata)
├── prompt.json              # Prompt sections (structured JSON — single source of truth)
├── prompt.py                # Loads prompt.json + build_system_prompt() builder
├── api.py                   # FastAPI endpoints (/query, /query/stream, /health)
├── requirements.txt         # Python dependencies
├── .env.example             # Template for env vars
├── README.md                # This file
│
├── ingestion/               # ← Document ingestion subpackage
│   ├── __init__.py
│   ├── __main__.py          # python -m search.ingestion
│   ├── pipeline.py          # HTML → markdown → chunks → FAISS
│   └── README.md            # Ingestion-specific docs
│
└── query/                   # ← Query / retrieval subpackage
    ├── __init__.py
    ├── __main__.py           # python -m search.query (test runner)
    ├── pipeline.py           # Retrieve → LLM → parse → RagAnswer
    └── README.md             # Query-specific docs
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r search/requirements.txt
```

### 2. Configure environment

```bash
cp search/.env.example .env
# Edit .env — set API_KEY at minimum
```

### 3. Run ingestion (one-time)

```bash
python -m search.ingestion
```

See [`search/ingestion/README.md`](ingestion/README.md) for details.

### 4. Run test queries (local, no server)

```bash
python -m search.query
```

See [`search/query/README.md`](query/README.md) for details.

### 5. Start the API server

```bash
python -m search
# → http://localhost:8000/docs  (Swagger UI)
```

---

## API Endpoints

| Method | Path               | Description                                      |
|--------|--------------------|--------------------------------------------------|
| GET    | `/health`          | Health check                                     |
| POST   | `/query`           | Submit query → get back `{job_id, stream_url}`   |
| GET    | `/stream/{job_id}` | Open stream URL → receive SSE tokens             |
| POST   | `/query/sync`      | Convenience: full JSON response (no streaming)   |

### Flow

```
  Frontend / Agent                         Search API
  ─────────────────                        ──────────
  POST /query {question, ...}  ──────▶    Creates job, returns instantly
                               ◀──────    {job_id, stream_url}

  GET /stream/{job_id}         ──────▶    Opens SSE connection
                               ◀──────    data: token1
                               ◀──────    data: token2
                               ◀──────    ...
                               ◀──────    data: [DONE]
```

- Each `stream_url` is **single-use** (second GET returns `410 Gone`).
- Jobs expire after **5 minutes** if not consumed.
- The `stream_url` is a plain **GET** — works with `EventSource`, `curl`, or any HTTP client.

### Request body (`POST /query` and `POST /query/sync`)

```json
{
  "question": "string (required)",
  "trade_analysis": "string (default: 'none')",
  "prompt_overrides": {
    "difficulty": "beginner | intermediate | advanced | null",
    "sections": ["role", "rules", "output_schema"] | null,
    "include_examples": true,
    "extra_rules": ["string"] | null,
    "extra_instructions": "string" | null
  }
}
```

### Response — `POST /query`

```json
{
  "job_id": "3a618b008365",
  "stream_url": "http://localhost:8000/stream/3a618b008365"
}
```

### Response — `GET /stream/{job_id}` (SSE)

```
data: {"difficulty": "beginner", "answer": "The RSI is...
data: ...
data: [DONE]
```

### Response — `POST /query/sync`

```json
{
  "difficulty": "beginner | intermediate | advanced | unknown",
  "answer": "Knowledge-grounded answer or INSUFFICIENT_CONTEXT",
  "confidence": "high | medium | low",
  "sources": ["https://...", "filename.html"]
}
```

### Frontend usage (JavaScript)

```javascript
// Step 1: submit query
const res = await fetch("/query", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ question: "What is RSI?" }),
});
const { stream_url } = await res.json();

// Step 2: open stream
const source = new EventSource(stream_url);
let buffer = "";
source.onmessage = (e) => {
  if (e.data === "[DONE]") { source.close(); return; }
  buffer += e.data;
};
```

---

## Prompt System

The prompt is split into independently addressable JSON fields in
[`prompt.json`](prompt.json):

| Key              | Type         | Purpose |
|------------------|--------------|---------|
| `role`           | `string`     | Base persona |
| `inputs`         | `string`     | Input description table |
| `reasoning`      | `string[]`   | Internal CoT steps |
| `output_schema`  | `string`     | `{format_instructions}` placeholder |
| `response_depth` | `object`     | Per-difficulty length/style config |
| `tone`           | `string[]`   | Trader-psychology guidelines |
| `rules`          | `string[]`   | Grounding and guardrail rules |
| `examples`       | `object[]`   | Few-shot examples keyed by difficulty |

The `build_system_prompt()` function in `prompt.py` assembles selected
fields at runtime.  An upstream agent can pass `prompt_overrides` to control
which sections are included — see [`query/README.md`](query/README.md).

---

## Configuration

| Variable          | Default                               | Description |
|-------------------|---------------------------------------|-------------|
| `BINDING`         | `nvidia`                              | LLM / embedding provider |
| `BINDING_HOST`    | `https://integrate.api.nvidia.com/v1` | Provider API base URL |
| `API_KEY`         | *(required)*                          | Provider API key |
| `EMBEDDING_MODEL` | `baai/bge-m3`                         | Embedding model name |
| `LLM_MODEL`       | `meta/llama-3.3-70b-instruct`         | Generation model name |
| `DATA_DIR`        | `data`                                | HTML files + url_map.json |
| `INDEX_DIR`       | `search_index`                        | FAISS index persistence |
| `CHUNK_SIZE`      | `800`                                 | Max chars per chunk |
| `CHUNK_OVERLAP`   | `120`                                 | Overlap between chunks |
| `TOP_K`           | `10`                                  | Chunks retrieved per query |

---

## Portability

The `search/` folder is designed to be moved anywhere:

1. All paths resolve from **CWD** or via env vars — no hardcoded paths.
2. `prompt.json` is resolved relative to the module file (`__file__`).
3. The `.env` loader walks upwards from CWD to find the nearest `.env`.
4. Set `DATA_DIR` and `INDEX_DIR` to absolute paths if needed.

---

## Storage Roadmap

| Component  | Current (v1)        | Planned            |
|------------|---------------------|--------------------|
| Documents  | Filesystem (HTML)   | PostgreSQL / MySQL |
| Chunks     | In FAISS pickle     | PostgreSQL / MySQL |
| Embeddings | FAISS (local files) | Milvus / Qdrant    |
| URL map    | `url_map.json`      | Database table     |
| Metadata   | `documents.json`    | Database table     |
