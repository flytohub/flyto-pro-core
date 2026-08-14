# State

Current as of 2026-08-14.

- Governed coding jobs create an isolated Python environment, install the
  pinned project/development contract, and run the complete verification suite
  through `.flyto/coding.yaml` before independent Codex audit.

- Status: active open-source Python library.
- Package metadata version: `0.1.3`.
- Published PyPI version: `0.1.3`, released through GitHub Actions and PyPI
  Trusted Publishing with wheel and sdist artifacts. The v0.1.2 GitHub release
  remains unpublished on PyPI because Ruff 0.16 expanded its default rules and
  stopped verification before build or upload; v0.1.3 supersedes that failed
  attempt.
- Public API inventory: 923 public Python classes, functions, and methods,
  generated into `docs/reference/python-api.md`; generation fails when a public
  callable lacks a docstring.
- Runtime contract inventory: 430 contracts in the audited workspace (427 from
  Flyto2 Core plus three local overrides). Counts are discovered at runtime and
  are not presented as a permanent product promise.
- Configuration inventory: 72 documented environment variables with generated
  `.env.example` and reference documentation.
- Automated tests: 46 focused tests covering Factory behavior, deterministic
  enrichment, current Blueprint compatibility, settings precedence, registry
  loading, parameter aliases, union types, and metadata round trips.
- Offline integration contracts: 45 deterministic Factory scenarios and 100
  sibling `flyto-pro` seed conversions.
- CI: Ruff, generated-reference drift checks, pytest on Python
  3.10/3.11/3.12/3.13, build and installed-wheel smoke tests, strict Flyto2
  Indexer verification, dependency audit, security/SBOM, branding, and
  documentation-contract checks.
- Ruff validation explicitly selects the pre-0.16 default rule families, so
  release results do not change when Ruff expands its implicit defaults.
- Latest local closed loop: `python scripts/verify.py` passed all 46 tests with
  Flyto2 Indexer 18/18, documentation score 100, and no secret or taint
  findings; the release lint command also passed under Ruff 0.16.1.
- Clean Python 3.11 installation resolved the public PyPI Blueprint/Core
  dependencies, passed all tests and `pip check`, and reported no known
  dependency vulnerabilities after upgrading the CI build toolchain.

The package version exported by `flyto_pro_core.__version__` now matches
`pyproject.toml`. Contract payload defaults such as `1.0.0` remain schema
versions and are intentionally independent.

Behavioral coverage is still concentrated on Factory, configuration, and the
Core contract adapter. Cost enforcement, provider adapters, interventions,
evidence pipelines, and the complete deterministic verifier require broader
direct tests before the package can claim production stability.

Mypy remains advisory: mypy 2.3.0 currently reports 109 errors across 21 source
files, primarily implicit optional annotations, mutable container variance, and
optional integration members. CI installs and runs mypy so this debt remains
visible; it is not yet a blocking release gate.
