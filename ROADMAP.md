# Roadmap

## P0

- Preserve the package and execution boundaries in `ARCHITECTURE.md`.
- Keep generated API reference and feature ownership checks blocking in CI.
- Add direct behavioral tests for cost, provider-adapter, intervention,
  evidence-pipeline, and deterministic-verification surfaces before claiming
  production stability. Contract registry/schema and configuration coverage are
  now present.

## P1

- Resolve the 109 findings currently reported by mypy 2.3.0, then promote type
  checking from advisory to blocking without broad ignores.
- Publish explicit compatibility matrices for optional provider SDK versions;
  current package constraints already bound Flyto2 Core and Blueprint majors.

## P2

- Add runnable examples for custom providers and offline evidence pipelines.
- Add benchmark fixtures for large contract catalogs and verification plans.
