# Project

`flyto-pro-core` is the Apache-2.0 Python foundation for advanced Flyto2
automation. It owns reusable workflow-contract, cost-control, provider,
deterministic-agent, project-state, evidence, and Factory primitives.

It does not own the `flyto-core` execution engine, cloud APIs, hosted state,
commercial-only implementations, or end-user web interfaces. Those systems may
depend on this package through its documented Python contracts.

## Audiences

- Python integrators embedding Flyto2 contracts or agent-runtime primitives
- provider authors implementing LLM, embedding, storage, or quality interfaces
- Flyto2 maintainers composing open and commercial layers
- contributors extending deterministic validation and Factory behavior

## Release Surface

- Package: `flyto-pro-core` on PyPI
- Source package: `src/flyto_pro_core/`
- Supported Python: 3.10 and newer
- License: Apache-2.0
- Current package metadata version: `0.1.2`
