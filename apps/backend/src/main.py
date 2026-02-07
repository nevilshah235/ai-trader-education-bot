"""FastAPI app for Agent Analysis: JSON + chart → Analyst → Tutor → Explanations."""

from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (parents[3]: src -> backend -> apps -> root)
_root = Path(__file__).resolve().parents[3]
load_dotenv(_root / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import init_db
from routes import analysis_router, transactions_router

# Create DB tables on startup (SQLite or Postgres per DATABASE_URL)
init_db()

app = FastAPI(
    title="Agent Analysis API",
    description="Analyst + Tutor agents for personalised trade education",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis_router)
app.include_router(transactions_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "agent_analysis"}
