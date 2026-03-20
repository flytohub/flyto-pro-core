# Copyright 2024 Flyto
# Licensed under the Apache License, Version 2.0
"""Factory v2 — Data Models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RecipeResult:
    """Result of LLM blueprint selection (Phase 1)."""

    ok: bool
    blueprints: List[str] = field(default_factory=list)
    args: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "blueprints": self.blueprints,
            "args": self.args,
            "error": self.error,
        }


@dataclass
class PipelineResult:
    """Result of the full v2 pipeline (Phase 1→2→4)."""

    ok: bool
    steps: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    recipe: Optional[RecipeResult] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "steps": self.steps,
            "edges": self.edges,
            "recipe": self.recipe.to_dict() if self.recipe else None,
            "error": self.error,
        }
