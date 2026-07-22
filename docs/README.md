# Documentation

## Use The Library

- [Feature reference](FEATURES.md): shipped capabilities and ownership
- [Technical whitepaper](WHITEPAPER.md): rationale, architecture, trust, and failure model
- [Contract engine](CONTRACT_ENGINE.md): metadata, validation, bindings, and compilation
- [Agent runtime](AGENT_RUNTIME.md): plans, observations, evidence, verification, and state
- [Cost control](COST_CONTROL.md): budgets and model-pricing estimates
- [Providers](PROVIDERS.md): interface and external-service boundaries
- [Factory](FACTORY.md): deterministic Blueprint composition pipeline
- [Configuration](CONFIGURATION.md): environment variables and optional services
- [Environment reference](reference/environment.md): generated variable catalog
- [Python API](reference/python-api.md): generated public classes, functions,
  methods, signatures, and source links
- [README](../README.md): installation and first use
- [Security](../SECURITY.md): supported reporting channel

## Maintain The Project

- [Project boundary](../PROJECT.md)
- [Architecture](../ARCHITECTURE.md)
- [Current state](../STATE.md)
- [Roadmap](../ROADMAP.md)
- [Decisions](../DECISIONS.md)
- [Tasks](../tasks.md)
- [Changelog](../CHANGELOG.md)
- [Contributing](../CONTRIBUTING.md)
- [Release runbook](RELEASE.md)

`reference/python-api.md` is generated. Update it with
`python scripts/generate-api-reference.py`; do not edit it manually.
