# Cost And Budget Control

## Budget Dimensions

`BudgetConfig` limits estimated USD cost, tokens, tool calls, LLM calls,
iterations, runtime seconds, and the warning threshold. Construct it directly,
from a caller-selected environment prefix, or from the `free`, `pro`, and
`enterprise` compatibility tiers.

`CostController` records usage, emits threshold warnings once per resource,
reports remaining capacity, answers affordability checks, and raises
`BudgetExceededError` when a configured limit is reached.

## Pricing

`ModelPricing` stores prompt/completion cost per 1,000 tokens and calculates one
call estimate. Pricing is loaded in this order:

1. `LLM_PRICING_CONFIG` JSON map.
2. Per-model `LLM_PRICING_<MODEL>_PROMPT` and `_COMPLETION` pairs.
3. `LLM_DEFAULT_PROMPT_COST` and `LLM_DEFAULT_COMPLETION_COST`.

`reload_pricing()` clears the in-process cache after configuration changes.
These values are estimates for admission control and reporting; the external
provider invoice remains authoritative.

## Configuration

All supported variables and dynamic naming rules are in the generated
[environment reference](reference/environment.md). Invalid numeric environment
values raise during configuration construction so a malformed budget is not
silently accepted.
