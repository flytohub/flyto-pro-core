# Release Runbook

## Preconditions

1. Update `pyproject.toml`, `flyto_pro_core.__version__`, `CHANGELOG.md`, and
   release-facing state/docs in one change.
2. Confirm every dependency version is published. In particular, the Factory
   extra must resolve its supported `flyto-blueprint` range from PyPI.
3. Run `python scripts/verify.py`, `python test_zapier_convert.py` when the
   sibling Pro checkout is available, and `python -m pip_audit`.
4. Push a clean `main` and wait for all required checks.

## Publish

Create a GitHub Release tagged exactly `v<project.version>`. The release
workflow repeats verification, builds fresh wheel/sdist artifacts, checks the
tag/version contract, and publishes through PyPI trusted publishing.

Configure PyPI once with the `flytohub/flyto-pro-core` repository, workflow
`publish-pypi.yml`, and environment `pypi`. No `PYPI_API_TOKEN` is used or
stored in GitHub.

## Post-release

Verify the PyPI project version, install the wheel into a clean environment,
check project URLs, and record the release in `STATE.md` and `CHANGELOG.md`.
Do not move or recreate a published tag.
