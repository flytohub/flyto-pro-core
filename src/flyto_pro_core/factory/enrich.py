# Copyright 2024 Flyto
# Licensed under the Apache License, Version 2.0
"""
Factory v2 — Phase 3: Template Enrichment

Converts pipeline output into the EXACT template format flyto-cloud canvas expects.

Target format reference (from real template):
- User params: {{param_name}} (mustache)
- Step refs: ${steps.NODE_ID.result} (no .data. prefix)
- Loop body refs: ${loop.item}
- All module params filled with schema defaults
- _ui.builder with full component definitions
"""

from __future__ import annotations

import re
import time
import random
import string
from typing import Any, Dict, List, Optional, Set

_LOOP_MODULES = {"flow.foreach", "flow.while", "flow.repeat"}


def enrich_template(
    steps: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    name: str = "",
    description: str = "",
    module_schemas: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    module_schemas = module_schemas or {}
    ts = int(time.time() * 1000)
    suffix_chars = string.ascii_lowercase + string.digits

    # --- 1. Generate new node IDs ---
    id_map: Dict[str, str] = {}
    for idx, step in enumerate(steps):
        suffix = "".join(random.choices(suffix_chars, k=6))
        id_map[step["id"]] = f"node_{ts + idx + 1}_{idx}_{suffix}"

    # --- 2. Build enriched steps ---
    enriched_steps: List[Dict[str, Any]] = []

    # flow.start
    start_id = f"node_{ts}"
    enriched_steps.append({
        "id": start_id,
        "module": "flow.start",
        "label": start_id,
        "params": {},
        "positionX": 100,
        "positionY": 150,
        "orderIndex": 0,
    })

    # Detect which steps are foreach body (next step after a foreach node)
    foreach_body_map: Dict[str, str] = {}  # foreach_new_id → body_new_id
    for i, step in enumerate(steps):
        if step.get("module") in _LOOP_MODULES and i + 1 < len(steps):
            foreach_new = id_map[step["id"]]
            body_new = id_map[steps[i + 1]["id"]]
            foreach_body_map[foreach_new] = body_new

    body_ids = set(foreach_body_map.values())

    for idx, step in enumerate(steps):
        old_id = step["id"]
        new_id = id_map[old_id]
        module_id = step.get("module", "")
        schema = module_schemas.get(module_id, {})
        properties = schema.get("properties", {}) if isinstance(schema, dict) else {}

        # Build params: start from schema defaults, overlay blueprint params
        params = {}
        for prop_name, prop_def in properties.items():
            if not isinstance(prop_def, dict):
                continue
            if "default" in prop_def:
                params[prop_name] = prop_def["default"]
            elif prop_def.get("type") == "string":
                params[prop_name] = ""
            elif prop_def.get("type") == "number":
                params[prop_name] = 0
            elif prop_def.get("type") == "boolean":
                params[prop_name] = prop_def.get("default", False)

        # Overlay blueprint params (converting refs)
        for key, val in step.get("params", {}).items():
            if isinstance(val, str):
                val = _convert_ref(val, id_map)
            params[key] = val

        # Is this a foreach body node?
        is_body = new_id in body_ids
        # Find parent foreach if body
        if is_body:
            parent_foreach = [k for k, v in foreach_body_map.items() if v == new_id]
            if parent_foreach:
                # Replace data-flow ref with ${loop.item}
                for key, val in params.items():
                    if isinstance(val, str) and "${steps." in val:
                        params[key] = "${loop.item}"
                        break  # Only replace the main data input

        # Position
        is_main_flow = not is_body
        if is_main_flow:
            main_idx = len([s for s in enriched_steps if s["id"] not in body_ids])
            pos_x = 100 + main_idx * 300
            pos_y = 150
        else:
            # Body nodes: same X as parent foreach, Y + 250
            parent_step = next((s for s in enriched_steps if s["id"] in foreach_body_map and foreach_body_map[s["id"]] == new_id), None)
            pos_x = parent_step["positionX"] if parent_step else 700
            pos_y = (parent_step["positionY"] if parent_step else 150) + 250

        enriched_step: Dict[str, Any] = {
            "id": new_id,
            "module": module_id,
            "label": new_id,
            "params": params,
            "positionX": pos_x,
            "positionY": pos_y,
            "orderIndex": idx + 1,
        }

        # Foreach: add connections.iterate
        if new_id in foreach_body_map:
            enriched_step["connections"] = {
                "iterate": [foreach_body_map[new_id]],
            }

        enriched_steps.append(enriched_step)

    # --- 3. Generate edges ---
    enriched_edges = _generate_edges(enriched_steps, body_ids, foreach_body_map)

    # --- 4. Build _ui.builder ---
    ui = _build_ui(steps, module_schemas)

    template: Dict[str, Any] = {
        "name": name,
        "version": "1.0.0",
        "steps": enriched_steps,
        "edges": enriched_edges,
    }
    if ui:
        template["_ui"] = ui

    return template


# --- Reference conversion ---

_STEP_DATA_REF = re.compile(r"\$\{(\w+)\.data\.(\w+)\}")  # ${step_id.data.field} → ${steps.NEW_ID.field}
_STEP_REF = re.compile(r"\$\{(\w+)\.(\w+)\}")  # ${step_id.field}
_PARAM_REF = re.compile(r"\$\{params\.(\w+)\}")  # ${params.X} → {{X}}


def _convert_ref(val: str, id_map: Dict[str, str]) -> str:
    """Convert pipeline refs to canvas format."""
    # ${params.X} → {{X}}
    val = _PARAM_REF.sub(r"{{\1}}", val)

    # ${step_id.data.field} → ${steps.NEW_ID.field}
    def _sub_data(m):
        old_id, field = m.group(1), m.group(2)
        new_id = id_map.get(old_id, old_id)
        return f"${{steps.{new_id}.{field}}}"
    val = _STEP_DATA_REF.sub(_sub_data, val)

    # ${step_id.field} (without .data.) → ${steps.NEW_ID.field}
    def _sub_plain(m):
        old_id, field = m.group(1), m.group(2)
        if old_id in ("steps", "params", "env", "loop", "item"):
            return m.group(0)  # Don't touch these
        new_id = id_map.get(old_id, old_id)
        return f"${{steps.{new_id}.{field}}}"
    val = _STEP_REF.sub(_sub_plain, val)

    return val


# --- Edge generation ---

def _generate_edges(
    steps: List[Dict[str, Any]],
    body_ids: Set[str],
    foreach_body_map: Dict[str, str],
) -> List[Dict[str, Any]]:
    edges: List[Dict[str, Any]] = []

    # Main flow (excluding body nodes)
    main_ids = [s["id"] for s in steps if s["id"] not in body_ids]

    for i in range(len(main_ids) - 1):
        src, tgt = main_ids[i], main_ids[i + 1]
        src_step = next((s for s in steps if s["id"] == src), {})

        # Skip foreach nodes (they use connections.iterate, not sequential to body)
        if src in foreach_body_map:
            continue

        tgt_step = next((s for s in steps if s["id"] == tgt), {})
        tgt_handle = "in" if tgt_step.get("module") in _LOOP_MODULES else "target"

        edges.append({
            "id": f"e_{src}_{tgt}",
            "source": src,
            "target": tgt,
            "sourceHandle": "output",
            "targetHandle": tgt_handle,
            "type": "glow",
            "data": {"edgeType": "sequential", "pathType": "bezier"},
        })

    # Iterate edges
    for foreach_id, body_id in foreach_body_map.items():
        edges.append({
            "id": f"loop_iterate_{foreach_id}_{body_id}",
            "source": foreach_id,
            "target": body_id,
            "sourceHandle": "body_out",
            "targetHandle": "target-top",
            "type": "glow",
            "data": {"edgeType": "iterate", "pathType": "smoothstep"},
            "label": "Iterate",
        })

    return edges


# --- UI Builder ---

_TEXTAREA_NAMES = {
    "text", "content", "body", "prompt", "message", "template",
    "script", "code", "query", "items", "data", "description",
}


def _build_ui(
    steps: List[Dict[str, Any]],
    module_schemas: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Build _ui.builder from {{X}} params in steps.

    Also includes key module params that users might want to customize
    (e.g. size, color, error_correction for qrcode).
    """
    param_re = re.compile(r"\{\{(\w+)\}\}")

    # 1. Collect explicit {{X}} user params
    user_params = []
    seen = set()
    for step in steps:
        for val in (step.get("params") or {}).values():
            if isinstance(val, str):
                for m in param_re.finditer(val):
                    name = m.group(1)
                    if name not in seen:
                        user_params.append(name)
                        seen.add(name)

    if not user_params:
        return {}

    # 2. Build components ONLY for {{X}} user params — no internal module params
    large = []
    small = []

    for pname in user_params:
        comp = _resolve_component(pname, steps, module_schemas)
        if comp["type"] in ("textarea",):
            large.append(comp)
        else:
            small.append(comp)

    # 4. Layout sections
    sections = []

    sec_idx = 0
    for comp in large:
        sec_idx += 1
        sections.append({
            "id": f"section_{sec_idx}",
            "gap": "16px",
            "columns": 1,
            "grid": [12],
            "columnsData": [{"components": [comp]}],
        })

    if small:
        left, right = [], []
        for i, comp in enumerate(small):
            (left if i % 2 == 0 else right).append(comp)
        sec_idx += 1
        sections.append({
            "id": f"section_{sec_idx}",
            "gap": "16px",
            "columns": 2,
            "grid": [6, 6],
            "columnsData": [
                {"components": left},
                {"components": right},
            ],
        })

    return {"builder": {"sections": sections}}


def _resolve_component(
    param_name: str,
    steps: List[Dict[str, Any]],
    module_schemas: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Build a _ui.builder component for a param, using module schema if available."""
    # Find which module + field this param maps to
    for step in steps:
        module_id = step.get("module", "")
        schema = module_schemas.get(module_id, {})
        properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
        for key, val in (step.get("params") or {}).items():
            if isinstance(val, str) and f"{{{{{param_name}}}}}" in val:
                prop = properties.get(key, {})
                if prop and isinstance(prop, dict):
                    return _prop_to_component(param_name, prop)

    # Fallback
    is_textarea = param_name in _TEXTAREA_NAMES
    comp: Dict[str, Any] = {
        "label": param_name.replace("_", " ").title(),
        "id": param_name,
        "type": "textarea" if is_textarea else "text",
        "props": {},
    }
    if is_textarea:
        comp["props"]["required"] = True
        comp["props"]["rows"] = 6
    return comp


def _prop_to_component(param_name: str, prop: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a flyto-core params_schema field to a _ui.builder component."""
    label = prop.get("label") or param_name.replace("_", " ").title()
    ptype = prop.get("type", "string")
    fmt = prop.get("format", "")

    # Detect widget type
    if prop.get("options"):
        comp_type = "select"
    elif fmt == "color" or ptype == "color":
        comp_type = "color"
    elif ptype in ("number", "integer"):
        comp_type = "number"
    elif ptype == "boolean":
        comp_type = "boolean"
    elif param_name in _TEXTAREA_NAMES or ptype == "textarea":
        comp_type = "textarea"
    else:
        comp_type = "text"

    comp: Dict[str, Any] = {
        "label": label,
        "id": param_name,
        "type": comp_type,
        "props": {},
    }

    # Default value
    if prop.get("default") is not None:
        comp["default"] = prop["default"]
    if prop.get("placeholder"):
        comp["props"]["placeholder"] = prop["placeholder"]

    # Type-specific props
    if comp_type == "textarea":
        comp["props"]["required"] = True
        comp["props"]["rows"] = 6
        if prop.get("placeholder"):
            comp["props"]["placeholder"] = prop["placeholder"]
    elif comp_type == "number":
        validation = prop.get("validation", {})
        if validation.get("min") is not None:
            comp["props"]["min"] = validation["min"]
        if validation.get("max") is not None:
            comp["props"]["max"] = validation["max"]
        if prop.get("default") is not None:
            comp["props"]["defaultValue"] = prop["default"]
        if prop.get("placeholder"):
            comp["props"]["placeholder"] = prop["placeholder"]
    elif comp_type == "select" and prop.get("options"):
        comp["props"]["options"] = prop["options"]
        if prop.get("default") is not None:
            comp["props"]["defaultValue"] = prop["default"]
    elif comp_type == "color":
        comp["props"]["default"] = prop.get("default", "#000000")
        comp["props"]["placeholder"] = prop.get("placeholder", "#000000")
        comp["props"]["defaultValue"] = prop.get("default", "#000000")
        if prop.get("default") is not None:
            comp["default"] = prop["default"]

    return comp
