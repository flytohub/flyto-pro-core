# Feature Reference

This page maps shipped behavior to its source, public interface, configuration,
and current test evidence. The complete symbol-level inventory is in the
[generated Python API reference](reference/python-api.md).

## Contract Engine

`flyto_pro_core.contract` models module ports, parameter schemas, workflow nodes,
edges, execution results, and control-flow contracts. `ContractRegistry` owns
catalog lookup and compatibility checks. `WorkflowValidator` returns structured
errors and warnings, `BindingResolver` resolves available expressions, and
`WorkflowCompiler` produces an `ExecutablePlan`. `ContractEngine` is the
facade combining those operations.

This layer validates and compiles; it does not execute a workflow. Contract
payload versions are schema versions, not the package release number.

Detailed lifecycle, type normalization, and failure semantics:
[Contract engine](CONTRACT_ENGINE.md).

## Cost And Budget Control

`CostController` records LLM tokens, estimated model cost, tool calls, and agent
iterations. It can reject work through `BudgetExceededError`, report remaining
budgets, and answer affordability checks. `BudgetConfig.from_env()` and
`BudgetConfig.for_tier()` construct limits. Pricing helpers calculate token cost
and support environment overrides.

Pricing order and budget semantics: [Cost control](COST_CONTROL.md).

## Provider And Storage Interfaces

Abstract interfaces cover chat/streaming LLMs, embeddings, files, vector stores,
quality checks, and code analysis. `LocalFileRepository` is the local file
implementation. OpenAI and Qdrant adapters are optional and require their named
extras plus caller-supplied credentials. Provider calls can create billable
external traffic; importing the package does not.

Provider implementation and data-handling rules: [Providers](PROVIDERS.md).

## Deterministic Agent Runtime

The runtime is split into explicit subdomains:

| Subdomain | Behavior |
|---|---|
| Contracts | Versioned plans, assertions, stop policy, capability tokens, execution bundles, proposals, and decision cards |
| Observation | Structured browser, database, filesystem, network, runtime, step, and module-I/O snapshots |
| Verification | Assertion execution, raw/derived evidence, deterministic reports, confidence, and failure analysis |
| Project | Goal/task/step state plus `.flyto/` directories, artifacts, logs, bundles, and cleanup |
| Intervention | Typed blocking or non-blocking requests, decision-card builders, callbacks, and console handling |
| EMS | Normalized error signatures, verified fix patterns, matching, lifecycle, statistics, and persistence |
| UI contracts | Progress events, task operations, risk cards, and technical-language translation |
| Integration | Adapters for existing agent loops, observations, and verification-gate formats |

These are library contracts. A caller owns scheduling, authentication,
persistence location, and any user interface that renders the data.

Lifecycle, evidence, and trust boundaries: [Agent runtime](AGENT_RUNTIME.md).

## Factory Pipeline

Factory turns a natural-language request into a workflow through recipe
resolution, direct-term Blueprint selection, deterministic
conversion/enrichment, autofix, and validation. An optional LLM selects only
known Blueprint IDs; wiring and layout remain deterministic. Unsupported
requests fail instead of returning an unrelated low-confidence recipe. Install
`flyto-pro-core[factory]` for the complete dependency set.

See [Factory](FACTORY.md) for the exact pipeline, compatibility range,
historical `validator` argument, and offline/live verification assets.

## Core Utilities

`ServiceContainer` provides singleton, transient, and factory registrations.
Safe-access functions convert missing list, mapping, attribute, response, and
result paths into caller-selected defaults or explicit errors. `Validator`
offers fluent type, range, length, pattern, membership, and predicate checks,
with standalone validation and numeric-conversion helpers.

## Configuration

Typed settings cover PostgreSQL, Redis, Qdrant, Ollama, OpenAI, Anthropic,
Telegram, API, quality, agent, and license behavior. Constants define retry,
timeout, pool, cache, file-size, batching, scoring, memory, model, embedding,
vector, conversation, circuit-breaker, text-processing, and scheduler defaults.

See [Configuration](CONFIGURATION.md) before enabling an external provider.

## Verification Boundary

Run from the repository root:

```bash
python -m ruff check src/ tests/ scripts/
python -m pytest
python scripts/generate-api-reference.py --check
python scripts/generate-config-reference.py --check
python -m build
```

Passing these checks proves lint, local behavior, API/config reference
freshness, and package construction. The generated API check requires a
docstring for all 923 public classes, functions, and methods. It does not prove
live OpenAI, Qdrant, Redis, PostgreSQL, Telegram, or license-server connectivity
because those require caller-owned services and credentials.

The system rationale and threat model are in the
[technical whitepaper](WHITEPAPER.md).
