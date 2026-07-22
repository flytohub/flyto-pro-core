#!/usr/bin/env python3
"""Run the reproducible Flyto2 Pro Core verification loop."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile
from pathlib import Path

try:
    import tomllib
except ImportError:  # pragma: no cover - Python 3.10 compatibility
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "flyto_pro_core"


def run(*command: str, cwd: Path = ROOT) -> None:
    """Run one required command and stop on failure."""
    print(f"+ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def source_inventory() -> set[str]:
    """Return package files that must be present in built artifacts."""
    return {
        path.relative_to(ROOT / "src").as_posix()
        for path in PACKAGE.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }


def verify_wheel(wheel: Path, expected: set[str], version: str) -> None:
    """Verify wheel contents and core metadata before installation."""
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        missing = sorted(expected - names)
        if missing:
            raise RuntimeError(f"wheel is missing package files: {missing}")
        metadata_name = next(
            name for name in names if name.endswith(".dist-info/METADATA")
        )
        metadata = archive.read(metadata_name).decode("utf-8")
    required = [
        f"Version: {version}",
        "Requires-Python: >=3.10",
        "Requires-Dist: pydantic>=2.0.0",
        "Requires-Dist: python-dotenv>=1.0.0",
        "Requires-Dist: pyyaml>=6.0",
        "Project-URL: Repository, https://github.com/flytohub/flyto-pro-core.git",
    ]
    absent = [line for line in required if line not in metadata]
    if absent:
        raise RuntimeError(f"wheel metadata is missing: {absent}")


def verify_sdist(sdist: Path, expected: set[str]) -> None:
    """Verify the source archive contains every distributable package file."""
    with tarfile.open(sdist, "r:gz") as archive:
        names = {"/".join(name.split("/")[1:]) for name in archive.getnames()}
    expected_sdist = {f"src/{name}" for name in expected}
    missing = sorted(expected_sdist - names)
    if missing:
        raise RuntimeError(f"sdist is missing package files: {missing}")


def smoke_install(wheel: Path, version: str, directory: Path) -> None:
    """Install the wheel into an isolated interpreter and import core surfaces."""
    environment = directory / "venv"
    venv.EnvBuilder(with_pip=True, system_site_packages=True).create(environment)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    run(
        str(python),
        "-m",
        "pip",
        "install",
        "--no-deps",
        "--force-reinstall",
        str(wheel),
    )
    code = (
        "import flyto_pro_core; "
        "from flyto_pro_core.config import Settings; "
        "from flyto_pro_core.contract.models.params_schema import ParamType; "
        f"assert flyto_pro_core.__version__ == {version!r}; "
        "assert Settings().environment; assert ParamType.ANY.value == 'any'"
    )
    run(str(python), "-c", code)


def verify_package() -> None:
    """Build, inspect, and install both package artifacts in a temporary tree."""
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = metadata["project"]["version"]
    expected = source_inventory()
    with tempfile.TemporaryDirectory(prefix="flyto-pro-core-build-") as temp:
        directory = Path(temp)
        output = directory / "dist"
        run(sys.executable, "-m", "build", "--outdir", str(output))
        wheel = next(output.glob("*.whl"))
        sdist = next(output.glob("*.tar.gz"))
        verify_wheel(wheel, expected, version)
        verify_sdist(sdist, expected)
        smoke_install(wheel, version, directory)


def main() -> int:
    """Run lint, tests, generated contracts, artifacts, and Indexer verification."""
    run(sys.executable, "-m", "ruff", "check", ".")
    run(sys.executable, "-m", "pytest", "-q")
    run(sys.executable, "scripts/generate-api-reference.py", "--check")
    run(sys.executable, "scripts/generate-config-reference.py", "--check")
    run(sys.executable, "scripts/check-documentation.py")
    run(sys.executable, "generate_real.py", "--check")
    run(sys.executable, "test_stress.py")
    verify_package()

    indexer = shutil.which("flyto-index")
    if not indexer:
        raise RuntimeError("flyto-index is required for closed-loop verification")
    run(indexer, "verify", ".", "--strict")
    print("Flyto2 Pro Core verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
