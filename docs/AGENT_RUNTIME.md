# Deterministic Agent Runtime

## Lifecycle

```text
proposal -> accepted plan -> capability check -> execution observation
        -> raw evidence -> derived evidence -> assertion results -> report
        -> project state / intervention / verified fix pattern
```

The package owns the data and deterministic checks in this lifecycle. A caller
owns planning intelligence, worker scheduling, module execution, authentication,
tenancy, and user-interface rendering.

## Contracts And Capabilities

`PlanContract` groups assertions, observations, and stop conditions.
`CapabilityToken` limits permitted scopes and `CapabilityGuard` evaluates an
operation against the token. `ExecutionBundle` records the plan, environment
fingerprint, inputs, outputs, and replay conditions. Proposals and decision
cards keep revisions, feedback, priority, status, options, context, and user
decisions serializable.

## Observation And Evidence

Observation packets can contain browser state, database table summaries,
filesystem changes, requests/responses, step traces, and module I/O. Raw
evidence stores original bytes or paths plus a SHA-256 digest and retention
policy. Derived evidence records the reproducible transformation and compact
result used by verification.

Callers must redact cookies, local storage, headers, file previews, database
rows, and provider payloads before persistence or model access. This library
does not infer which fields are customer secrets.

## Verification

`AssertionExecutor` evaluates supported assertion types against an
`ExecutionContext`. `DeterministicVerifier` collects evidence in assertion order
and returns a `VerificationReport` containing hard/soft outcomes, confidence,
and failure analysis. Sequential evaluation is intentional because assertions
may refer to ordered execution evidence; it is not a database query loop.

## State, Intervention, EMS, And UI

- Project types model goals, tasks, steps, checklists, artifacts, and `.flyto/`
  storage.
- Intervention types model blocking/non-blocking requests and responses.
- EMS types normalize failures and rank only verified repair patterns.
- UI types expose progress, task operations, risk, and translated decisions as
  transport-neutral data.

The complete symbol-level contract is in the
[generated Python API](reference/python-api.md).
