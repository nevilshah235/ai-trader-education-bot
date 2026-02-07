"""FastAPI routes for syncing and querying transactions."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_engine, get_session_factory
from db.crud_transactions import get_transactions, upsert_transaction

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

_engine = None
_SessionLocal = None


def _get_session():
    global _engine, _SessionLocal
    if _engine is None:
        _engine = get_engine()
        _SessionLocal = get_session_factory(_engine)
    return _SessionLocal()


def get_db():
    session = _get_session()
    try:
        yield session
    finally:
        session.close()


class TransactionIn(BaseModel):
    """Single transaction payload (Contract shape + optional loginid and context)."""
    loginid: str | None = None
    user_id: str | None = None  # alias for loginid
    contract_id: str
    run_id: str | None = None
    buy_price: float = 0
    payout: float = 0
    profit: float = 0
    currency: str = ""
    contract_type: str = ""
    shortcode: str = ""
    date_start: str = ""
    date_expiry: str = ""
    entry_tick: str | None = None
    exit_tick: str | None = None
    strategy_intent: dict | None = None
    behavioral_summary: dict | None = None

    class Config:
        extra = "ignore"


class TransactionSyncResponse(BaseModel):
    count: int
    ids: list[int]


@router.post("", response_model=TransactionSyncResponse, status_code=201)
def sync_transactions(
    body: TransactionIn | list[TransactionIn],
    db: Session = Depends(get_db),
):
    """
    Upsert one or more transactions. Uses loginid or user_id; unique per (user_id, contract_id).
    """
    items = body if isinstance(body, list) else [body]
    ids = []
    for t in items:
        user_id = t.loginid or t.user_id
        if not user_id:
            raise HTTPException(status_code=400, detail="loginid or user_id required")
        row = upsert_transaction(
            db,
            user_id=user_id,
            contract_id=t.contract_id,
            run_id=t.run_id,
            buy_price=t.buy_price,
            payout=t.payout,
            profit=t.profit,
            currency=t.currency,
            contract_type=t.contract_type,
            shortcode=t.shortcode,
            date_start=t.date_start,
            date_expiry=t.date_expiry,
            entry_tick=t.entry_tick,
            exit_tick=t.exit_tick,
            strategy_intent=t.strategy_intent,
            behavioral_summary=t.behavioral_summary,
        )
        ids.append(row.id)
    db.commit()
    return TransactionSyncResponse(count=len(ids), ids=ids)


@router.get("")
def list_transactions(
    loginid: str = Query(..., description="User login id"),
    run_id: str | None = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    since: int | None = Query(None, description="Return transactions with id > since"),
    db: Session = Depends(get_db),
):
    """List transactions for a user. For use by agents or UI."""
    rows = get_transactions(db, user_id=loginid, run_id=run_id, limit=limit, since_id=since)
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "contract_id": r.contract_id,
            "run_id": r.run_id,
            "buy_price": r.buy_price,
            "payout": r.payout,
            "profit": r.profit,
            "currency": r.currency,
            "contract_type": r.contract_type,
            "shortcode": r.shortcode,
            "date_start": r.date_start,
            "date_expiry": r.date_expiry,
            "entry_tick": r.entry_tick,
            "exit_tick": r.exit_tick,
            "strategy_intent": r.strategy_intent,
            "behavioral_summary": r.behavioral_summary,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
