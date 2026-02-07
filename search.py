"""
This script is a starting point for a Retrieval-Augmented Generation (RAG) app.

## Goals
- Ingest a small document set
- Create embeddings + vector index
- Build a retriever + answer generation pipeline
- Evaluate with simple checks

## Environment setup (recommended)
Create a local virtual env, install dependencies, and register a Jupyter kernel:

```bash
uv venv .venv
source .venv/bin/activate
uv python -m pip install --upgrade pip
uv pip install jupyter ipykernel \
  langchain langchain-community langchain-openai langchain-google-genai \
  langchain-nvidia-ai-endpoints \
  faiss-cpu sentence-transformers python-dotenv requests certifi
uv run python -m ipykernel install --user --name .venv --display-name ".venv"
```

"""


from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

from dotenv import dotenv_values, load_dotenv

PROJECT_ROOT = Path.cwd()
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# Load environment variables from .env (if present)
env_path = PROJECT_ROOT / ".env"
load_dotenv(env_path, override=True)


@dataclass
class RagConfig:
    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k: int = 4

config = RagConfig()


# Create dummy data (multiple files) if data folder is empty

sample_docs = {
    "overview.md": """
# RAG Overview

Retrieval-Augmented Generation (RAG) combines a retriever and a generator.
It retrieves relevant chunks and uses them as context for answers.
""".strip(),
    "architecture.txt": """
System Architecture

- Ingestion: load files from data folder
- Chunking: split documents into overlapping chunks
- Index: store embeddings in a vector store
- Retrieval: find top-k relevant chunks
""".strip(),
    "usage.md": """
Usage Notes

Place .txt or .md files under the data directory.
Then run the notebook cells to build the index and query it.
""".strip(),
}

if not any(DATA_DIR.rglob("*.txt")) and not any(DATA_DIR.rglob("*.md")):
    for filename, content in sample_docs.items():
        (DATA_DIR / filename).write_text(content, encoding="utf-8")
    print(f"Wrote {len(sample_docs)} dummy files to {DATA_DIR}")
else:
    print("Data folder already has documents; skipping dummy data creation.")



from langchain_community.document_loaders import DirectoryLoader, TextLoader

def load_documents(folder: Path) -> List:
    """
    Load .txt and .md documents as LangChain Documents.
    """
    loader = DirectoryLoader(
        str(folder),
        glob="**/*.*",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        silent_errors=True,
    )
    docs = loader.load()
    # Keep only .txt/.md
    return [doc for doc in docs if doc.metadata.get("source", "").lower().endswith((".txt", ".md"))]

raw_docs = load_documents(DATA_DIR)
print(f"Loaded {len(raw_docs)} documents")


# https://reference.langchain.com/python/langchain_text_splitters/

from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=config.chunk_size,
    chunk_overlap=config.chunk_overlap,
)

chunks = splitter.split_documents(raw_docs)
print(f"Built {len(chunks)} chunks")


# Embedding
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from langchain_community.vectorstores import FAISS

import os

embeddings = NVIDIAEmbeddings(
    model="baai/bge-m3",
    api_key=os.getenv("EMBEDDING_BINDING_API_KEY"),
    base_url="https://integrate.api.nvidia.com/v1",
)

print("Storing embeddings")

vectorstore = FAISS.from_documents(
    documents=chunks,
    embedding=embeddings
)
print("Vector store ready" if vectorstore else "No chunks to index")



from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

if PROVIDER == "google":
    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
else:
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

retriever = vectorstore.as_retriever(search_kwargs={"k": config.top_k}) if vectorstore else None

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful assistant. Use the context to answer. "
            "If the answer is not in the context, say you don't know.",
        ),
        ("human", "Question: {question}\n\nContext:\n{context}"),
    ]
)


def format_docs(docs: List) -> str:
    return "\n\n".join(
        f"[Source: {doc.metadata.get('source', 'unknown')}]\n{doc.page_content}"
        for doc in docs
    )


def answer_question(question: str) -> str:
    if retriever is None:
        return "No documents indexed. Add files under ./data first."

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain.invoke(question)
