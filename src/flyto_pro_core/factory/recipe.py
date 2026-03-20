# Copyright 2024 Flyto
# Licensed under the Apache License, Version 2.0
"""
Factory v2 — Phase 1: Recipe Resolution

Asks LLM to pick which blueprints to compose for a given description.
LLM only outputs a JSON array of blueprint IDs + args — everything else is deterministic.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from .models import RecipeResult

logger = logging.getLogger(__name__)

# Compact prompt — LLM ONLY picks blueprint order, does NOT fill args
_SYSTEM_PROMPT = """\
You are a workflow composer. Pick which blueprints to chain together for the user's request.

Rules:
- Pick 1-5 blueprints from the catalog. Order matters (sequential execution).
- Output ONLY the blueprint IDs in order. Do NOT fill arguments — the system handles wiring automatically.
- Output ONLY valid JSON.

Format: {"blueprints": ["id1", "id2", "id3"]}
"""


def _build_catalog_text(summaries: List[dict]) -> str:
    """Build a compact catalog string from blueprint summaries (~3KB for 34 blueprints)."""
    lines = []
    for s in summaries:
        args_str = ""
        if s.get("args"):
            arg_parts = []
            for name, meta in s["args"].items():
                req = "*" if meta.get("required") else ""
                arg_parts.append(f"{name}{req}")
            args_str = f" args=[{', '.join(arg_parts)}]"
        lines.append(f"- {s['id']}: {s.get('description', '')}{args_str}")
    return "\n".join(lines)


def _parse_llm_json(text: str) -> Optional[dict]:
    """Parse LLM output as JSON, stripping markdown fences if present."""
    content = text.strip()
    # Strip markdown code fences
    if content.startswith("```"):
        lines = content.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        content = "\n".join(lines).strip()
    # Try to extract JSON object
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def _fuzzy_match_blueprint(
    candidate: str,
    available_ids: set,
    search_fn,
) -> Optional[str]:
    """Try to fuzzy-match a blueprint ID using search."""
    if candidate in available_ids:
        return candidate
    if search_fn:
        results = search_fn(candidate)
        if results:
            return results[0]["id"]
    return None


async def resolve_recipe(
    description: str,
    blueprint_engine: Any,
    llm: Any = None,
    llm_model: Optional[str] = None,
) -> RecipeResult:
    """
    Phase 1: Ask LLM to select blueprints for a user description.

    Args:
        description: Natural language workflow description.
        blueprint_engine: BlueprintEngine instance with list_blueprints/search.
        llm: ILLMService instance. If None, creates OpenAILLMService.
        llm_model: Optional LLM model override.

    Returns:
        RecipeResult with blueprint IDs and args.
    """
    # Get catalog
    summaries = blueprint_engine.list_blueprints()
    if not summaries:
        return RecipeResult(ok=False, error="No blueprints available")

    catalog_text = _build_catalog_text(summaries)
    available_ids = {s["id"] for s in summaries}

    # Build messages for LLM
    user_message = (
        f"Catalog:\n{catalog_text}\n\n"
        f"User request: {description}"
    )

    # Get or create LLM
    if llm is None:
        try:
            from flyto_pro_core.interfaces.providers.openai_llm import OpenAILLMService
            llm = OpenAILLMService()
        except ImportError:
            return RecipeResult(ok=False, error="No LLM service available. Install: pip install flyto-pro-core[openai]")

    # Call LLM
    try:
        response = await llm.chat(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
            max_tokens=500,
            model=llm_model or "gpt-4o-mini",
        )
        response_text = response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        return RecipeResult(ok=False, error=f"LLM call failed: {e}")

    # Parse response
    parsed = _parse_llm_json(response_text)
    if not parsed:
        return RecipeResult(ok=False, error=f"Failed to parse LLM response: {response_text[:200]}")

    raw_blueprints = parsed.get("blueprints", [])
    raw_args = parsed.get("args", {})

    if not raw_blueprints or not isinstance(raw_blueprints, list):
        return RecipeResult(ok=False, error="LLM returned no blueprints")

    # Validate and fuzzy-match blueprint IDs
    resolved_ids = []
    for bp_id in raw_blueprints:
        if not isinstance(bp_id, str):
            continue
        matched = _fuzzy_match_blueprint(bp_id, available_ids, blueprint_engine.search)
        if matched:
            resolved_ids.append(matched)
        else:
            logger.warning("Blueprint '%s' not found, skipping", bp_id)

    if not resolved_ids:
        return RecipeResult(
            ok=False,
            error=f"None of the suggested blueprints exist: {raw_blueprints}",
        )

    # Args are filled deterministically by _sanitize_recipe_args in pipeline.
    # LLM only picks blueprint order.
    return RecipeResult(
        ok=True,
        blueprints=resolved_ids,
        args={},
    )
