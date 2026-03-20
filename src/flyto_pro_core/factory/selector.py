# Copyright 2024 Flyto
# Licensed under the Apache License, Version 2.0
"""
Factory v2 — Deterministic Blueprint Selector

No LLM. Uses BlueprintEngine.search() + heuristic composition.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from .models import RecipeResult

# Connectors that separate intents in a description
_SPLIT_PATTERN = re.compile(
    r'\b(?:and|then|after that|next|finally|,|→|->|=>|；|，|然後|接著|再|並)\b',
    re.IGNORECASE,
)

# Blueprints that produce lists
_LIST_PRODUCERS = {"string_split"}
_LIST_PRODUCER_MODULES = {"string.split", "array.filter", "array.map", "data.csv.read"}

# Blueprints that are iteration wrappers
_ITERATION_BPS = {"foreach_loop"}


def select_blueprints(
    description: str,
    blueprint_engine: Any,
    max_candidates: int = 3,
) -> RecipeResult:
    """
    Select blueprints deterministically using search + heuristics.

    Returns multiple ranked candidates so the pipeline can try each
    until one passes validation.
    """
    phrases = _split_intents(description)
    if not phrases:
        phrases = [description]

    desc_lower = description.lower()
    wants_browser = any(
        kw in desc_lower
        for kw in ("browser", "scrape", "website", "webpage", "click", "login", "screenshot", "網頁", "爬")
    )

    # For each phrase, collect top N candidates (not just top 1)
    phrase_candidates: List[List[str]] = []

    for phrase in phrases:
        phrase = phrase.strip()
        if len(phrase) < 3:
            continue
        results = blueprint_engine.search(phrase)
        candidates = []
        for r in results:
            bp_id = r["id"]
            if bp_id in _ITERATION_BPS:
                continue
            if not wants_browser and _is_browser_blueprint(bp_id, blueprint_engine._blueprints):
                continue
            if _has_dynamic_module(bp_id, blueprint_engine._blueprints):
                continue
            candidates.append(bp_id)
            if len(candidates) >= max_candidates:
                break
        if candidates:
            phrase_candidates.append(candidates)

    if not phrase_candidates:
        # Fallback: search full description
        results = blueprint_engine.search(description)
        for r in results:
            bp_id = r["id"]
            skip = (not wants_browser and _is_browser_blueprint(bp_id, blueprint_engine._blueprints))
            skip = skip or _has_dynamic_module(bp_id, blueprint_engine._blueprints)
            if not skip:
                return RecipeResult(ok=True, blueprints=[bp_id], args={})
        return RecipeResult(ok=False, error="No matching blueprints found")

    # Build the primary selection (top-1 for each phrase)
    selected = []
    seen: Set[str] = set()
    for cands in phrase_candidates:
        for bp_id in cands:
            if bp_id not in seen:
                selected.append(bp_id)
                seen.add(bp_id)
                break

    selected = _dedup_by_module(selected, blueprint_engine._blueprints)
    selected = _order_by_dependency(selected, blueprint_engine._blueprints)
    if any(bp in _LIST_PRODUCERS for bp in selected) and len(selected) > 1:
        selected = _insert_foreach(selected, blueprint_engine._blueprints)

    return RecipeResult(ok=True, blueprints=selected, args={})


def _split_intents(description: str) -> List[str]:
    """Split a description into separate intent phrases."""
    parts = _SPLIT_PATTERN.split(description)
    return [p.strip() for p in parts if p.strip() and len(p.strip()) > 3]


def _order_by_dependency(
    bp_ids: List[str],
    blueprints: Dict[str, dict],
) -> List[str]:
    """Put list-producing blueprints before item-consuming ones."""
    producers = []
    consumers = []

    for bp_id in bp_ids:
        bp = blueprints.get(bp_id, {})
        is_producer = bp_id in _LIST_PRODUCERS
        if not is_producer:
            for step in bp.get("steps", []):
                if step.get("module") in _LIST_PRODUCER_MODULES:
                    is_producer = True
                    break
        if is_producer:
            producers.append(bp_id)
        else:
            consumers.append(bp_id)

    return producers + consumers


_BROWSER_MODULES = {"browser.launch", "browser.goto", "browser.click", "browser.type", "browser.screenshot"}
_BROWSER_ID_PREFIXES = ("browser_", "scrape_")


def _dedup_by_module(
    bp_ids: List[str],
    blueprints: Dict[str, dict],
) -> List[str]:
    """Remove blueprints with overlapping modules.

    If a composite blueprint (e.g. api_fetch_save = http.get + file.write) covers
    a simple one (e.g. http_get = http.get), drop the simple one.
    """
    if len(bp_ids) <= 1:
        return bp_ids

    # Collect modules per blueprint
    bp_modules_map: Dict[str, Set[str]] = {}
    for bp_id in bp_ids:
        bp = blueprints.get(bp_id, {})
        bp_modules_map[bp_id] = {s.get("module", "") for s in bp.get("steps", [])}

    # Remove blueprints whose modules are a subset of another's
    result = []
    for bp_id in bp_ids:
        my_modules = bp_modules_map[bp_id]
        is_subset = False
        for other_id in bp_ids:
            if other_id == bp_id:
                continue
            other_modules = bp_modules_map[other_id]
            if my_modules and my_modules.issubset(other_modules):
                is_subset = True
                break
        if not is_subset:
            result.append(bp_id)

    return result if result else bp_ids[:1]  # Always keep at least one


def _has_dynamic_module(bp_id: str, blueprints: Dict[str, dict]) -> bool:
    """Check if blueprint has a dynamic module ID like {{operation}}."""
    bp = blueprints.get(bp_id, {})
    for step in bp.get("steps", []):
        m = step.get("module", "")
        if "{{" in m:
            return True
    return False


def _is_browser_blueprint(bp_id: str, blueprints: Dict[str, dict]) -> bool:
    """Check if a blueprint requires a browser."""
    if any(bp_id.startswith(p) for p in _BROWSER_ID_PREFIXES):
        return True
    bp = blueprints.get(bp_id, {})
    for step in bp.get("steps", []):
        if step.get("module", "").startswith("browser."):
            return True
    if "browser_init" in bp.get("compose", []):
        return True
    return False


def _insert_foreach(
    bp_ids: List[str],
    blueprints: Dict[str, dict],
) -> List[str]:
    """Insert foreach_loop between list-producer and item-consumer."""
    if "foreach_loop" not in blueprints:
        return bp_ids
    if any(bp in _ITERATION_BPS for bp in bp_ids):
        return bp_ids  # Already has foreach

    result = []
    for i, bp_id in enumerate(bp_ids):
        result.append(bp_id)
        if bp_id in _LIST_PRODUCERS and i + 1 < len(bp_ids):
            result.append("foreach_loop")
    return result
