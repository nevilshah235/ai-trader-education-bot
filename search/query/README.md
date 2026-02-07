# search/query — RAG Query Pipeline

Retrieval + generation pipeline that answers trading knowledge questions
using the pre-built FAISS index and a configured LLM.

---

## Pipeline Steps

```
  { question,           ┌──────────────────┐    { RagAnswer JSON }
    trade_analysis, ──▶  │  1. Retrieve     │ ─▶  { difficulty,
    prompt_overrides }   │  2. Build prompt │      answer,
                         │  3. LLM generate │      confidence,
                         │  4. Parse output │      sources }
                         └──────────────────┘
```

| Step | What happens |
|------|-------------|
| **1. Retrieve** | Loads FAISS index, runs similarity search (`top_k` chunks). |
| **2. Build prompt** | Assembles system prompt from `prompt.json` sections (filterable by difficulty, sections, etc.). |
| **3. Generate** | Calls the configured LLM with retrieved context + question + trade analysis. |
| **4. Parse** | Validates LLM output against `RagAnswer` Pydantic schema. |

---

## Usage

### Run test queries from CLI

```bash
# From the project root
python -m search.query
```

This runs three built-in test cases (beginner, trade-anchored, out-of-scope)
and prints the structured JSON results.

### Call from Python

```python
from search.query.pipeline import answer_question

# Basic query
result = answer_question("What is RSI?")

# With trade context
result = answer_question(
    question="How do Bollinger Bands help identify entries?",
    trade_analysis="Gold spot at $4,860. RSI = 48. Bollinger Bands expanding.",
)

# With prompt overrides
result = answer_question(
    question="What is a stop-loss?",
    difficulty="beginner",                       # filter depth + examples
    sections=["role", "rules", "output_schema"], # minimal prompt
    include_examples=False,                      # skip few-shots
    extra_rules=["Keep answer under 2 sentences."],
)
```

### Via FastAPI (see `search/api.py`)

```bash
# Step 1: Submit query → get stream URL
curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is RSI?"}'
# → {"job_id": "abc123", "stream_url": "http://localhost:8000/stream/abc123"}

# Step 2: Open the stream URL (GET — works with EventSource)
curl -N http://localhost:8000/stream/abc123
# → data: {"difficulty": "beginner", "answer": "The RSI is...
# → data: [DONE]

# Sync (no streaming, for testing)
curl -s -X POST http://localhost:8000/query/sync \
  -H "Content-Type: application/json" \
  -d '{"question": "What is RSI?"}'

# With prompt overrides
curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is RSI?",
    "prompt_overrides": {"difficulty": "beginner", "include_examples": false}
  }'
```

---

## Configuration

| Variable    | Default                    | Description |
|-------------|----------------------------|-------------|
| `INDEX_DIR` | `search_index`             | FAISS index location |
| `LLM_MODEL` | `meta/llama-3.3-70b-instruct` | LLM for generation |
| `TOP_K`     | `10`                       | Chunks retrieved per query |
| `BINDING`   | `nvidia`                   | API provider |
| `BINDING_HOST` | `https://integrate.api.nvidia.com/v1` | Provider base URL |

---

## Prompt Override Parameters

These can be passed via `answer_question()` kwargs or the API `prompt_overrides` field:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `difficulty` | `str \| None` | `None` | Filter response-depth and examples to this level |
| `sections` | `list[str] \| None` | `None` (all) | Which prompt sections to include |
| `include_examples` | `bool` | `True` | Attach few-shot examples |
| `extra_rules` | `list[str] \| None` | `None` | Inject additional rules |
| `extra_instructions` | `str \| None` | `None` | Free-form text appended to prompt |

---

## Response Schema

```json
{
  "difficulty": "beginner | intermediate | advanced | unknown",
  "answer": "Knowledge-grounded answer or INSUFFICIENT_CONTEXT",
  "confidence": "high | medium | low",
  "sources": ["https://...", "filename.html"]
}
```

---

## Key Functions

| Function | Description |
|----------|-------------|
| `answer_question(question, trade_analysis, **overrides)` | Sync RAG query -> `RagAnswer` dict |
| `answer_question_stream(question, trade_analysis, **overrides)` | Async generator yielding SSE tokens |
| `run()` | CLI test runner with sample queries |
