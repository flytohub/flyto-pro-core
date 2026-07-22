#!/usr/bin/env python3
"""Convert the 100 Flyto2 Pro seed workflows without network execution.

The source seed bank belongs to the sibling ``flyto-pro`` repository. Override
its location with ``FLYTO_PRO_REPO`` when the repositories are not siblings.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

from flyto_pro_core.factory.converter import modules_to_workflow
from flyto_pro_core.factory.enrich import enrich_template


ROOT = Path(__file__).resolve().parent
FLYTO_PRO_REPO = Path(
    os.environ.get("FLYTO_PRO_REPO", ROOT.parent / "flyto-pro")
).resolve()


def load_seed_templates():
    """Load the commercial seed bank from an explicit local repository path."""
    if not FLYTO_PRO_REPO.is_dir():
        raise RuntimeError(
            "flyto-pro repository not found; set FLYTO_PRO_REPO to its checkout"
        )
    sys.path.insert(0, str(FLYTO_PRO_REPO))
    try:
        from src.pro.factory.seed_bank import SEED_TEMPLATES
    finally:
        sys.path.pop(0)
    return SEED_TEMPLATES


def main() -> int:
    """Convert every seed and reject empty workflows or malformed references."""
    failures = []
    seeds = load_seed_templates()

    for index, seed in enumerate(seeds, 1):
        workflow = modules_to_workflow(
            modules=seed.modules,
            name=seed.description[:80],
            description=seed.description,
        )
        template = enrich_template(
            steps=workflow["steps"],
            edges=workflow["edges"],
            name=workflow["name"],
        )
        rendered = yaml.safe_dump(template, allow_unicode=True, sort_keys=False)

        if not template["steps"]:
            failures.append(f"seed {index}: no steps: {seed.description}")
        if ".result}}" in rendered:
            failures.append(f"seed {index}: malformed reference: {seed.description}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print(f"Seed conversion contract passed: {len(seeds)} workflows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
