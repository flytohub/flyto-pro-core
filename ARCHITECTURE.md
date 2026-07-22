# Architecture

## Package Boundary

`flyto-pro-core` is a Python library, not a service. Importing it must not start
network listeners or create hosted resources. Network access only occurs when a
caller instantiates and invokes an optional provider.

```text
workflow input
    |
    v
contract models -> registry -> validator -> binding resolver -> compiler
    |                                                       |
    +-------------------- executable plan ------------------+

agent plan -> observations -> deterministic verifier -> evidence/report
    |               |                 |
    +-> project state/EMS     intervention and UI contracts

recipe -> blueprint selection -> deterministic composition -> validation
```

## Source Areas

| Area | Responsibility | Dependency direction |
|---|---|---|
| `contract` | Typed workflow/module contracts, catalog lookup, validation, bindings, compilation | May load `flyto-core` metadata at runtime; remains usable with explicit contracts |
| `agent_runtime` | Versioned plan/execution contracts, observation, evidence, verification, state, EMS, intervention, UI data | Depends on local models and caller-provided adapters |
| `cost` | Pricing lookup and multi-resource budget enforcement | Reads pricing overrides from environment |
| `interfaces` | Abstract ports and optional OpenAI/Qdrant/local-file implementations | Optional SDKs are imported only for their providers |
| `factory` | Recipe resolution, blueprint selection, conversion, enrichment, autofix, and pipeline orchestration | Requires the `factory` optional dependency set for full use |
| `core` | Service container, guarded access, and validation helpers | Shared leaf utilities |
| `config` | Environment-backed dataclasses, constants, and timeout lookup | No application-specific global state beyond cached settings |

## Stability Rules

- Public imports are the symbols exported by package `__init__.py` files plus
  documented public provider classes.
- Contract schema versions are independent of the Python package version.
- `flyto-core` executes workflows; this package validates or composes them and
  must not duplicate engine execution behavior.
- Hosted authentication, tenants, queues, databases, billing, and deployment
  belong to `flyto-cloud`, not this library.
- Optional providers require caller-owned credentials and preserve the abstract
  interface contracts in `src/flyto_pro_core/interfaces/`.

## Generated Reference

`scripts/generate-api-reference.py` parses the Python AST and writes
`docs/reference/python-api.md`. CI runs it with `--check`, so adding or changing
a public class, function, or method requires a matching generated reference.
