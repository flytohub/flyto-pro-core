# Changelog

## Unreleased

## [0.1.3] - 2026-08-03

### Fixed

- Made Ruff release validation deterministic by explicitly retaining the
  pre-0.16 default rule families after Ruff 0.16 expanded its defaults.

### Changed

- Replaced generic project and architecture pages with package-specific
  boundaries, feature ownership, configuration, and verification guidance.
- Aligned the exported package version with `pyproject.toml` and restored a
  clean Ruff gate for the test suite.
- Prepared a metadata-only PyPI patch release so live registry backlinks,
  Flyto2 project URLs, and issue links are exposed from PyPI.
- Corrected the supported Python baseline to 3.10 because the current Blueprint
  dependency does not publish Python 3.9-compatible distributions.
- Made Factory selection fail closed for unsupported requests and rerank
  catalog candidates using the original request terms and browser intent.
- Replaced stale QR/string/foreach examples with workflows supported by the
  current Flyto2 Blueprint catalog.
- Made Factory enrichment reproducible: IDs derive from content, descriptions
  and explicit edges are preserved, and labels remain human-readable.
- Made YAML settings effective, reject unknown sections and fields, coerce
  values, and preserve environment-variable precedence.
- Normalized Flyto2 Core parameter metadata, including `any`, `null`, UI type
  aliases, union types, nested schemas, sensitivity, grouping, and ordering.
- Moved blocking file and hash work out of async event-loop paths.
- Converted historical root scripts into deterministic offline examples and
  opt-in local integration checks that do not read sibling credentials.

### Added

- Added a generated public Python API reference with a CI freshness check.
- Added feature, configuration, documentation-contract, and contribution docs.
- Added project memory files, workflow docs, and handoff registry.
- Added generated documentation for 72 environment variables and a secret-free
  `.env.example`.
- Added domain guides for contracts, agent runtime, cost control, providers,
  Factory, release operations, and the technical whitepaper.
- Added source-area ownership pages across every substantive package directory.
- Added contract registry, parameter schema, and configuration tests; the suite
  now contains 46 focused tests.
- Added a one-command verification runner covering lint, tests, generated
  artifacts, deterministic examples, build contents, installed-wheel imports,
  and strict Flyto2 Indexer checks.
- Added a documentation structure gate for manifest targets and local Markdown
  links.
- Added a pinned-action CI matrix and a PyPI Trusted Publishing workflow that
  requires a version-matching published GitHub release.
- Installed mypy in development/CI environments so the advisory typing job
  reports real findings instead of failing because the checker is absent.
