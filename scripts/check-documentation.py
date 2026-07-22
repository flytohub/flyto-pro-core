#!/usr/bin/env python3
"""Validate the documentation manifest and local Markdown links."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterator


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "documentation-manifest.json"
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
SKIP_PARTS = {".flyto-index", ".git", ".mypy_cache", ".pytest_cache", ".ruff_cache"}


def documentation_paths(manifest: dict) -> Iterator[str]:
    """Yield every documentation path declared by the manifest."""
    yield from manifest["documentation"].values()
    for area in manifest["source_areas"]:
        yield from area["documentation"]
    for feature in manifest["feature_surfaces"]:
        yield from feature["documentation"]


def markdown_files() -> Iterator[Path]:
    """Yield repository Markdown files outside generated and tool caches."""
    for path in ROOT.rglob("*.md"):
        if not any(part in SKIP_PARTS for part in path.parts):
            yield path


def local_target(source: Path, raw_target: str) -> Path | None:
    """Resolve one Markdown target, or return None for non-local links."""
    target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
    if target.startswith(("#", "http://", "https://", "mailto:")):
        return None
    path = target.split("#", 1)[0]
    return (source.parent / path).resolve() if path else None


def main() -> int:
    """Fail when the manifest or a local Markdown link points to a missing file."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    missing = []
    for raw_path in documentation_paths(manifest):
        path = raw_path.split("#", 1)[0]
        if path and not (ROOT / path).exists():
            missing.append(f"manifest: {raw_path}")

    files = list(markdown_files())
    checked_links = 0
    for source in files:
        content = source.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(content):
            target = local_target(source, raw_target)
            if target is None:
                continue
            checked_links += 1
            if not target.exists():
                relative_source = source.relative_to(ROOT).as_posix()
                missing.append(f"{relative_source}: {raw_target}")

    if missing:
        raise RuntimeError("missing documentation targets:\n" + "\n".join(missing))
    print(
        "documentation structure passed: "
        f"{len(files)} Markdown files, {checked_links} local links"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
