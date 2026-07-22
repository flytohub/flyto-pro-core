# Factory Pipeline

## Contract

Factory composes workflows from the currently installed `flyto-blueprint`
catalog. Install `flyto-pro-core[factory]`; supported versions are
`flyto-blueprint>=0.2.1,<0.3`.

```text
description
  -> split intents
  -> Blueprint search
  -> original-word relevance and browser-intent filtering
  -> dependency ordering / deduplication
  -> argument placeholders and cross-step wiring
  -> Blueprint composition
  -> reference normalization / optional stringify insertion
  -> built-in module and reference validation
  -> PipelineResult
```

Unsupported intent returns `RecipeResult(ok=False)` rather than an unrelated
low-confidence recipe. An optional LLM can select valid catalog IDs after the
deterministic selector fails, but wiring and validation stay deterministic.

## Public Operations

- `select_blueprints()` chooses catalog IDs without an LLM.
- `resolve_recipe()` asks an LLM for a constrained JSON list of known IDs.
- `modules_to_workflow()` converts an explicit module list.
- `generate_v2()` orchestrates selection, composition, and built-in validation.
- `enrich_template()` adds flow start, positions, canvas edges, and UI fields.
- `autofix_workflow()` repairs recognized module/reference/default errors.

`generate_v2(..., validator=...)` retains the historical argument for API
compatibility but does not invoke it. A successful result proves only built-in
module/reference checks; validate with Flyto2 Core before execution.

## Verification Assets

- `generate_real.py` deterministically refreshes committed YAML examples.
- `test_stress.py` repeats supported and unsupported catalog contracts.
- `test_zapier_convert.py` converts all 100 sibling Flyto2 Pro seed workflows.
- `test_closed_loop.py` is opt-in and calls a trusted local engine endpoint.

No script loads sibling `.env` files or prints credentials.
