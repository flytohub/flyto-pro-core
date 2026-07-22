# GitHub Workflows

- `ci.yml` runs lint, generated contracts, Python 3.10/3.11/3.12/3.13 tests,
  artifact verification, strict Indexer checks, and dependency audit.
- `documentation.yml` enforces the shared Flyto2 documentation contract.
- `security.yml` runs reusable secret/dependency/SBOM security workflows.
- `branding-guard.yml` rejects non-canonical public domains.
- `publish-pypi.yml` verifies a `v<version>` GitHub Release and publishes with
  PyPI trusted publishing (OIDC), without a repository API token.

Third-party actions and Flyto2 reusable workflows are pinned to immutable
commits. Updating a pin requires reviewing the upstream change first.
