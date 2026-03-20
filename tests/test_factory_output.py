# Copyright 2024 Flyto
# Licensed under the Apache License, Version 2.0
"""
Factory v2 — Output verification

Generates real YAML files to /tmp/factory_v2_output/ for manual inspection.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml

from flyto_blueprint import BlueprintEngine
from flyto_blueprint.storage.memory import MemoryBackend
from flyto_pro_core.factory.pipeline import generate_v2

OUTPUT_DIR = Path("/tmp/factory_v2_output")


@pytest.fixture(autouse=True)
def setup_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture
def engine():
    return BlueprintEngine(storage=MemoryBackend())


def _mock_llm(response_dict):
    mock = MagicMock()
    resp = MagicMock()
    resp.content = json.dumps(response_dict)
    mock.chat = AsyncMock(return_value=resp)
    return mock


def _save(name, result):
    workflow = {
        "name": name,
        "description": name,
        "steps": result.steps,
        "edges": result.edges,
    }
    path = OUTPUT_DIR / f"{name.replace(' ', '_')}.yaml"
    path.write_text(yaml.dump(workflow, default_flow_style=False, allow_unicode=True, sort_keys=False))
    print(f"\n{'='*60}")
    print(f"  OUTPUT: {path}")
    print(f"{'='*60}")
    print(path.read_text())
    return path


@pytest.mark.asyncio
async def test_qrcode_pipeline(engine):
    result = await generate_v2(
        description="批量生成 QR code",
        blueprint_engine=engine,
        llm=_mock_llm({
            "blueprints": ["string_split", "foreach_loop", "qrcode_generate"],
            "args": {
                "string_split": {"text": "https://flyto.io\nhttps://github.com/flytohub", "delimiter": "\n"},
                "foreach_loop": {"items": "${steps.split_text.data.result}", "module": "image.qrcode_generate"},
                "qrcode_generate": {"content": "${steps.loop.data.item}"},
            },
        }),
    )
    assert result.ok, result.error
    _save("批量生成_QR_code", result)


@pytest.mark.asyncio
async def test_http_to_slack(engine):
    result = await generate_v2(
        description="Fetch API and notify Slack",
        blueprint_engine=engine,
        llm=_mock_llm({
            "blueprints": ["http_get", "slack_notify"],
            "args": {
                "http_get": {"url": "https://api.example.com/health"},
                "slack_notify": {"webhook_url": "https://hooks.slack.com/services/XXX", "text": "API status: ${steps.http_request.data.body}"},
            },
        }),
    )
    assert result.ok, result.error
    _save("fetch_api_notify_slack", result)


@pytest.mark.asyncio
async def test_ai_summarize_email(engine):
    result = await generate_v2(
        description="AI summarize sales and email to boss",
        blueprint_engine=engine,
        llm=_mock_llm({
            "blueprints": ["llm_chat", "email_send"],
            "args": {
                "llm_chat": {"prompt": "Summarize today's sales numbers: revenue $12,500, orders 84, returns 3"},
                "email_send": {"to": "boss@company.com", "subject": "Daily Sales Summary", "body": "${steps.ai_chat.data.response}"},
            },
        }),
    )
    assert result.ok, result.error
    _save("ai_summarize_email", result)


@pytest.mark.asyncio
async def test_scrape_transform_save(engine):
    result = await generate_v2(
        description="Fetch JSON, transform, save to file",
        blueprint_engine=engine,
        llm=_mock_llm({
            "blueprints": ["http_get", "json_transform", "file_save"],
            "args": {
                "http_get": {"url": "https://api.example.com/users"},
                "json_transform": {"template": "Total users: ${steps.http_request.data.body}"},
                "file_save": {"path": "/tmp/report.txt", "content": "${steps.render_template.data.result}"},
            },
        }),
    )
    assert result.ok, result.error
    _save("fetch_transform_save", result)


@pytest.mark.asyncio
async def test_five_blueprint_chain(engine):
    result = await generate_v2(
        description="Full pipeline: split URLs, fetch each, transform, save, notify",
        blueprint_engine=engine,
        llm=_mock_llm({
            "blueprints": ["string_split", "http_get", "json_transform", "file_save", "slack_notify"],
            "args": {
                "string_split": {"text": "https://a.com\nhttps://b.com", "delimiter": "\n"},
                "http_get": {"url": "${steps.split_text.data.result}"},
                "json_transform": {"template": "Fetched: ${steps.http_request.data.body}"},
                "file_save": {"path": "/tmp/output.txt", "content": "${steps.render_template.data.result}"},
                "slack_notify": {"webhook_url": "https://hooks.slack.com/xxx", "text": "Pipeline done, saved to /tmp/output.txt"},
            },
        }),
    )
    assert result.ok, result.error
    _save("full_5_step_pipeline", result)
