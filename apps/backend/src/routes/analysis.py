"""FastAPI routes for trade analysis pipeline."""

import os
import base64
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from models.schemas import TradePayload, AnalystOutput, TutorOutput
from agents import run_analyst, run_tutor

router = APIRouter(prefix="/api/agent_analysis", tags=["agent_analysis"])

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


@router.post("/analyse", response_model=AnalysisResponse)
async def analyse_trade(
    payload_json: str = Form(..., description="Trade payload as JSON string"),
    chart_screenshot: UploadFile | None = File(None),
):
    """
    Analyse a trade: JSON + optional chart screenshot → Analyst Agent → Tutor Agent → Explanations.
    """
    try:
        payload = TradePayload.model_validate_json(payload_json)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload JSON: {e}")

    chart_b64: str | None = None
    if chart_screenshot and chart_screenshot.filename:
        content = await chart_screenshot.read()
        chart_b64 = base64.b64encode(content).decode("utf-8")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set in .env")

    analyst_output: AnalystOutput = run_analyst(payload, chart_image_b64=chart_b64, api_key=api_key)
    tutor_output: TutorOutput = run_tutor(analyst_output, payload, api_key=api_key)

    explanation_file = _save_explanation(payload.contract.contract_id, tutor_output)

    return AnalysisResponse(
        trade_explanation=tutor_output.explanation,
        learning_recommendation=analyst_output.win_loss_assessment,
        learning_points=tutor_output.learning_points,
        explanation_file=explanation_file,
    )


@router.post("/analyse/json", response_model=AnalysisResponse)
async def analyse_trade_json_only(payload: TradePayload):
    """Analyse trade from JSON only (no chart). Useful for testing."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set in .env")

    analyst_output = run_analyst(payload, chart_image_b64=None, api_key=api_key)
    tutor_output = run_tutor(analyst_output, payload, api_key=api_key)

    explanation_file = _save_explanation(payload.contract.contract_id, tutor_output)

    return AnalysisResponse(
        trade_explanation=tutor_output.explanation,
        learning_recommendation=analyst_output.win_loss_assessment,
        learning_points=tutor_output.learning_points,
        explanation_file=explanation_file,
    )
