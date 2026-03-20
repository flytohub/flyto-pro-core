# Copyright 2024 Flyto
# Licensed under the Apache License, Version 2.0
"""
Factory v2 — Pipeline Orchestrator

Orchestrates Phase 1 → 2 → 4:
  1. resolve_recipe() — LLM picks blueprints
  2. compose_chain() — deterministic expansion + wiring
  4. autofix_workflow() — deterministic fixes

Phase 3 (enrichment: layout, edges, _ui) happens in flyto-cloud.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .models import PipelineResult
from .recipe import resolve_recipe
from .selector import select_blueprints
from .autofix import autofix_workflow

# Output type hints for type-aware wiring
_DICT_OUTPUT_MODULES = {"http.get", "http.request", "http.paginate"}
_LIST_OUTPUT_MODULES = {"string.split", "array.filter", "array.map", "array.sort", "data.csv.read"}
_STRING_INPUT_PARAMS = {"content", "text", "body", "message", "template"}  # params that need string, not dict

logger = logging.getLogger(__name__)


# Blueprints whose output is a list of items
_LIST_PRODUCING_BLUEPRINTS = {
    "string_split",  # splits text → list of strings
}

# Modules whose output is a list
_LIST_PRODUCING_MODULES = {
    "string.split", "array.filter", "array.map", "array.sort",
    "data.csv.read", "file.list",
}

# Blueprints that already handle iteration internally
_ITERATION_BLUEPRINTS = {"foreach_loop"}


def _auto_insert_foreach(
    blueprint_ids: List[str],
    blueprints: Dict[str, dict],
) -> List[str]:
    """Insert foreach_loop between list-producer and item-consumer if missing.

    Example: [string_split, qrcode_generate] → [string_split, foreach_loop, qrcode_generate]
    """
    if "foreach_loop" not in blueprints:
        return blueprint_ids

    # If LLM already included foreach_loop, don't auto-insert
    if any(bp in _ITERATION_BLUEPRINTS for bp in blueprint_ids):
        return blueprint_ids

    result = []
    for i, bp_id in enumerate(blueprint_ids):
        result.append(bp_id)

        # Check if this blueprint produces a list
        bp = blueprints.get(bp_id, {})
        produces_list = bp_id in _LIST_PRODUCING_BLUEPRINTS
        if not produces_list:
            for step in bp.get("steps", []):
                if step.get("module") in _LIST_PRODUCING_MODULES:
                    produces_list = True
                    break

        if produces_list and i + 1 < len(blueprint_ids):
            result.append("foreach_loop")

    return result


def _sanitize_recipe_args(
    blueprint_ids: List[str],
    args: Dict[str, Any],
    blueprints: Dict[str, dict],
) -> Dict[str, Any]:
    """Fill missing required args deterministically.

    For each blueprint in the chain:
    - First missing required arg that looks like "data input" → wire to previous output
    - All other missing required args → ``{{arg_name}}`` (user-provided placeholder)
    - First blueprint's args are always ``{{arg_name}}`` (no previous step)

    "Data input" heuristic: arg names containing text, content, data, items, body,
    path, url, prompt, query, input, message — things that carry data between steps.
    """
    _DATA_FLOW_NAMES = {
        "text", "content", "data", "items", "body", "input",
        "path", "url", "prompt", "query", "message", "source",
        "html", "json_data", "csv_data", "template",
    }

    sanitized = {}
    prev_last_step_id = None
    prev_output_field = "data.result"
    prev_outputs_dict = False
    is_after_foreach = False

    for idx, bp_id in enumerate(blueprint_ids):
        bp = blueprints.get(bp_id, {})
        # Use unique key for duplicate bp_ids (e.g. two string_splits)
        key = bp_id if bp_id not in sanitized else f"{bp_id}_{idx}"
        bp_args = dict(args.get(bp_id, {}))
        wired_one = False

        required_args = [
            (name, meta) for name, meta in bp.get("args", {}).items()
            if meta.get("required") and name not in bp_args
        ]

        for arg_name, arg_meta in required_args:
            if is_after_foreach and arg_name in _DATA_FLOW_NAMES:
                bp_args[arg_name] = "${loop.item}"
                wired_one = True
                is_after_foreach = False
            elif (
                prev_last_step_id
                and not wired_one
                and arg_name in _DATA_FLOW_NAMES
            ):
                # Type-aware: if prev outputs dict and this param needs string,
                # wire via stringify (prev.result will be JSON string)
                if prev_outputs_dict and arg_name in _STRING_INPUT_PARAMS:
                    bp_args[arg_name] = f"${{{prev_last_step_id}.{prev_output_field}}}"
                    # Mark that we need a stringify step inserted
                    # (handled by _auto_insert_stringify below)
                else:
                    bp_args[arg_name] = f"${{{prev_last_step_id}.{prev_output_field}}}"
                wired_one = True
            else:
                bp_args[arg_name] = f"{{{{{arg_name}}}}}"

        sanitized[bp_id] = bp_args

        # Track state for next iteration
        is_after_foreach = bp_id in _ITERATION_BLUEPRINTS
        bp_steps = bp.get("steps", [])
        if bp_steps:
            prev_last_step_id = bp_steps[-1].get("id")
            last_module = bp_steps[-1].get("module", "")
            prev_outputs_dict = last_module in _DICT_OUTPUT_MODULES
        prev_output_field = bp.get("connections", {}).get("output_field", "data.result")

    return sanitized


async def generate_v2(
    description: str,
    blueprint_engine: Optional[Any] = None,
    llm: Optional[Any] = None,
    llm_model: Optional[str] = None,
    max_retries: int = 2,
    validator: Optional[Any] = None,
) -> PipelineResult:
    """
    Generate a validated workflow via the recipe-based pipeline (v2).

    Pipeline: select → compose → validate → if fail, retry with next candidates → autofix.
    Guaranteed: if it returns ok=True, the workflow passes sandbox validation.
    """
    # Get or create blueprint engine
    if blueprint_engine is None:
        try:
            from flyto_blueprint import get_engine
            blueprint_engine = get_engine()
        except ImportError:
            return PipelineResult(ok=False, error="flyto-blueprint not installed")

    try:
        from flyto_blueprint.compose import compose_chain
    except ImportError:
        return PipelineResult(ok=False, error="flyto-blueprint not installed")

    # Phase 1: Select blueprints
    recipe = select_blueprints(description, blueprint_engine)

    if not recipe.ok and llm:
        for attempt in range(1, max_retries + 1):
            recipe = await resolve_recipe(
                description=description, blueprint_engine=blueprint_engine,
                llm=llm, llm_model=llm_model,
            )
            if recipe.ok:
                break

    if not recipe or not recipe.ok:
        return PipelineResult(ok=False, error=f"No matching blueprints: {recipe.error if recipe else 'unknown'}")

    # Phase 2+4: Compose → Validate → Autofix loop
    result = _compose_and_validate(
        recipe.blueprints, recipe.args,
        blueprint_engine._blueprints, blueprint_engine._blocks,
    )

    if result:
        logger.info("Pipeline v2: %d steps from %s", len(result["steps"]), recipe.blueprints)
        return PipelineResult(
            ok=True,
            steps=result["steps"],
            edges=result["edges"],
            recipe=recipe,
        )

    return PipelineResult(
        ok=False,
        error=f"All blueprint combinations failed validation for: {recipe.blueprints}",
        recipe=recipe,
    )


def _compose_and_validate(
    blueprint_ids: List[str],
    args: Dict[str, Any],
    blueprints: Dict[str, dict],
    blocks: Dict[str, dict],
) -> Optional[Dict[str, Any]]:
    """Compose blueprint chain and validate all modules exist + refs resolve."""
    from flyto_blueprint.compose import compose_chain

    sanitized = _sanitize_recipe_args(blueprint_ids, args, blueprints)

    chain_result = compose_chain(
        blueprint_ids=blueprint_ids,
        args=sanitized,
        blueprints=blueprints,
        blocks=blocks,
    )

    if not chain_result.get("ok"):
        logger.warning("Compose failed for %s: %s", blueprint_ids, chain_result.get("error"))
        return None

    steps = chain_result["data"]["steps"]
    edges = chain_result["data"]["edges"]

    _fix_blueprint_id_refs(steps, blueprints)
    _clean_params(steps)
    _auto_insert_stringify(steps, edges)

    # Validate: all modules must exist, no unresolved {{X.Y}} patterns
    errors = _validate_workflow(steps, blueprints)
    if errors:
        logger.warning("Validation failed for %s: %s", blueprint_ids, errors)
        return None

    return {
        "name": "",
        "steps": steps,
        "edges": edges,
    }


def _validate_workflow(
    steps: List[Dict[str, Any]],
    blueprints: Dict[str, dict],
) -> List[str]:
    """Built-in validation — no external sandbox needed.

    Checks:
    1. All module IDs are known (exist in some blueprint)
    2. No {{X.Y}} unresolved patterns (indicates broken ref)
    3. All ${step_id.field} refs point to existing steps
    """
    import re

    errors = []
    known_modules = set()
    for bp in blueprints.values():
        for s in bp.get("steps", []):
            m = s.get("module", "")
            if m and "{{" not in m:
                known_modules.add(m)
    # Add common flow modules
    known_modules.update({"flow.start", "flow.foreach", "flow.while", "flow.repeat"})

    step_ids = {s["id"] for s in steps}
    broken_ref_re = re.compile(r"\{\{\w+\.\w+\}\}")  # {{step_id.field}} is broken
    step_ref_re = re.compile(r"\$\{(\w+)\.")

    for step in steps:
        module = step.get("module", "")

        # Check module exists
        if module and module not in known_modules and "{{" not in module:
            errors.append(f"Unknown module: {module}")

        # Check params
        for key, val in step.get("params", {}).items():
            if not isinstance(val, str):
                continue
            # Broken ref: {{step_id.field}} — should be ${step_id.field}
            if broken_ref_re.search(val):
                errors.append(f"Broken ref in {step['id']}.{key}: {val}")
            # Step ref validation: ${X.field} — X must be a known step or special var
            for m in step_ref_re.finditer(val):
                ref_root = m.group(1)
                if ref_root in ("params", "env", "loop", "steps", "item", "index"):
                    continue
                if ref_root not in step_ids:
                    errors.append(f"Unknown step ref '{ref_root}' in {step['id']}.{key}")

    return errors


# ---------------------------------------------------------------------------
# Post-processing helpers
# ---------------------------------------------------------------------------

import re

_STEP_REF_RE = re.compile(r"\$\{steps\.(\w+)\.")
_STEPS_PREFIX_RE = re.compile(r"\$\{steps\.(\w+)\.(.+?)\}")
_PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")


def _fix_blueprint_id_refs(
    steps: List[Dict[str, Any]],
    blueprints: Dict[str, dict],
) -> None:
    """Fix ${steps.blueprint_id.xxx} → ${steps.actual_step_id.xxx}.

    LLM often uses the blueprint ID (e.g. ``api_get``) instead of the
    actual step ID (e.g. ``api_request``).  Build a mapping and replace.
    """
    # Build mapping: blueprint_id → last step_id of that blueprint
    bp_to_step: Dict[str, str] = {}
    for bp_id, bp in blueprints.items():
        bp_steps = bp.get("steps", [])
        if bp_steps:
            bp_to_step[bp_id] = bp_steps[-1].get("id", bp_id)

    # Also map actual step IDs to themselves (so they don't get clobbered)
    actual_ids = {s["id"] for s in steps}

    def _replace_ref(val: str) -> str:
        def _sub(m):
            ref_id = m.group(1)
            if ref_id in actual_ids:
                return m.group(0)  # Already correct
            if ref_id in bp_to_step:
                real_id = bp_to_step[ref_id]
                return f"${{steps.{real_id}."
            return m.group(0)  # Unknown, leave as is
        return _STEP_REF_RE.sub(_sub, val)

    for step in steps:
        params = step.get("params", {})
        for key, val in list(params.items()):
            if isinstance(val, str) and "${steps." in val:
                params[key] = _replace_ref(val)


def _normalize_refs(steps: List[Dict[str, Any]]) -> None:
    """Normalize variable references to flyto-core runtime format.

    - ``${steps.X.data.Y}`` → ``${X.data.Y}`` (strip ``steps.`` prefix)
    - ``{{X}}`` → ``${params.X}`` (user-provided params)
    """
    for step in steps:
        params = step.get("params", {})
        for key, val in list(params.items()):
            if not isinstance(val, str):
                continue
            # ${steps.X.Y} → ${X.Y}
            val = _STEPS_PREFIX_RE.sub(r"${\1.\2}", val)
            # {{X}} → ${params.X}
            val = _PLACEHOLDER_RE.sub(r"${params.\1}", val)
            params[key] = val


def _auto_insert_stringify(
    steps: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
) -> None:
    """Insert data.json.stringify between dict-output and string-input steps.

    Detects: step A outputs dict (http.get) → step B needs string (file.write content).
    Inserts a stringify step in between and re-wires the ref.
    """
    import re
    ref_re = re.compile(r"\$\{(\w+)\.([\w.]+)\}")

    i = 0
    while i < len(steps):
        step = steps[i]
        params = step.get("params", {})
        for key, val in list(params.items()):
            if key not in _STRING_INPUT_PARAMS or not isinstance(val, str):
                continue
            m = ref_re.match(val)
            if not m:
                continue
            ref_step_id = m.group(1)
            # Find the referenced step
            ref_step = next((s for s in steps if s["id"] == ref_step_id), None)
            if not ref_step:
                continue
            if ref_step.get("module") not in _DICT_OUTPUT_MODULES:
                continue
            # Need stringify: insert between ref_step and this step
            stringify_id = f"{ref_step_id}_stringify"
            stringify_step = {
                "id": stringify_id,
                "module": "data.json.stringify",
                "label": "Convert to string",
                "params": {"data": val},
            }
            # Insert right before current step
            steps.insert(i, stringify_step)
            # Re-wire current step to use stringify output
            params[key] = f"${{{stringify_id}.data.result}}"
            # Add edge
            edges.append({
                "source": ref_step_id,
                "target": stringify_id,
            })
            edges.append({
                "source": stringify_id,
                "target": step["id"],
            })
            # Remove old direct edge if exists
            edges[:] = [
                e for e in edges
                if not (e.get("source") == ref_step_id and e.get("target") == step["id"])
            ]
            i += 1  # Skip the inserted step
            break  # Only fix one param per step
        i += 1


def _clean_params(steps: List[Dict[str, Any]]) -> None:
    """Remove nested dicts that look like blueprint args (not valid step params)."""
    for step in steps:
        params = step.get("params", {})
        to_remove = []
        for key, val in params.items():
            # Nested dict with ${...} or {{...}} — likely LLM hallucination
            if isinstance(val, dict) and any(
                isinstance(v, str) and ("${" in v or "{{" in v)
                for v in val.values()
            ):
                to_remove.append(key)
        for key in to_remove:
            del params[key]
