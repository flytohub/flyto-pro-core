# Copyright 2024 Flyto
# Licensed under the Apache License, Version 2.0
"""
Factory v2 — Integration Tests

Uses REAL BlueprintEngine + REAL compose_chain + REAL blueprints.
Verifies end-to-end YAML generation.
"""

from __future__ import annotations

import pytest
import yaml

from flyto_blueprint import BlueprintEngine
from flyto_blueprint.storage.memory import MemoryBackend
from flyto_pro_core.factory.pipeline import generate_v2
from flyto_pro_core.factory.converter import modules_to_workflow
from flyto_pro_core.factory.enrich import enrich_template


@pytest.fixture
def engine():
    return BlueprintEngine(storage=MemoryBackend())


class TestPipelineEndToEnd:

    @pytest.mark.asyncio
    async def test_qrcode(self, engine):
        result = await generate_v2("Generate a QR code", blueprint_engine=engine)
        assert result.ok
        assert any(s["module"] == "image.qrcode_generate" for s in result.steps)

    @pytest.mark.asyncio
    async def test_split_and_qr(self, engine):
        result = await generate_v2("Split text and generate QR for each", blueprint_engine=engine)
        assert result.ok
        modules = [s["module"] for s in result.steps]
        assert "string.split" in modules
        assert "image.qrcode_generate" in modules
        assert "flow.foreach" in modules

    @pytest.mark.asyncio
    async def test_http_get(self, engine):
        result = await generate_v2("HTTP GET request", blueprint_engine=engine)
        assert result.ok
        assert result.steps[0]["module"] == "http.get"

    @pytest.mark.asyncio
    async def test_fetch_and_notify(self, engine):
        result = await generate_v2("Health check a website and send Slack notification", blueprint_engine=engine)
        assert result.ok
        modules = [s["module"] for s in result.steps]
        assert "http.get" in modules
        assert any("slack" in m for m in modules)

    @pytest.mark.asyncio
    async def test_yaml_roundtrip(self, engine):
        result = await generate_v2("Write text to file", blueprint_engine=engine)
        assert result.ok
        workflow = {"steps": result.steps, "edges": result.edges}
        yaml_str = yaml.dump(workflow, default_flow_style=False, allow_unicode=True)
        parsed = yaml.safe_load(yaml_str)
        assert len(parsed["steps"]) == len(result.steps)

    @pytest.mark.asyncio
    async def test_no_match(self, engine):
        result = await generate_v2("xyzzy foobar nonexistent", blueprint_engine=engine)
        assert result.ok is False


class TestConverterEndToEnd:

    def test_zapier_seed_converts(self):
        wf = modules_to_workflow(
            modules=["http.get", "string.template", "slack.send"],
            name="Test Zapier Seed",
        )
        assert len(wf["steps"]) == 3
        assert len(wf["edges"]) == 2
        # Params are wired
        assert "${" in wf["steps"][1]["params"]["template"]
        assert "${" in wf["steps"][2]["params"]["text"]
        # User placeholders for non-data params
        assert "{{webhook_url}}" == wf["steps"][2]["params"]["webhook_url"]

    def test_all_100_seeds_convert(self):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "flyto-pro"))
        try:
            from src.pro.factory.seed_bank import SEED_TEMPLATES
        except ImportError:
            pytest.skip("flyto-pro not available")

        for seed in SEED_TEMPLATES:
            wf = modules_to_workflow(modules=seed.modules, name=seed.description[:60])
            assert len(wf["steps"]) > 0, f"Empty steps for: {seed.description}"
            assert len(wf["edges"]) == len(wf["steps"]) - 1, f"Edge count wrong for: {seed.description}"


class TestEnrichEndToEnd:

    def test_enrich_adds_flow_start(self):
        steps = [{"id": "s1", "module": "http.get", "params": {"url": "{{url}}"}}]
        template = enrich_template(steps=steps, edges=[], name="Test")
        assert template["steps"][0]["module"] == "flow.start"
        assert len(template["steps"]) == 2

    def test_enrich_adds_positions(self):
        steps = [
            {"id": "s1", "module": "http.get", "params": {"url": "{{url}}"}},
            {"id": "s2", "module": "file.write", "params": {"path": "{{path}}", "content": "${s1.data.body}"}},
        ]
        template = enrich_template(steps=steps, edges=[{"source": "s1", "target": "s2"}], name="Test")
        for step in template["steps"]:
            assert "positionX" in step
            assert "positionY" in step
            assert "orderIndex" in step

    def test_enrich_adds_edges(self):
        steps = [
            {"id": "s1", "module": "http.get", "params": {"url": "{{url}}"}},
            {"id": "s2", "module": "file.write", "params": {"content": "${s1.data.body}"}},
        ]
        template = enrich_template(steps=steps, edges=[{"source": "s1", "target": "s2"}], name="Test")
        assert len(template["edges"]) >= 2  # start→s1, s1→s2
        for edge in template["edges"]:
            assert "sourceHandle" in edge
            assert "targetHandle" in edge
            assert "type" in edge

    def test_enrich_builds_ui(self):
        steps = [{"id": "s1", "module": "http.get", "params": {"url": "{{url}}"}}]
        template = enrich_template(steps=steps, edges=[], name="Test")
        assert "_ui" in template
        sections = template["_ui"]["builder"]["sections"]
        assert len(sections) > 0
        # Should have a component with id=url
        all_comps = []
        for sec in sections:
            for col in sec.get("columnsData", []):
                all_comps.extend(col.get("components", []))
        assert any(c["id"] == "url" for c in all_comps)

    def test_enrich_sections_have_id(self):
        steps = [{"id": "s1", "module": "http.get", "params": {"url": "{{url}}"}}]
        template = enrich_template(steps=steps, edges=[], name="Test")
        for sec in template["_ui"]["builder"]["sections"]:
            assert "id" in sec, "Section missing 'id' field"
