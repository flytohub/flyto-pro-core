# Copyright 2024 Flyto2
# Licensed under the Apache License, Version 2.0
"""
Factory v2 — Unit Tests

Tests for: models, autofix, resolve_recipe, select_blueprints, converter, generate_v2.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from flyto_pro_core.factory.models import RecipeResult, PipelineResult
from flyto_pro_core.factory.autofix import autofix_workflow

import importlib.util

# These tests exercise the real flyto-blueprint engine, an optional dependency
# not present in the [dev] extra. Skip them when it is unavailable.
requires_blueprint = pytest.mark.skipif(
    importlib.util.find_spec("flyto_blueprint") is None,
    reason="requires optional flyto-blueprint dependency",
)


# ============================================================================
# Model Tests
# ============================================================================


class TestRecipeResult:
    """Tests for RecipeResult behavior."""

    def test_success(self):
        """Verify success."""
        r = RecipeResult(ok=True, blueprints=["a", "b"], args={"a": {"x": 1}})
        assert r.ok is True
        d = r.to_dict()
        assert d["blueprints"] == ["a", "b"]

    def test_failure(self):
        """Verify failure."""
        r = RecipeResult(ok=False, error="no blueprints")
        assert r.ok is False


class TestPipelineResult:
    """Tests for PipelineResult behavior."""

    def test_success(self):
        """Verify success."""
        r = PipelineResult(
            ok=True,
            steps=[{"id": "s1", "module": "http.get"}],
            edges=[],
            recipe=RecipeResult(ok=True, blueprints=["http_get"]),
        )
        d = r.to_dict()
        assert d["ok"] is True
        assert len(d["steps"]) == 1

    def test_failure(self):
        """Verify failure."""
        r = PipelineResult(ok=False, error="fail")
        assert r.to_dict()["error"] == "fail"


# ============================================================================
# Autofix Tests
# ============================================================================


class TestAutofix:
    """Tests for Autofix behavior."""

    def test_fix_module_typo(self):
        """Verify fix module typo."""
        workflow = {
            "steps": [
                {"id": "s1", "module": "http.ger", "params": {"url": "http://x.com"}}
            ]
        }
        fixed, remaining = autofix_workflow(
            workflow, ["Unknown module 'http.ger'"], {"http.get", "http.post"}
        )
        assert len(remaining) == 0
        assert fixed["steps"][0]["module"] == "http.get"

    def test_fix_variable_ref_typo(self):
        """Verify fix variable ref typo."""
        workflow = {
            "steps": [
                {
                    "id": "fetch",
                    "module": "http.get",
                    "params": {"url": "http://x.com"},
                },
                {
                    "id": "notify",
                    "module": "slack.send",
                    "params": {"text": "${steps.ftch.data.body}"},
                },
            ]
        }
        fixed, remaining = autofix_workflow(
            workflow,
            ["invalid variable reference: unknown step 'ftch'"],
            {"http.get", "slack.send"},
        )
        assert len(remaining) == 0
        assert "${steps.fetch.data.body}" in fixed["steps"][1]["params"]["text"]

    def test_fix_missing_param_with_schema_default(self):
        """Verify fix missing param with schema default."""
        workflow = {
            "steps": [
                {"id": "s1", "module": "http.get", "params": {"url": "http://x.com"}}
            ]
        }
        schemas = {
            "http.get": {"properties": {"timeout": {"type": "number", "default": 30}}}
        }
        fixed, remaining = autofix_workflow(
            workflow,
            ["Missing required parameter 'timeout' in step 's1'"],
            {"http.get"},
            params_schemas=schemas,
        )
        assert len(remaining) == 0
        assert fixed["steps"][0]["params"]["timeout"] == 30

    def test_unfixable_error_remains(self):
        """Verify unfixable error remains."""
        _, remaining = autofix_workflow(
            {"steps": [{"id": "s1", "module": "x", "params": {}}]},
            ["Something unknown"],
            {"http.get"},
        )
        assert len(remaining) == 1

    def test_empty_steps(self):
        """Verify empty steps."""
        _, remaining = autofix_workflow({"steps": []}, ["error"], set())
        assert len(remaining) == 1


# ============================================================================
# Selector Tests
# ============================================================================


class TestSelectBlueprints:
    """Tests for SelectBlueprints behavior."""

    @requires_blueprint
    def test_select_from_real_engine(self):
        """Verify select from real engine."""
        from flyto_blueprint import BlueprintEngine
        from flyto_blueprint.storage.memory import MemoryBackend
        from flyto_pro_core.factory.selector import select_blueprints

        engine = BlueprintEngine(storage=MemoryBackend())

        # Simple single-blueprint from the current catalog.
        r = select_blueprints("HTTP GET request", engine)
        assert r.ok
        assert r.blueprints == ["api_get"]

        # Multi-intent request selects one direct blueprint for each intent.
        r = select_blueprints(
            "Health check a website and send Slack notification", engine
        )
        assert r.ok
        assert r.blueprints == ["monitor_http", "notify_slack"]

        # An unsupported request must not silently return an unrelated recipe.
        r = select_blueprints("Generate a QR code", engine)
        assert r.ok is False

    @requires_blueprint
    def test_browser_filter(self):
        """Verify browser filter."""
        from flyto_blueprint import BlueprintEngine
        from flyto_blueprint.storage.memory import MemoryBackend
        from flyto_pro_core.factory.selector import select_blueprints

        engine = BlueprintEngine(storage=MemoryBackend())

        # Non-browser query should not get browser blueprints
        r = select_blueprints("Send a Slack message", engine)
        assert r.ok
        for bp in r.blueprints:
            assert not bp.startswith("browser_")


# ============================================================================
# Converter Tests
# ============================================================================


class TestConverter:
    """Tests for Converter behavior."""

    def test_modules_to_workflow(self):
        """Verify modules to workflow."""
        from flyto_pro_core.factory.converter import modules_to_workflow

        wf = modules_to_workflow(
            modules=["http.get", "string.template", "slack.send"],
            name="Test",
        )
        assert len(wf["steps"]) == 3
        assert wf["steps"][0]["module"] == "http.get"
        assert wf["steps"][1]["module"] == "string.template"
        assert wf["steps"][2]["module"] == "slack.send"
        assert len(wf["edges"]) == 2

    def test_params_wiring(self):
        """Verify params wiring."""
        from flyto_pro_core.factory.converter import modules_to_workflow

        wf = modules_to_workflow(modules=["http.get", "slack.send"])
        # slack.send.text should be wired to http.get output
        slack_params = wf["steps"][1]["params"]
        assert "${" in slack_params.get("text", "")
        # webhook_url should be user placeholder
        assert "{{webhook_url}}" == slack_params.get("webhook_url", "")

    def test_string_template_has_variables(self):
        """Verify string template has variables."""
        from flyto_pro_core.factory.converter import modules_to_workflow

        wf = modules_to_workflow(modules=["string.template"])
        assert wf["steps"][0]["params"].get("variables") == {}


# ============================================================================
# resolve_recipe Tests (mocked LLM)
# ============================================================================


class TestResolveRecipe:
    """Tests for ResolveRecipe behavior."""

    @pytest.mark.asyncio
    async def test_resolve_recipe_success(self):
        """Verify resolve recipe success."""
        from flyto_pro_core.factory.recipe import resolve_recipe

        engine = MagicMock()
        engine.list_blueprints.return_value = [
            {
                "id": "string_split",
                "description": "Split text",
                "args": {"text": {"required": True}},
            },
            {
                "id": "qrcode_generate",
                "description": "Generate QR",
                "args": {"data": {"required": True}},
            },
        ]
        engine.search.return_value = []

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps(
            {"blueprints": ["string_split", "qrcode_generate"]}
        )
        mock_llm.chat = AsyncMock(return_value=mock_response)

        result = await resolve_recipe("generate QR codes", engine, llm=mock_llm)
        assert result.ok is True
        assert result.blueprints == ["string_split", "qrcode_generate"]
        assert result.args == {}  # Args filled by pipeline, not LLM

    @pytest.mark.asyncio
    async def test_resolve_recipe_no_blueprints(self):
        """Verify resolve recipe no blueprints."""
        from flyto_pro_core.factory.recipe import resolve_recipe

        engine = MagicMock()
        engine.list_blueprints.return_value = []

        result = await resolve_recipe("do something", engine)
        assert result.ok is False


# ============================================================================
# generate_v2 Tests
# ============================================================================


class TestGenerateV2:
    """Tests for GenerateV2 behavior."""

    @requires_blueprint
    @pytest.mark.asyncio
    async def test_generate_v2_with_real_engine(self):
        """Verify generate v2 with real engine."""
        from flyto_blueprint import BlueprintEngine
        from flyto_blueprint.storage.memory import MemoryBackend
        from flyto_pro_core.factory.pipeline import generate_v2

        engine = BlueprintEngine(storage=MemoryBackend())

        result = await generate_v2(
            description="HTTP GET request", blueprint_engine=engine
        )
        assert result.ok is True
        assert len(result.steps) >= 1
        assert result.steps[0]["module"] == "http.get"

    @requires_blueprint
    @pytest.mark.asyncio
    async def test_generate_v2_fetch_and_save(self):
        """Verify generate v2 fetch and save."""
        from flyto_blueprint import BlueprintEngine
        from flyto_blueprint.storage.memory import MemoryBackend
        from flyto_pro_core.factory.pipeline import generate_v2

        engine = BlueprintEngine(storage=MemoryBackend())

        result = await generate_v2(
            description="Fetch an API and save it to a file",
            blueprint_engine=engine,
        )
        assert result.ok is True
        modules = [s["module"] for s in result.steps]
        assert modules == ["http.get", "file.write"]

    @requires_blueprint
    @pytest.mark.asyncio
    async def test_generate_v2_no_match(self):
        """Verify generate v2 no match."""
        from flyto_blueprint import BlueprintEngine
        from flyto_blueprint.storage.memory import MemoryBackend
        from flyto_pro_core.factory.pipeline import generate_v2

        engine = BlueprintEngine(storage=MemoryBackend())

        result = await generate_v2(
            description="xyzzy foobar nonexistent",
            blueprint_engine=engine,
        )
        assert result.ok is False
