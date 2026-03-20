# Copyright 2024 Flyto
# Licensed under the Apache License, Version 2.0
"""Factory v2 — Recipe-based template generation pipeline.

LLM only picks which blueprints to compose (a JSON array of IDs).
Everything else — wiring, layout, edges — is deterministic.

Usage:
    from flyto_pro_core.factory import generate_v2, resolve_recipe, autofix_workflow

    result = await generate_v2(description="批量生成 QR code")
"""

from .models import RecipeResult, PipelineResult
from .recipe import resolve_recipe
from .selector import select_blueprints
from .autofix import autofix_workflow
from .pipeline import generate_v2

__all__ = [
    "RecipeResult",
    "PipelineResult",
    "resolve_recipe",
    "autofix_workflow",
    "generate_v2",
]
