"""Tutor Agent: Turn Analyst output into educational explanations."""

import json
from typing import Optional

import google.generativeai as genai

from models.schemas import TradePayload, AnalystOutput, TutorOutput


TUTOR_SYSTEM_PROMPT = """You are an AI trading tutor. Your job is to turn a trade analysis into clear, memorable educational content.

## Principles
- Explain concepts simply: assume varied levels (beginner to intermediate)
- Use the trader's own trade as the teaching example—it's more memorable
- Keep tone encouraging and educational, never preachy or condescending
- No promises of profits; focus on learning and patterns

## Output format (JSON)
Return ONLY valid JSON:
{
  "explanation": "2-3 paragraph explanation suitable for the trader. Use the analysis to teach: what happened, why it matters, what they can learn.",
  "learning_points": ["Point 1", "Point 2", "Point 3"]
}
"""


def _build_tutor_prompt(analyst_output: AnalystOutput, payload: TradePayload) -> str:
    return f"""## Analyst analysis

{analyst_output.trade_analysis}

Key factors: {', '.join(analyst_output.key_factors)}
Win/loss assessment: {analyst_output.win_loss_assessment}

## Trade context
- Contract: {payload.contract.contract_type} ({payload.contract.shortcode})
- P/L: {payload.contract.profit} {payload.contract.currency}
- Entry: {payload.contract.entry_tick or 'N/A'} → Exit: {payload.contract.exit_tick or 'N/A'}

Turn this into an educational explanation for the trader. Return JSON only."""


def run_tutor(
    analyst_output: AnalystOutput,
    payload: TradePayload,
    api_key: Optional[str] = None,
) -> TutorOutput:
    """Run Tutor Agent on Analyst output."""
    if api_key:
        genai.configure(api_key=api_key)

    model = genai.GenerativeModel("gemini-2.0-flash", system_instruction=TUTOR_SYSTEM_PROMPT)
    response = model.generate_content(_build_tutor_prompt(analyst_output, payload))
    text = response.text.strip()

    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    data = json.loads(text)
    return TutorOutput(**data)
