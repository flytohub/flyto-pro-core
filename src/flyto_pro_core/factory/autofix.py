# Copyright 2024 Flyto
# Licensed under the Apache License, Version 2.0
"""
Factory v2 — Phase 4: Deterministic Autofix

Tries to fix common workflow errors without re-running the LLM:
- Module typos → fuzzy match from known modules
- Missing required params → fill from params_schema defaults
- Invalid variable refs → fix step ID typos
"""

from __future__ import annotations

import re
from difflib import get_close_matches
from typing import Any, Dict, List, Optional, Set, Tuple


def autofix_workflow(
    workflow: Dict[str, Any],
    errors: List[str],
    known_modules: Set[str],
    params_schemas: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Attempt deterministic fixes for common workflow errors.

    Args:
        workflow: Workflow dict with steps.
        errors: List of error strings from validation.
        known_modules: Set of valid module IDs.
        params_schemas: Optional module_id → params_schema mapping for default values.

    Returns:
        (fixed_workflow, remaining_errors) — remaining_errors is empty if all fixed.
    """
    steps = workflow.get("steps", [])
    if not steps:
        return workflow, errors

    remaining = []
    step_ids = {s.get("id") for s in steps if s.get("id")}

    for error in errors:
        fixed = False

        # Try module typo fix
        fixed = fixed or _fix_module_typo(error, steps, known_modules)

        # Try missing param fix
        if not fixed and params_schemas:
            fixed = _fix_missing_param(error, steps, params_schemas)

        # Try variable ref fix
        if not fixed:
            fixed = _fix_variable_ref(error, steps, step_ids)

        if not fixed:
            remaining.append(error)

    return workflow, remaining


def _fix_module_typo(
    error: str,
    steps: List[Dict[str, Any]],
    known_modules: Set[str],
) -> bool:
    """Fix module ID typos using fuzzy matching."""
    # Pattern: "Unknown module 'xxx'" or "Module 'xxx' not found"
    match = re.search(
        r"(?:unknown module|module\b.*\bnot found)[:\s]*['\"]?(\S+?)['\"]?(?:\s|$|['\"])",
        error,
        re.IGNORECASE,
    )
    if not match:
        match = re.search(r"[Uu]nknown module\s+['\"](\S+?)['\"]", error)
    if not match:
        match = re.search(r"module['\"\s]+(\S+?)['\"]", error, re.IGNORECASE)
    if not match:
        return False

    bad_module = match.group(1).strip("'\"")
    candidates = get_close_matches(bad_module, list(known_modules), n=1, cutoff=0.6)
    if not candidates:
        # Try prefix match
        candidates = [m for m in known_modules if m.startswith(bad_module.split(".")[0] + ".")]
        if not candidates:
            return False
        candidates = candidates[:1]

    replacement = candidates[0]
    for step in steps:
        if step.get("module") == bad_module:
            step["module"] = replacement
            return True
    return False


def _fix_missing_param(
    error: str,
    steps: List[Dict[str, Any]],
    params_schemas: Dict[str, Dict[str, Any]],
) -> bool:
    """Fill missing required params with defaults from params_schema."""
    # Pattern: "Missing required parameter 'xxx' in step 'yyy'"
    match = re.search(
        r"missing required param(?:eter)?[:\s]*['\"]?(\w+)['\"]?.*(?:step|in)[:\s]*['\"]?(\w+)['\"]?",
        error,
        re.IGNORECASE,
    )
    if not match:
        return False

    param_name = match.group(1)
    step_id = match.group(2)

    for step in steps:
        if step.get("id") != step_id:
            continue
        module_id = step.get("module", "")
        schema = params_schemas.get(module_id, {})
        properties = schema.get("properties", {})
        prop = properties.get(param_name, {})

        # Use default from schema
        default = prop.get("default")
        if default is not None:
            step.setdefault("params", {})[param_name] = default
            return True

        # Use type-based default
        prop_type = prop.get("type", "string")
        type_defaults = {
            "string": "",
            "number": 0,
            "integer": 0,
            "boolean": False,
            "array": [],
            "object": {},
        }
        if prop_type in type_defaults:
            step.setdefault("params", {})[param_name] = type_defaults[prop_type]
            return True

    return False


def _fix_variable_ref(
    error: str,
    steps: List[Dict[str, Any]],
    step_ids: Set[str],
) -> bool:
    """Fix variable reference typos (e.g. ${steps.stp1.result} → ${steps.step1.result})."""
    # Pattern: "Variable reference ... unknown step 'xxx'" or "invalid ... step 'xxx'"
    match = re.search(
        r"(?:unknown step|step\b.*\bnot found)[:\s]*['\"]?(\w+)['\"]?",
        error,
        re.IGNORECASE,
    )
    if not match:
        match = re.search(r"(?:invalid|unknown).*(?:step|reference).*['\"](\w+)['\"]", error, re.IGNORECASE)
    if not match:
        return False

    bad_step_id = match.group(1)
    if bad_step_id in step_ids:
        return False  # Not actually a typo

    candidates = get_close_matches(bad_step_id, list(step_ids), n=1, cutoff=0.6)
    if not candidates:
        return False

    replacement = candidates[0]
    old_ref = f"${{steps.{bad_step_id}."
    new_ref = f"${{steps.{replacement}."
    old_ref2 = f"${{{bad_step_id}."
    new_ref2 = f"${{{replacement}."

    fixed = False
    for step in steps:
        params = step.get("params", {})
        for key, val in params.items():
            if isinstance(val, str):
                if old_ref in val:
                    params[key] = val.replace(old_ref, new_ref)
                    fixed = True
                elif old_ref2 in val:
                    params[key] = val.replace(old_ref2, new_ref2)
                    fixed = True
    return fixed
