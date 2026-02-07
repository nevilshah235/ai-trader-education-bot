"""Prompt loader and builder for the RAG knowledge assistant.

``PROMPT_SECTIONS`` is loaded from ``prompt.json`` (co-located with this
module).  The builder function (``build_system_prompt``) selectively joins
fields at runtime so that an upstream agent or middleware can:

    - Include / exclude entire sections  (``sections=["role", "rules", "output_schema"]``)
    - Filter response-depth & examples by difficulty  (``difficulty="beginner"``)
    - Inject extra rules on the fly  (``extra_rules=["Respond in Spanish"]``)
    - Toggle few-shot examples  (``include_examples=False``)

The assembled string is a plain LangChain system-message template that
expects ``{format_instructions}`` to be ``.partial()``-ed in later.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

# ─────────────────────────────────────────────────────────────────────
# Load prompt sections from the JSON file next to this module
# ─────────────────────────────────────────────────────────────────────

_PROMPT_JSON = Path(__file__).with_name("prompt.json")

def _load_sections() -> dict:
    return json.loads(_PROMPT_JSON.read_text(encoding="utf-8"))

PROMPT_SECTIONS: dict = _load_sections()


def reload_sections() -> None:
    """Hot-reload ``PROMPT_SECTIONS`` from disk (useful during development)."""
    global PROMPT_SECTIONS
    PROMPT_SECTIONS = _load_sections()


# ─────────────────────────────────────────────────────────────────────
# Builder — assembles final system-prompt string from selected fields
# ─────────────────────────────────────────────────────────────────────


def build_system_prompt(
    *,
    sections: Optional[List[str]] = None,
    difficulty: Optional[str] = None,
    include_examples: bool = True,
    extra_rules: Optional[List[str]] = None,
    extra_instructions: Optional[str] = None,
) -> str:
    """Compose the system prompt from ``PROMPT_SECTIONS``.

    Parameters
    ----------
    sections:
        Which top-level keys to include.  ``None`` (default) -> all.
        Example: ``["role", "rules", "output_schema"]`` for a minimal prompt.
    difficulty:
        If set, only include the matching response-depth row and filter
        few-shot examples to that difficulty level.  ``None`` -> include all.
    include_examples:
        Whether to append few-shot examples.  Default ``True``.
    extra_rules:
        Additional rules injected after the base rules list.
    extra_instructions:
        Free-form text appended at the very end of the prompt.

    Returns
    -------
    str
        Assembled system-prompt template (still contains ``{format_instructions}``
        placeholder for LangChain ``.partial()``).
    """
    s = PROMPT_SECTIONS
    _all = sections is None

    parts: list[str] = []

    # 1. Role
    if _all or "role" in sections:
        parts.append(s["role"])

    # 2. Inputs
    if _all or "inputs" in sections:
        parts.append(s["inputs"])

    # 3. Reasoning
    if _all or "reasoning" in sections:
        steps = "\n".join(s["reasoning"])
        parts.append(
            "## Internal reasoning (do NOT output — perform silently before answering)\n"
            + steps
        )

    # 4. Output schema
    if _all or "output_schema" in sections:
        parts.append(s["output_schema"])

    # 5. Response depth
    if _all or "response_depth" in sections:
        depth = s["response_depth"]
        header = (
            "## Response-depth guidelines\n\n"
            "| Difficulty | Target length | Style |\n"
            "|------------|---------------|-------|\n"
        )
        if difficulty and difficulty in depth:
            d = depth[difficulty]
            rows = f"| {difficulty} | {d['target_length']} | {d['style']} |"
        else:
            rows = "\n".join(
                f"| {k} | {v['target_length']} | {v['style']} |"
                for k, v in depth.items()
            )
        parts.append(header + rows)

    # 6. Tone
    if _all or "tone" in sections:
        bullets = "\n".join(f"- {t}" for t in s["tone"])
        parts.append(
            "## Tone & style (be a coach, not a textbook)\n" + bullets
        )

    # 6b. Engagement rules
    if _all or "engagement" in sections:
        eng = s.get("engagement", [])
        if eng:
            bullets = "\n".join(f"- {e}" for e in eng)
            parts.append(
                "## Engagement & curriculum rules (make learning stick)\n" + bullets
            )

    # 7. Rules
    if _all or "rules" in sections:
        rules = list(s["rules"])
        if extra_rules:
            rules.extend(extra_rules)
        numbered = "\n".join(f"{i}. {r}" for i, r in enumerate(rules, 1))
        parts.append("## Rules\n" + numbered)

    # 8. Examples
    #    JSON braces in expected_output must be escaped ({{ }}) so
    #    LangChain doesn't treat them as template variables.
    if include_examples and (_all or "examples" in sections):
        examples = s["examples"]
        if difficulty:
            examples = [e for e in examples if e["difficulty"] == difficulty]
        if examples:
            ex_parts = ["## Few-shot examples"]
            for ex in examples:
                ex_parts.append(f"\n### Example — {ex['label']}")
                ex_parts.append(f"TRADE_ANALYSIS: {ex['trade_analysis']}")
                ex_parts.append(f"QUESTION: {ex['question']}")
                ex_parts.append(f"CONTEXT:\n{ex['context']}")
                raw_json = json.dumps(ex["expected_output"], ensure_ascii=False)
                ex_parts.append(raw_json.replace("{", "{{").replace("}", "}}"))
            parts.append("\n".join(ex_parts))

    # 9. Extra free-form instructions
    if extra_instructions:
        parts.append(extra_instructions)

    return "\n\n".join(parts)


# ─────────────────────────────────────────────────────────────────────
# Convenience: default full prompt (backward compatible)
# ─────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = build_system_prompt()
