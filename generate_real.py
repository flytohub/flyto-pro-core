#!/usr/bin/env python3
"""Generate deterministic Factory examples from the installed Blueprint catalog.

The historical filename is retained for compatibility. This script is offline:
it does not load credentials, call an LLM, or execute the generated workflows.
"""

from __future__ import annotations

import asyncio
import argparse
from pathlib import Path

import yaml
from flyto_blueprint import BlueprintEngine
from flyto_blueprint.storage.memory import MemoryBackend

from flyto_pro_core.factory.enrich import enrich_template
from flyto_pro_core.factory.pipeline import generate_v2


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"
SCENARIOS = [
    "HTTP GET request",
    "Fetch an API and save it to a file",
    "Health check a website",
    "Send a Slack message",
    "Resize an image",
]


async def main(*, check: bool = False) -> int:
    """Generate one enriched YAML example for every supported scenario."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    engine = BlueprintEngine(storage=MemoryBackend())
    failures = []
    expected_paths = set()

    for index, description in enumerate(SCENARIOS, 1):
        result = await generate_v2(description, blueprint_engine=engine)
        if not result.ok:
            failures.append(f"{description}: {result.error}")
            continue

        template = enrich_template(
            steps=result.steps,
            edges=result.edges,
            name=description,
            description=description,
        )
        filename = f"example_{index:02d}_{result.recipe.blueprints[0]}.yaml"
        output = OUTPUT_DIR / filename
        expected_paths.add(output)
        content = yaml.safe_dump(template, allow_unicode=True, sort_keys=False)
        if check:
            current = (
                await asyncio.to_thread(output.read_text, encoding="utf-8")
                if output.exists()
                else None
            )
            if current != content:
                failures.append(f"stale generated example: {output.relative_to(ROOT)}")
        else:
            await asyncio.to_thread(output.write_text, content, encoding="utf-8")
            print(
                f"generated {output.relative_to(ROOT)} ({len(template['steps'])} steps)"
            )

    unexpected = set(OUTPUT_DIR.glob("example_*.yaml")) - expected_paths
    failures.extend(
        f"unexpected generated example: {path.relative_to(ROOT)}"
        for path in sorted(unexpected)
    )

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        return 1
    if check:
        print(f"Factory example contract passed: {len(expected_paths)} files")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    raise SystemExit(asyncio.run(main(check=arguments.check)))
