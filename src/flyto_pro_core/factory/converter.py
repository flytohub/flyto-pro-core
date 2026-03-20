# Copyright 2024 Flyto
# Licensed under the Apache License, Version 2.0
"""
Factory v2 — Zapier Seed → flyto YAML Converter

Converts a list of module IDs (from Zapier seed mapping) into a complete
flyto workflow with steps, params, edges, positions, and _ui.

No LLM. No blueprint search. Pure deterministic conversion.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

# Module output type hints
_DICT_OUTPUT = {"http.get", "http.request", "http.webhook_wait", "http.paginate"}
_STRING_OUTPUT = {
    "string.template", "string.split", "llm.chat", "ai.extract",
    "email.send", "slack.send", "file.read", "pdf.parse", "image.ocr",
}
_LIST_OUTPUT = {"string.split", "array.filter", "array.map", "data.csv.read"}

# Params that carry data between steps (need wiring)
_DATA_PARAMS = {"text", "content", "body", "data", "message", "prompt", "query", "input", "template", "path", "url"}

# Known required params per module (most important ones)
_MODULE_REQUIRED_PARAMS: Dict[str, List[str]] = {
    "http.get": ["url"],
    "http.request": ["url", "method", "body"],
    "http.webhook_wait": [],
    "string.template": ["template"],
    "string.split": ["text"],
    "slack.send": ["webhook_url", "text"],
    "notification.slack.send_message": ["webhook_url", "text"],
    "notification.discord.send_message": ["webhook_url", "content"],
    "notification.teams.send_message": ["webhook_url", "text"],
    "email.send": ["to", "subject", "body"],
    "llm.chat": ["prompt"],
    "ai.extract": ["text"],
    "file.write": ["path", "content"],
    "file.read": ["path"],
    "image.qrcode_generate": ["data"],
    "data.json.stringify": ["data"],
    "core.api.google_search": ["query"],
}


def modules_to_workflow(
    modules: List[str],
    name: str = "",
    description: str = "",
    module_schemas: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Convert a list of module IDs into a complete workflow.

    Args:
        modules: Ordered list of flyto module IDs (e.g. ["http.get", "string.template", "slack.send"])
        name: Workflow name
        description: Workflow description
        module_schemas: Optional module_id → params_schema for filling defaults

    Returns:
        Workflow dict with steps, edges ready for enrich_template()
    """
    module_schemas = module_schemas or {}
    steps = []
    edges = []

    prev_step_id = None
    prev_output_field = "data.result"
    prev_module = None

    for idx, module_id in enumerate(modules):
        step_id = _make_step_id(module_id, idx)
        params = _build_params(
            module_id, idx, prev_step_id, prev_output_field, prev_module, module_schemas,
        )

        steps.append({
            "id": step_id,
            "module": module_id,
            "label": _module_to_label(module_id),
            "params": params,
        })

        if prev_step_id:
            edges.append({
                "source": prev_step_id,
                "target": step_id,
            })

        prev_step_id = step_id
        prev_module = module_id
        prev_output_field = _get_output_field(module_id)

    return {
        "name": name,
        "description": description,
        "steps": steps,
        "edges": edges,
    }


def _make_step_id(module_id: str, idx: int) -> str:
    """Generate a readable step ID from module."""
    parts = module_id.split(".")
    base = parts[-1] if len(parts) > 1 else parts[0]
    return f"{base}_{idx}"


def _module_to_label(module_id: str) -> str:
    """Convert module ID to human-readable label."""
    parts = module_id.replace(".", " ").replace("_", " ").split()
    return " ".join(p.capitalize() for p in parts)


def _get_output_field(module_id: str) -> str:
    """Get the default output field for a module."""
    if module_id in ("http.get", "http.request", "http.paginate"):
        return "data.body"
    if module_id == "llm.chat":
        return "data.response"
    if module_id == "file.read":
        return "data.content"
    if module_id == "string.split":
        return "data.result"
    return "data.result"


def _build_params(
    module_id: str,
    idx: int,
    prev_step_id: Optional[str],
    prev_output_field: str,
    prev_module: Optional[str],
    module_schemas: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Build params for a step, wiring to previous step where appropriate."""
    required = _MODULE_REQUIRED_PARAMS.get(module_id, [])
    schema = module_schemas.get(module_id, {})
    properties = schema.get("properties", {}) if isinstance(schema, dict) else {}

    params: Dict[str, Any] = {}
    wired_one = False

    for param_name in required:
        if prev_step_id and not wired_one and param_name in _DATA_PARAMS:
            # Wire to previous step output
            # If prev outputs dict and this needs string, add stringify note
            if prev_module in _DICT_OUTPUT and param_name in ("text", "content", "body", "message", "template"):
                # Still wire — stringify is handled by _auto_insert_stringify in pipeline
                params[param_name] = f"${{{prev_step_id}.{prev_output_field}}}"
            else:
                params[param_name] = f"${{{prev_step_id}.{prev_output_field}}}"
            wired_one = True
        else:
            # User-provided placeholder
            params[param_name] = f"{{{{{param_name}}}}}"

    # Fill schema defaults for non-required params
    for prop_name, prop_def in properties.items():
        if prop_name in params:
            continue
        if not isinstance(prop_def, dict):
            continue
        if "default" in prop_def:
            params[prop_name] = prop_def["default"]

    # Special cases
    if module_id == "http.request" and "method" in params:
        params["method"] = "POST"
    if module_id == "string.template" and "variables" not in params:
        params["variables"] = {}

    return params
