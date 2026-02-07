"""CRUD for Transaction. Upsert by (user_id, contract_id)."""

from typing import Any

from sqlalchemy.orm import Session

from db.models import Transaction


def upsert_transaction(
    session: Session,
    *,
    user_id: str,
    contract_id: str,
    run_id: str | None = None,
    buy_price: float = 0,
    payout: float = 0,
    profit: float = 0,
    currency: str = "",
    contract_type: str = "",
    shortcode: str = "",
    date_start: str = "",
    date_expiry: str = "",
    entry_tick: str | None = None,
    exit_tick: str | None = None,
    strategy_intent: dict | None = None,
    behavioral_summary: dict | None = None,
    chart_image_b64: str | None = None,
) -> Transaction:
    """Insert or update a transaction. Unique on (user_id, contract_id)."""
    row = session.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.contract_id == contract_id,
    ).first()
    if row:
        row.run_id = run_id or row.run_id
        row.buy_price = buy_price
        row.payout = payout
        row.profit = profit
        row.currency = currency
        row.contract_type = contract_type
        row.shortcode = shortcode
        row.date_start = date_start
        row.date_expiry = date_expiry
        row.entry_tick = entry_tick
        row.exit_tick = exit_tick
        if strategy_intent is not None:
            row.strategy_intent = strategy_intent
        if behavioral_summary is not None:
            row.behavioral_summary = behavioral_summary
        if chart_image_b64 is not None:
            row.chart_image_b64 = chart_image_b64
        return row
    row = Transaction(
        user_id=user_id,
        contract_id=contract_id,
        run_id=run_id,
        buy_price=buy_price,
        payout=payout,
        profit=profit,
        currency=currency,
        contract_type=contract_type,
        shortcode=shortcode,
        date_start=date_start,
        date_expiry=date_expiry,
        entry_tick=entry_tick,
        exit_tick=exit_tick,
        strategy_intent=strategy_intent,
        behavioral_summary=behavioral_summary,
        chart_image_b64=chart_image_b64,
    )
    session.add(row)
    return row


def get_transactions(
    session: Session,
    user_id: str,
    *,
    run_id: str | None = None,
    limit: int = 500,
    since_id: int | None = None,
) -> list[Transaction]:
    """List transactions for a user, optionally by run_id, with limit and cursor."""
    q = session.query(Transaction).filter(Transaction.user_id == user_id)
    if run_id is not None:
        q = q.filter(Transaction.run_id == run_id)
    if since_id is not None:
        q = q.filter(Transaction.id > since_id)
    q = q.order_by(Transaction.id.desc())
    return q.limit(limit).all()


def get_transaction_by_contract(
    session: Session,
    user_id: str,
    contract_id: str,
) -> Transaction | None:
    """Get a single transaction by user_id and contract_id."""
    return session.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.contract_id == contract_id,
    ).first()


def get_chart_image_b64(
    session: Session,
    user_id: str,
    contract_id: str,
) -> str | None:
    """Get stored chart image (base64) for a transaction, for use by analyst."""
    tx = get_transaction_by_contract(session, user_id=user_id, contract_id=contract_id)
    return tx.chart_image_b64 if tx else None
