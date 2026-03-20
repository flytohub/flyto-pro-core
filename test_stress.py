"""
Stress test: 30 random descriptions → generate → run → verify.
Smarter dummy params, 5s delay between runs.
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

from flyto_blueprint import BlueprintEngine
from flyto_blueprint.storage.memory import MemoryBackend
from flyto_pro_core.factory.pipeline import generate_v2
from flyto_pro_core.factory.enrich import enrich_template

API = "https://localhost:3000"
DELAY = 5

# Smart dummy values per param name
_DUMMY = {
    "url": "https://httpbin.org/get",
    "webhook_url": "https://httpbin.org/post",
    "path": "output/test_output.txt",
    "output": "output/test_output.txt",
    "input": "output/test_input.txt",
    "file_path": "output/test_input.txt",
    "to": "test@example.com",
    "subject": "Test Subject",
    "text": "hello world",
    "content": "test content",
    "data": "https://example.com",
    "body": "test body",
    "prompt": "Say hello",
    "template": "Hello {{name}}",
    "query": "flyto automation",
    "message": "test message",
    "items": "a\nb\nc",
}

DESCRIPTIONS = [
    "Generate a QR code",
    "Split text by comma",
    "Fetch URL and save response",
    "Send a Slack message",
    "Download a JSON file from API",
    "Generate QR codes from a list of URLs",
    "HTTP GET request",
    "Write text to file",
    "Fetch API data",
    "Split lines and generate QR for each",
    "Health check a website",
    "Render a text template",
    "Fetch URL and render template",
    "HTTP POST request with JSON body",
    "Search Google",
    "Split and loop over items",
    "Download file and write to disk",
    "Check if API is responding",
    "Generate QR code from URL",
    "Split text by newline",
]


async def main():
    engine = BlueprintEngine(storage=MemoryBackend())

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

    print(f"Blueprints: {len(engine._blueprints)}, Schemas: {len(module_schemas)}")
    print(f"Scenarios: {len(DESCRIPTIONS)}, Delay: {DELAY}s\n")

    results = {"pass": 0, "gen_fail": 0, "run_fail": 0, "exec_fail": 0}
    details = []

    # Create output dir for test files
    Path("output").mkdir(exist_ok=True)
    Path("output/test_input.txt").write_text("test,data,here\n1,2,3")

    async with aiohttp.ClientSession() as session:
        # Verify backend
        try:
            async with session.get(f"{API}/api/health", ssl=False, timeout=aiohttp.ClientTimeout(total=5)) as r:
                if r.status != 200:
                    print("Backend not running"); sys.exit(1)
        except:
            print("Backend not reachable"); sys.exit(1)

        for i, desc in enumerate(DESCRIPTIONS, 1):
            print(f"[{i:2d}/{len(DESCRIPTIONS)}] {desc}")

            # Generate
            result = await generate_v2(description=desc, blueprint_engine=engine)
            if not result.ok:
                results["gen_fail"] += 1
                details.append(f"  ✗ GEN: {desc} — {result.error[:60]}")
                print(f"         ✗ GEN FAIL: {result.error[:60]}")
                continue

            bps = result.recipe.blueprints
            template = enrich_template(steps=result.steps, edges=result.edges, name=desc, module_schemas=module_schemas)
            yaml_str = yaml.dump(template, default_flow_style=False, allow_unicode=True, sort_keys=False)

            # Smart params
            user_params = {}
            for m in re.finditer(r"\{\{(\w+)\}\}", yaml_str):
                name = m.group(1)
                if name not in user_params:
                    user_params[name] = _DUMMY.get(name, "test_value")

            # Canary: verify execution engine is alive before each run
            canary_ok = False
            for _retry in range(5):
                try:
                    canary_yaml = "name: canary\nsteps:\n  - id: s0\n    module: flow.start\n    params: {}\n"
                    async with session.post(f"{API}/api/workflows/run",
                        json={"workflow_yaml": canary_yaml, "params": {}},
                        ssl=False, timeout=aiohttp.ClientTimeout(total=10)) as _cr:
                        _cd = await _cr.json()
                        if _cr.status == 200 and _cd.get("ok"):
                            canary_ok = True
                            # Wait for canary to finish
                            cid = _cd["execution_id"]
                            for _ in range(10):
                                await asyncio.sleep(1)
                                try:
                                    async with session.get(f"{API}/api/executions/{cid}", ssl=False) as _cr2:
                                        _cd2 = await _cr2.json()
                                        if _cd2.get("execution", _cd2).get("status") in ("completed", "failed"):
                                            break
                                except: pass
                            break
                except: pass
                if not canary_ok:
                    print(f"         ⏳ Engine down, waiting {DELAY*2}s...")
                    await asyncio.sleep(DELAY * 2)
            if not canary_ok:
                results["run_fail"] += 1
                details.append(f"  ✗ RUN: {desc} — engine down after retries")
                print(f"         ✗ ENGINE DOWN, skipping")
                continue

            # Run
            try:
                async with session.post(f"{API}/api/workflows/run",
                    json={"workflow_yaml": yaml_str, "params": {"ui": user_params}, "screenshot_mode": "off"},
                    ssl=False, timeout=aiohttp.ClientTimeout(total=15)) as r:
                    d = await r.json()
                    if r.status != 200 or not d.get("ok"):
                        err = d.get("error", "?")[:80]
                        results["run_fail"] += 1
                        details.append(f"  ✗ RUN: {desc} ({bps}) — {err}")
                        print(f"         ✗ RUN FAIL: {err}")
                        await asyncio.sleep(DELAY)
                        continue
                    exec_id = d["execution_id"]
            except Exception as e:
                results["run_fail"] += 1
                details.append(f"  ✗ RUN: {desc} — {e}")
                print(f"         ✗ RUN ERROR: {e}")
                await asyncio.sleep(DELAY)
                continue

            # Poll — wait for THIS execution to finish before starting next
            status = "unknown"
            d2 = {}
            for _ in range(30):
                await asyncio.sleep(2)
                try:
                    async with session.get(f"{API}/api/executions/{exec_id}", ssl=False) as r2:
                        d2 = await r2.json()
                        status = d2.get("execution", d2).get("status", "unknown")
                        if status in ("completed", "failed", "error", "cancelled"):
                            break
                except: pass

            if status == "completed":
                results["pass"] += 1
                details.append(f"  ✓ {desc} → {bps}")
                print(f"         ✓ COMPLETED ({bps})")
            else:
                err = d2.get("execution", d2).get("error", "?")[:100] if d2 else "?"
                results["exec_fail"] += 1
                details.append(f"  ✗ EXEC: {desc} ({bps}) — {err}")
                print(f"         ✗ {status.upper()}: {err[:60]}")

            await asyncio.sleep(DELAY)

    # Summary
    total = sum(results.values())
    print(f"\n{'='*60}")
    print(f"RESULTS: {results['pass']}/{total} passed")
    print(f"  gen_fail={results['gen_fail']}, run_fail={results['run_fail']}, exec_fail={results['exec_fail']}")
    print(f"{'='*60}")
    for d in details:
        print(d)

    sys.exit(0 if results["pass"] == total else 1)

if __name__ == "__main__":
    asyncio.run(main())
