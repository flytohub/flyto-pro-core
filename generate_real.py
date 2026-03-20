"""
Real end-to-end factory v2 — calls real OpenAI, real BlueprintEngine.
Outputs YAML files to ./output/

Usage:
    cd flyto-pro-core
    python generate_real.py
"""

import asyncio
import os
import re
import sys
from pathlib import Path

# Load .env from flyto-pro
import os
env_path = Path(__file__).resolve().parent.parent / "flyto-pro" / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

# Add sibling projects to path
_base = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_base / "flyto-core"))
sys.path.insert(0, str(_base / "flyto-pro"))

from flyto_blueprint import BlueprintEngine
from flyto_blueprint.storage.memory import MemoryBackend
from flyto_pro_core.factory.pipeline import generate_v2
from flyto_pro_core.interfaces.providers.openai_llm import OpenAILLMService

import yaml

OUTPUT_DIR = Path(__file__).parent / "output"


SCENARIOS = [
    "Split text into lines and generate a QR code for each line",
    "Fetch API health check and send Slack notification",
    "AI summarize sales data and email to manager",
    "Fetch JSON from API and save to file",
    "Split a list of URLs and fetch each one",
]


async def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    key = os.getenv("OPENAI_API_KEY")
    if not key:
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)

    print(f"OpenAI key: {key[:8]}...{key[-4:]}")
    print(f"Output dir: {OUTPUT_DIR}\n")

    engine = BlueprintEngine(storage=MemoryBackend())
    llm = OpenAILLMService(model="gpt-4o")

    print(f"Loaded {len(engine._blueprints)} blueprints")

    # Load module schemas via SandboxExecutor (it already loads flyto-core registry)
    module_schemas = {}
    try:
        from src.pro.factory.sandbox import SandboxExecutor as _SE
        _sandbox_for_schemas = _SE.from_registry()
        for mid, ps in _sandbox_for_schemas._module_params_schema.items():
            if not ps or not isinstance(ps, dict):
                continue
            properties = {}
            required_fields = []
            for fname, fdef in ps.items():
                if isinstance(fdef, dict):
                    properties[fname] = fdef
                    if fdef.get("required"):
                        required_fields.append(fname)
            module_schemas[mid] = {"properties": properties, "required": required_fields}
        print(f"Loaded {len(module_schemas)} module schemas")
    except Exception as e:
        print(f"Module schemas not available: {e}")
    print()

    # SandboxExecutor for post-generation validation
    sandbox = None
    validator = None
    try:
        from src.pro.factory.sandbox import SandboxExecutor
        sandbox = SandboxExecutor.from_registry()

        async def _validate(workflow):
            r = await sandbox.execute(workflow)
            return r.success, r.errors

        validator = _validate
        print("SandboxExecutor: available (will validate)\n")
    except ImportError:
        print("SandboxExecutor: not available (skipping validation)\n")

    for i, desc in enumerate(SCENARIOS, 1):
        print(f"[{i}/{len(SCENARIOS)}] {desc}")
        print("-" * 60)

        result = await generate_v2(
            description=desc,
            blueprint_engine=engine,
            # No LLM — pure search-based selection
        )

        if not result.ok:
            print(f"  FAILED: {result.error}\n")
            continue

        # Sandbox validation BEFORE enrichment
        # Sandbox expects ${params.X} and ${step.field}, not {{X}} and ${steps.X.field}
        if sandbox:
            import copy as _copy
            sandbox_steps = _copy.deepcopy(result.steps)
            for s in sandbox_steps:
                for k, v in s.get("params", {}).items():
                    if isinstance(v, str):
                        v = re.sub(r"\{\{(\w+)\}\}", r"${params.\1}", v)  # {{X}} → ${params.X}
                        v = re.sub(r"\$\{steps\.(\w+)\.", r"${\1.", v)  # ${steps.X. → ${X.
                        s["params"][k] = v
            pre_workflow = {
                "name": desc, "description": desc,
                "steps": sandbox_steps, "edges": result.edges,
            }
            sr = await sandbox.execute(pre_workflow)
            if sr.success:
                print(f"  ✓ SANDBOX PASS")
            else:
                print(f"  ✗ SANDBOX FAIL:")
                for err in sr.errors:
                    print(f"    - {err}")

        # Phase 3: Enrich to full template format (converts to ${steps.X.Y} canvas format)
        from flyto_pro_core.factory.enrich import enrich_template
        template = enrich_template(
            steps=result.steps,
            edges=result.edges,
            name=desc,
            description=desc,
            module_schemas=module_schemas,
        )

        # Save YAML
        filename = f"{i:02d}_{desc[:40].replace(' ', '_').replace('/', '_')}.yaml"
        path = OUTPUT_DIR / filename
        yaml_str = yaml.dump(template, default_flow_style=False, allow_unicode=True, sort_keys=False)
        path.write_text(yaml_str)

        print(f"  Blueprints: {result.recipe.blueprints}")
        print(f"  Steps: {len(template['steps'])}")
        print(f"  Edges: {len(template['edges'])}")
        print(f"  Output: {path}")
        print()
        print(yaml_str)
        print()

    print(f"Done. Files in {OUTPUT_DIR}/")


if __name__ == "__main__":
    asyncio.run(main())
