"""
Zapier seed → flyto YAML conversion test.

Converts all 100 Zapier-inspired seeds → flyto workflows → validate → run.

Usage:
    cd flyto-pro-core
    python test_zapier_convert.py
"""
import asyncio, sys, os, re, json, aiohttp, yaml, time
from pathlib import Path

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

from flyto_pro_core.factory.converter import modules_to_workflow
from flyto_pro_core.factory.enrich import enrich_template

API = "https://localhost:3000"
DELAY = 3

_DUMMY = {
    "url": "https://httpbin.org/get",
    "webhook_url": "https://httpbin.org/post",
    "path": "output/test.txt",
    "to": "test@example.com",
    "subject": "Test",
    "text": "hello",
    "content": "test",
    "data": "test data",
    "body": '{"key": "value"}',
    "prompt": "Say hello",
    "template": "Result: {{data}}",
    "query": "test query",
    "message": "test message",
    "method": "POST",
    "input": "test input",
}

# Modules that need external services (skip runtime test)
_SKIP_RUNTIME = {
    "email.send",  # Needs SMTP
    "notification.teams.send_message",  # Needs Teams webhook
    "notification.discord.send_message",  # Needs Discord webhook
    "http.webhook_wait",  # Hangs waiting for external trigger
}


async def main():
    # Load seeds
    from src.pro.factory.seed_bank import SEED_TEMPLATES

    # Load schemas
    module_schemas = {}
    try:
        from src.pro.factory.sandbox import SandboxExecutor
        s = SandboxExecutor.from_registry()
        for mid, ps in s._module_params_schema.items():
            if ps and isinstance(ps, dict):
                props, req = {}, []
                for fn, fd in ps.items():
                    if isinstance(fd, dict):
                        props[fn] = fd
                        if fd.get("required"): req.append(fn)
                module_schemas[mid] = {"properties": props, "required": req}
    except: pass

    print(f"Seeds: {len(SEED_TEMPLATES)}, Schemas: {len(module_schemas)}")

    # Phase 1: Convert all seeds → YAML (no network needed)
    gen_ok = 0
    gen_fail = 0
    converted = []

    for i, seed in enumerate(SEED_TEMPLATES):
        workflow = modules_to_workflow(
            modules=seed.modules,
            name=seed.description[:80],
            description=seed.description,
            module_schemas=module_schemas,
        )

        # Basic validation
        if not workflow["steps"]:
            gen_fail += 1
            print(f"  ✗ GEN [{i+1}] {seed.description[:60]} — no steps")
            continue

        # Enrich
        template = enrich_template(
            steps=workflow["steps"],
            edges=workflow["edges"],
            name=workflow["name"],
            module_schemas=module_schemas,
        )

        yaml_str = yaml.dump(template, default_flow_style=False, allow_unicode=True, sort_keys=False)

        # Check for broken refs
        if "{{" in yaml_str and ".result}}" in yaml_str:
            gen_fail += 1
            print(f"  ✗ GEN [{i+1}] {seed.description[:60]} — broken ref")
            continue

        gen_ok += 1
        skip_runtime = any(m in _SKIP_RUNTIME for m in seed.modules)
        converted.append({
            "idx": i + 1,
            "seed": seed,
            "yaml": yaml_str,
            "skip_runtime": skip_runtime,
        })

    print(f"\nGeneration: {gen_ok}/{gen_ok + gen_fail} passed\n")

    # Phase 2: Run first 20 non-skip seeds on live backend
    runnable = [c for c in converted if not c["skip_runtime"]][:20]
    run_ok = 0
    run_fail = 0
    run_skip = 0

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API}/api/health", ssl=False, timeout=aiohttp.ClientTimeout(total=5)) as r:
                if r.status != 200:
                    print("Backend not running, skipping runtime tests")
                    runnable = []
        except:
            print("Backend not reachable, skipping runtime tests")
            runnable = []

        for c in runnable:
            seed = c["seed"]
            yaml_str = c["yaml"]
            desc = seed.description[:50]

            # Fill params
            user_params = {}
            for m in re.finditer(r"\{\{(\w+)\}\}", yaml_str):
                name = m.group(1)
                if name not in user_params:
                    user_params[name] = _DUMMY.get(name, "test")

            # Canary check
            try:
                canary = "name: c\nsteps:\n  - id: s\n    module: flow.start\n    params: {}\n"
                async with session.post(f"{API}/api/workflows/run",
                    json={"workflow_yaml": canary, "params": {}}, ssl=False,
                    timeout=aiohttp.ClientTimeout(total=10)) as cr:
                    cd = await cr.json()
                    if cr.status != 200:
                        print(f"  ⏳ Engine down, stopping runtime tests")
                        break
                    # Wait for canary
                    cid = cd.get("execution_id", "")
                    for _ in range(5):
                        await asyncio.sleep(1)
                        try:
                            async with session.get(f"{API}/api/executions/{cid}", ssl=False) as cr2:
                                cd2 = await cr2.json()
                                if cd2.get("execution", cd2).get("status") in ("completed", "failed"):
                                    break
                        except: pass
            except:
                break

            # Run
            try:
                async with session.post(f"{API}/api/workflows/run",
                    json={"workflow_yaml": yaml_str, "params": {"ui": user_params}, "screenshot_mode": "off"},
                    ssl=False, timeout=aiohttp.ClientTimeout(total=15)) as r:
                    d = await r.json()
                    if r.status != 200 or not d.get("ok"):
                        err = d.get("error", "?")[:60]
                        run_fail += 1
                        print(f"  ✗ RUN [{c['idx']}] {desc} — {err}")
                        await asyncio.sleep(DELAY)
                        continue
                    exec_id = d["execution_id"]
            except Exception as e:
                run_fail += 1
                print(f"  ✗ RUN [{c['idx']}] {desc} — {e}")
                await asyncio.sleep(DELAY)
                continue

            # Poll
            status = "unknown"
            poll_data = {}
            for _ in range(20):
                await asyncio.sleep(2)
                try:
                    async with session.get(f"{API}/api/executions/{exec_id}", ssl=False) as r2:
                        poll_data = await r2.json()
                        status = poll_data.get("execution", poll_data).get("status", "unknown")
                        if status in ("completed", "failed", "error"):
                            break
                except: pass

            if status == "completed":
                run_ok += 1
                print(f"  ✓ RUN [{c['idx']}] {desc}")
            else:
                err = (poll_data.get("execution", poll_data).get("error", "?") or "?")[:80] if poll_data else "?"
                run_fail += 1
                print(f"  ✗ RUN [{c['idx']}] {desc} — {err}")

            await asyncio.sleep(DELAY)

    # Summary
    total_gen = gen_ok + gen_fail
    total_run = run_ok + run_fail
    print(f"\n{'='*60}")
    print(f"GENERATION: {gen_ok}/{total_gen} ({gen_ok/total_gen*100:.0f}%)")
    print(f"RUNTIME:    {run_ok}/{total_run} ({run_ok/total_run*100:.0f}%)" if total_run else "RUNTIME:    skipped")
    print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(main())
