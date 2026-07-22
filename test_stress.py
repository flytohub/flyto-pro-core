#!/usr/bin/env python3
"""Repeat offline Factory generation to detect nondeterminism and catalog drift."""

from __future__ import annotations

import asyncio

from flyto_blueprint import BlueprintEngine
from flyto_blueprint.storage.memory import MemoryBackend

from flyto_pro_core.factory.pipeline import generate_v2


SUPPORTED = {
    "HTTP GET request": {"http.get"},
    "Fetch an API and save it to a file": {"http.get", "file.write"},
    "Send a Slack message": {"notification.slack.send_message"},
    "Health check a website": {"http.get"},
    "Resize an image": {"image.resize"},
    "Extract text from a PDF": {"pdf.parse", "file.write"},
    "Convert CSV data to JSON": {"data.csv.read", "data.json.stringify"},
}
UNSUPPORTED = [
    "Generate a QR code",
    "xyzzy foobar nonexistent",
]
ROUNDS = 5


async def main() -> int:
    """Run the catalog contract repeatedly and report any unstable result."""
    engine = BlueprintEngine(storage=MemoryBackend())
    failures = []

    for round_number in range(1, ROUNDS + 1):
        for description, required_modules in SUPPORTED.items():
            result = await generate_v2(description, blueprint_engine=engine)
            modules = {step["module"] for step in result.steps}
            if not result.ok or not required_modules.issubset(modules):
                failures.append(
                    f"round {round_number}: {description}: "
                    f"ok={result.ok}, modules={sorted(modules)}, error={result.error}"
                )

        for description in UNSUPPORTED:
            result = await generate_v2(description, blueprint_engine=engine)
            if result.ok:
                failures.append(
                    f"round {round_number}: unsupported request matched "
                    f"{result.recipe.blueprints}: {description}"
                )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    total = ROUNDS * (len(SUPPORTED) + len(UNSUPPORTED))
    print(f"Factory stress contract passed: {total} deterministic scenarios")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
