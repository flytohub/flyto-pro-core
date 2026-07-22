# Flyto2 Pro Core Technical Whitepaper

## Abstract

AI automation systems fail when model output, runtime authority, validation,
evidence, and cost policy are collapsed into one opaque loop. Flyto2 Pro Core
separates those concerns into portable contracts and deterministic gates. The
package provides an Apache-2.0 boundary between caller-selected intelligence and
the Flyto2 execution ecosystem.

## Design Principles

1. **Plans are data.** Versioned plan, proposal, stop, capability, observation,
   and decision contracts can be reviewed before work begins.
2. **Generation is not execution.** Factory composes candidate workflows;
   Flyto2 Core remains the execution and sandbox boundary.
3. **Verification is evidence based.** Raw evidence is retained separately from
   compact deterministic derivations and assertion results.
4. **Authority is explicit.** Capability tokens and interventions describe what
   may proceed and when a human or host application must decide.
5. **Cost is a resource limit.** Estimated money, tokens, calls, iterations, and
   runtime are checked before an unbounded loop develops.
6. **Providers are replaceable.** Interfaces isolate external models, vectors,
   files, and quality systems from domain contracts.

## Architecture

```text
caller / planner
    | plan + capability + budget
    v
agent contracts ---- project state ---- intervention/UI data
    |                         |
    v                         v
observations -> evidence -> deterministic verification report

workflow request -> Factory -> WorkflowSpec -> Contract Engine -> ExecutablePlan
                                                        |
                                                        v
                                        Flyto2 Core execution boundary
```

## Trust Boundaries

- Environment variables, YAML, workflow parameters, model output, Blueprint
  metadata, filesystem paths, browser state, and provider responses are inputs.
- The package validates known shapes but does not authenticate users, authorize
  tenants, isolate processes, or guarantee network destinations.
- Provider credentials remain outside source control and are blank in generated
  examples.
- Evidence may contain sensitive application state; callers own redaction,
  encryption, access control, retention, and deletion.
- A `PipelineResult(ok=True)` is not proof of safe or successful execution.

## Determinism And Reproducibility

Composition, argument wiring, graph validation, cost arithmetic, evidence
hashing, and assertion evaluation are deterministic for the same catalog and
inputs. `EnvironmentFingerprint`, schema versions, committed generated
references, package artifact checks, and exact dependency ranges make drift
observable. External provider output and live-system state remain explicitly
nondeterministic.

## Failure Model

Expected workflow defects become structured validation issues. Budget exhaustion
raises a typed exception. Unsupported Factory intents fail closed. Incompatible
Blueprint versions return a diagnostic error. Malformed configuration is
rejected. Optional service absence is visible through imports or availability
checks. CI verifies source, tests, generated docs/config, package contents,
dependencies, branding, secrets, and the Indexer closed loop.

## Scope

This package is not a hosted control plane, workflow runner, scheduler, billing
system, identity provider, secret manager, or commercial feature bundle. Those
responsibilities stay in their owning Flyto2 repositories or the embedding
application.
