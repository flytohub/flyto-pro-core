# Contract Engine

## Purpose

The contract engine turns Flyto2 Core module metadata and a `WorkflowSpec` into
structured diagnostics or an `ExecutablePlan`. It is a validation and
compilation layer. It does not invoke modules, schedule jobs, or persist hosted
state.

## Data Model

- `DataContract` and `DataType` describe values and compatibility.
- `Port` combines direction, edge type, shape, cardinality, and restrictions.
- `ParamDef` and `ParamsSchema` validate user-supplied module parameters.
- `ModuleContract` combines ports, parameters, output, policy, version, tier,
  deprecation, and examples.
- `NodeSpec`, `EdgeSpec`, and `WorkflowSpec` represent a workflow graph.
- `ExecutionResult`, `ScopeData`, and `ExecutionTrace` describe runtime output
  without owning execution.

Flyto2 Core aliases such as `text`, `json`, `password`, `any`, and union type
lists are normalized when metadata enters `ParamsSchema`. Unknown types degrade
to `any` with a warning rather than dropping an entire module contract.

## Processing Flow

1. `ContractRegistry.initialize()` loads Flyto2 Core metadata.
2. JSON files under `contract/overrides/` replace or add local contracts.
3. `WorkflowValidator.validate()` checks graph, module, parameter, binding,
   port, entry-node, orphan, and connection rules.
4. `BindingResolver` enumerates parameters, upstream outputs, scopes, and loop
   values and resolves a requested expression.
5. `WorkflowCompiler.compile()` produces ordered `CompiledNode` values,
   `PortBinding` values, routing rules, and an `ExecutablePlan`.

## Failure Semantics

Validation returns `ValidationReport`; expected user errors are not exceptions.
Compilation raises `CompilationError` when an executable plan cannot be formed.
Individual malformed Flyto2 Core metadata entries are logged and skipped, while
the integration test requires the current catalog to remain above the audited
minimum and checks representative alias/union modules.

## Public API

Use `ContractEngine` for the facade and lower-level classes when building custom
tooling. Every class and method signature is listed in the
[generated Python API](reference/python-api.md).
