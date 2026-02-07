"""Analyst Agent: Deep analysis of a trade for educational purposes."""

import base64
import json
from typing import Optional

from google import genai
from google.genai import types

from models.schemas import TradePayload, AnalystOutput


ANALYST_SYSTEM_PROMPT = """You are an expert trading analyst for a personalised education platform. Your role is to analyse trades objectively and extract insights that help traders learn—never to judge or promise profits.

## Core principles
- Stay neutral: explain what happened and why, without blame or defensiveness
- Focus on education: highlight patterns, context, and decision points
- Use the trader's own data: contract details, strategy intent, behavioural context
- If chart/image is provided: reference price action, entry/exit ticks, and visual context

## Output format (JSON)
Return ONLY valid JSON in this exact structure:
{
  "trade_analysis": "2-4 paragraph analysis covering: (1) what the trade was, (2) key factors that influenced outcome, (3) how strategy/risk/exit choices played out",
  "key_factors": ["factor1", "factor2", "factor3"],
  "win_loss_assessment": "Brief assessment: was this a win or loss, and what was the main driver?"
}

## Behavioural context
If behavioral_summary is present, use it to add context (e.g. "3rd trade in run, recent outcomes: win, loss, win") but never use it to belittle or predict future results.
"""


def _build_analyst_prompt(payload: TradePayload) -> str:
    parts = [
        "## Trade data (JSON)\n```json\n",
        payload.model_dump_json(indent=2),
        "\n```\n\nAnalyse this trade and return the JSON output.",
    ]
    return "".join(parts)


def _mime_for_image(img_bytes: bytes) -> str:
    """Detect MIME type from image bytes (PNG/JPEG)."""
    if img_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if img_bytes[:2] == b"\xff\xd8" or img_bytes[6:10] in (b"JFIF", b"Exif"):
        return "image/jpeg"
    return "image/png"


def run_analyst(
    payload: TradePayload,
    chart_image_b64: Optional[str] = None,
    api_key: Optional[str] = None,
) -> AnalystOutput:
    """Run Analyst Agent on trade payload and optional chart screenshot."""
    client = genai.Client(api_key=api_key) if api_key else genai.Client()
    user_content = _build_analyst_prompt(payload)

    if chart_image_b64:
        img_data = base64.b64decode(chart_image_b64)
        mime = _mime_for_image(img_data)
        contents = [user_content, types.Part.from_bytes(data=img_data, mime_type=mime)]
    else:
        contents = [user_content]

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=ANALYST_SYSTEM_PROMPT),
    )
    text = response.text.strip()

    # Extract JSON (handle markdown code blocks)
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    data = json.loads(text)
    return AnalystOutput(**data)
