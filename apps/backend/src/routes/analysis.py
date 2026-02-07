"""FastAPI routes for trade analysis pipeline."""

import logging
import os
import base64
import traceback
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_engine, get_session_factory

log = logging.getLogger("agent_analysis.routes.analysis")
from db.crud_analysis import create_analysis_result
from db.crud_transactions import get_chart_image_b64, upsert_transaction
from models.schemas import TradePayload, AnalystOutput, TutorOutput
from agents import run_analyst, run_tutor

router = APIRouter(prefix="/api/agent_analysis", tags=["agent_analysis"])

_SessionLocal = None


def _get_db():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = get_session_factory(get_engine())
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()

EXPLANATIONS_DIR = Path(__file__).resolve().parent.parent / "Explanations"
EXPLANATIONS_DIR.mkdir(exist_ok=True)


class AnalysisResponse(BaseModel):
    version: int = 1
    trade_explanation: str
    learning_recommendation: str
    learning_points: list[str]
    explanation_file: str | None = None


def _save_explanation(contract_id: str, tutor_output: TutorOutput) -> str:
    """Save explanation to Explanations folder. Returns relative path."""
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{contract_id}_{ts}.txt"
    path = EXPLANATIONS_DIR / filename
    content = f"# Trade Explanation\n\n{tutor_output.explanation}\n\n## Learning Points\n"
    for i, pt in enumerate(tutor_output.learning_points, 1):
        content += f"{i}. {pt}\n"
    path.write_text(content, encoding="utf-8")
    return filename


def _persist_payload_and_result(
    db: Session,
    payload: TradePayload,
    analyst_output: AnalystOutput,
    tutor_output: TutorOutput,
    explanation_file: str,
    loginid: str | None,
    chart_image_b64: str | None = None,
):
    """Upsert transaction and create analysis result when loginid is provided."""
    if not loginid:
        return
    c = payload.contract
    tx = upsert_transaction(
        db,
        user_id=loginid,
        contract_id=c.contract_id,
        run_id=payload.behavioral_summary.run_id if payload.behavioral_summary else None,
        buy_price=c.buy_price,
        payout=c.payout,
        profit=c.profit,
        currency=c.currency,
        contract_type=c.contract_type,
        shortcode=c.shortcode,
        date_start=c.date_start,
        date_expiry=c.date_expiry,
        entry_tick=c.entry_tick,
        exit_tick=c.exit_tick,
        strategy_intent=payload.strategy_intent.model_dump() if payload.strategy_intent else None,
        behavioral_summary=payload.behavioral_summary.model_dump() if payload.behavioral_summary else None,
        chart_image_b64=chart_image_b64,
    )
    db.flush()  # ensure tx.id is set for new rows
    create_analysis_result(
        db,
        transaction_id=tx.id,
        trade_analysis=analyst_output.trade_analysis,
        key_factors=analyst_output.key_factors or [],
        win_loss_assessment=analyst_output.win_loss_assessment,
        trade_explanation=tutor_output.explanation,
        learning_points=tutor_output.learning_points or [],
        explanation_file=explanation_file,
    )
    db.commit()


@router.post("/analyse", response_model=AnalysisResponse)
async def analyse_trade(
    payload_json: str = Form(..., description="Trade payload as JSON string"),
    chart_screenshot: UploadFile | None = File(None),
    loginid: str | None = Query(None, description="User login id for persisting to DB"),
    db: Session = Depends(_get_db),
):
    """
    Analyse a trade: JSON + optional chart screenshot → Analyst Agent → Tutor Agent → Explanations.
    When loginid is provided, persists transaction and analysis result to DB.
    """
    try:
        payload = TradePayload.model_validate_json(payload_json)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload JSON: {e}")

    chart_b64: str | None = None
    if chart_screenshot and chart_screenshot.filename:
        content = await chart_screenshot.read()
        chart_b64 = base64.b64encode(content).decode("utf-8")
    if chart_b64 is None and loginid:
        chart_b64 = get_chart_image_b64(db, user_id=loginid, contract_id=payload.contract.contract_id)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        log.error("GEMINI_API_KEY not set")
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY not set. Add it to apps/backend/.env (or repo root .env).",
        )

    log.debug("Running analyst then tutor for contract_id=%s", payload.contract.contract_id)
    try:
        analyst_output: AnalystOutput = run_analyst(payload, chart_image_b64=chart_b64, api_key=api_key)
        tutor_output: TutorOutput = run_tutor(analyst_output, payload, api_key=api_key)
    except Exception as e:
        log.exception("Agent error: %s", e)
        raise HTTPException(status_code=500, detail=f"Agent error: {e!s}") from e

    explanation_file = _save_explanation(payload.contract.contract_id, tutor_output)
    try:
        _persist_payload_and_result(
            db, payload, analyst_output, tutor_output, explanation_file, loginid, chart_image_b64=chart_b64
        )
    except Exception as e:
        log.exception("Failed to persist analysis result: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to persist result: {e!s}") from e

    return AnalysisResponse(
        trade_explanation=tutor_output.explanation,
        learning_recommendation=analyst_output.win_loss_assessment,
        learning_points=tutor_output.learning_points,
        explanation_file=explanation_file,
    )


@router.post("/analyse/json", response_model=AnalysisResponse)
async def analyse_trade_json_only(
    payload: TradePayload,
    loginid: str | None = Query(None, description="User login id for persisting to DB"),
    db: Session = Depends(_get_db),
):
    """Analyse trade from JSON only (no chart). When loginid is provided, persists to DB."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set in .env")

    analyst_output = run_analyst(payload, chart_image_b64=None, api_key=api_key)
    tutor_output = run_tutor(analyst_output, payload, api_key=api_key)

    explanation_file = _save_explanation(payload.contract.contract_id, tutor_output)
    _persist_payload_and_result(db, payload, analyst_output, tutor_output, explanation_file, loginid)

    return AnalysisResponse(
        trade_explanation=tutor_output.explanation,
        learning_recommendation=analyst_output.win_loss_assessment,
        learning_points=tutor_output.learning_points,
        explanation_file=explanation_file,
    )
