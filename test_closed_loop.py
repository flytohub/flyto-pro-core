"""
Closed-loop test: generate YAML → run on local backend → verify execution succeeds.

No manual intervention. Hits localhost:3000/api/workflows/run directly.

Usage:
    cd flyto-pro-core
    python test_closed_loop.py
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

import aiohttp
import yaml

_base = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_base / "flyto-core"))
sys.path.insert(0, str(_base / "flyto-pro"))

env_path = _base / "flyto-pro" / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

API_BASE = "https://localhost:3000"
POLL_INTERVAL = 2
MAX_WAIT = 60

# Test scenarios: description → test params (values for {{X}} placeholders)
SCENARIOS = [
    {
        "description": "Fetch API health check and send Slack notification",
        "params": {"url": "https://httpbin.org/get", "webhook_url": "https://httpbin.org/post"},
    },
    {
        "description": "Fetch JSON from API and save to file",
        "params": {"url": "https://httpbin.org/get", "content": "hello world"},
    },
    {
        "description": "Split text and generate a QR code for each line",
        "params": {"text": "https://google.com\nhttps://github.com"},
    },
    {
        "description": "Fetch a URL and render a text template with the result",
        "params": {"url": "https://httpbin.org/get", "template": "Result: {{data}}"},
    },
    {
        "description": "Write text content to a file",
        "params": {"path": "output/hello.txt", "content": "Hello World from Factory v2!"},
    },
    {
        "description": "Download a file from URL and save locally",
        "params": {"url": "https://httpbin.org/get", "path": "downloads/test_download.json"},
    },
    {
        "description": "Generate a QR code from a URL",
        "params": {"data": "https://flyto2.com"},
    },
    {
        "description": "Split text by newline and process each line",
        "params": {"text": "line1\nline2\nline3"},
    },
]


async def generate_yaml(description: str) -> dict:
    """Generate enriched YAML via factory v2 pipeline."""
    from flyto_blueprint import BlueprintEngine
    from flyto_blueprint.storage.memory import MemoryBackend
    from flyto_pro_core.factory.pipeline import generate_v2
    from flyto_pro_core.factory.enrich import enrich_template
    engine = BlueprintEngine(storage=MemoryBackend())

    # Load schemas
    module_schemas = {}
    try:
        from src.pro.factory.sandbox import SandboxExecutor
        sandbox = SandboxExecutor.from_registry()
        for mid, ps in sandbox._module_params_schema.items():
            if ps and isinstance(ps, dict):
                props = {}
                req = []
                for fn, fd in ps.items():
                    if isinstance(fd, dict):
                        props[fn] = fd
                        if fd.get("required"):
                            req.append(fn)
                module_schemas[mid] = {"properties": props, "required": req}
    except Exception:
        pass

    result = await generate_v2(
        description=description,
        blueprint_engine=engine,
    )

    if not result.ok:
        return {"ok": False, "error": result.error}

    template = enrich_template(
        steps=result.steps,
        edges=result.edges,
        name=description,
        description=description,
        module_schemas=module_schemas,
    )

    return {"ok": True, "template": template, "blueprints": result.recipe.blueprints}


async def run_workflow(session: aiohttp.ClientSession, yaml_str: str, params: dict) -> dict:
    """Send workflow to /api/workflows/run and return execution result."""
    payload = {
        "workflow_yaml": yaml_str,
        "params": {"ui": params},
        "screenshot_mode": "off",
    }

    async with session.post(
        f"{API_BASE}/api/workflows/run",
        json=payload,
        ssl=False,
    ) as resp:
        body = await resp.json()
        if resp.status != 200:
            return {"ok": False, "error": f"HTTP {resp.status}: {body}"}
        return body


async def poll_execution(session: aiohttp.ClientSession, execution_id: str) -> dict:
    """Poll execution status until complete or timeout."""
    start = time.time()
    while time.time() - start < MAX_WAIT:
        try:
            async with session.get(
                f"{API_BASE}/api/executions/{execution_id}",
                ssl=False,
            ) as resp:
                if resp.status != 200:
                    await asyncio.sleep(POLL_INTERVAL)
                    continue
                data = await resp.json()
                status = data.get("status") or data.get("execution", {}).get("status")
                if status in ("completed", "failed", "error", "cancelled"):
                    return {"ok": status == "completed", "status": status, "data": data}
        except Exception:
            pass
        await asyncio.sleep(POLL_INTERVAL)
    return {"ok": False, "status": "timeout"}


async def main():
    print("=" * 70)
    print("  CLOSED-LOOP TEST: Generate → Run → Verify")
    print("=" * 70)
    print(f"  API: {API_BASE}")
    print()

    results = []

    async with aiohttp.ClientSession() as session:
        # Check backend is running
        try:
            async with session.get(f"{API_BASE}/api/health", ssl=False, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    print("ERROR: Backend not responding at", API_BASE)
                    sys.exit(1)
                print("Backend: OK\n")
        except Exception as e:
            print(f"ERROR: Cannot reach backend at {API_BASE}: {e}")
            sys.exit(1)

        for i, scenario in enumerate(SCENARIOS, 1):
            desc = scenario["description"]
            params = scenario["params"]
            print(f"[{i}/{len(SCENARIOS)}] {desc}")
            print("-" * 60)

            # Step 1: Generate
            print("  1. Generating YAML...", end=" ", flush=True)
            gen = await generate_yaml(desc)
            if not gen["ok"]:
                print(f"FAIL: {gen['error']}")
                results.append({"scenario": desc, "ok": False, "stage": "generate", "error": gen["error"]})
                print()
                continue
            print(f"OK ({gen['blueprints']})")

            yaml_str = yaml.dump(gen["template"], default_flow_style=False, allow_unicode=True, sort_keys=False)

            # Save for debugging
            fname = f"closedloop_{i:02d}.yaml"
            Path(f"output/{fname}").write_text(yaml_str)

            # Step 2: Run
            print("  2. Running workflow...", end=" ", flush=True)
            run_result = await run_workflow(session, yaml_str, params)
            if not run_result.get("ok"):
                print(f"FAIL: {run_result.get('error', run_result)}")
                results.append({"scenario": desc, "ok": False, "stage": "run", "error": str(run_result)})
                print()
                continue

            exec_id = run_result.get("execution_id")
            print(f"OK (execution_id={exec_id})")

            # Step 3: Poll
            print("  3. Waiting for completion...", end=" ", flush=True)
            poll = await poll_execution(session, exec_id)
            status = poll.get("status", "unknown")
            if poll["ok"]:
                print(f"COMPLETED")
                results.append({"scenario": desc, "ok": True, "execution_id": exec_id})
            else:
                print(f"FAIL (status={status})")
                # Try to get error details
                error_detail = ""
                if poll.get("data"):
                    error_detail = str(poll["data"].get("error", ""))[:200]
                results.append({"scenario": desc, "ok": False, "stage": "execution", "status": status, "error": error_detail})
            # Delay between scenarios to avoid overloading execution engine
            await asyncio.sleep(3)
            print()

    # Summary
    print("=" * 70)
    print("  RESULTS")
    print("=" * 70)
    passed = sum(1 for r in results if r["ok"])
    total = len(results)
    for r in results:
        icon = "✓" if r["ok"] else "✗"
        line = f"  {icon} {r['scenario']}"
        if not r["ok"]:
            line += f" [{r.get('stage', '?')}: {r.get('error', r.get('status', ''))[:80]}]"
        print(line)
    print()
    print(f"  {passed}/{total} passed")
    print()

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    asyncio.run(main())
