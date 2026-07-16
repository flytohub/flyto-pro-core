# Copyright 2024 Flyto2
# Licensed under the Apache License, Version 2.0
"""
Factory v2 — Output verification

Generates real YAML files to /tmp/factory_v2_output/ for manual inspection.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
_WORKSPACE_ROOT = _REPO_ROOT.parent
for _path in (_REPO_ROOT / "src", _WORKSPACE_ROOT / "flyto-blueprint"):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)

# Skip the whole module when the optional flyto-blueprint dep is absent
# (these are real end-to-end integration tests; the dep is not in [dev]).
pytest.importorskip("flyto_blueprint")

from flyto_blueprint import BlueprintEngine  # noqa: E402
from flyto_blueprint.storage.memory import MemoryBackend  # noqa: E402
from flyto_pro_core.factory.pipeline import generate_v2  # noqa: E402

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
async def test_api_fetch_save_pipeline(engine):
    result = await generate_v2(
        description="Fetch Flyto2 homepage and save the response",
        blueprint_engine=engine,
        llm=_mock_llm({
            "blueprints": ["api_fetch_save"],
            "args": {
                "api_fetch_save": {"url": "https://flyto2.com", "path": "/tmp/flyto2-homepage.json"},
            },
        }),
    )
    assert result.ok, result.error
    _save("fetch_flyto2_homepage_save_response", result)


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
