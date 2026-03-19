# flyto-pro-core

Open-source foundation for [Flyto](https://flyto.io) — workflow validation, cost control, agent runtime, and provider interfaces.

## What's Inside

| Module | Purpose | Lines |
|--------|---------|-------|
| `contract` | Workflow validation, binding resolution, compilation | 4.9K |
| `cost` | Multi-resource budget management (cost, tokens, tool calls, iterations) | 1.3K |
| `interfaces` | Abstract LLM, vector store, quality checker + OpenAI/Qdrant providers | 1.8K |
| `agent_runtime` | Deterministic verification, observations, project state management | 11.9K |
| `core` | DI container, safe access utilities, validators | 1.5K |
| `config` | Settings, constants, timeouts | 1K |

## Install

```bash
pip install flyto-pro-core
```

With optional providers:

```bash
pip install flyto-pro-core[openai]    # OpenAI LLM + embeddings
pip install flyto-pro-core[qdrant]    # Qdrant vector store
pip install flyto-pro-core[full]      # All providers
```

## Quick Start

### Contract Engine — Validate Workflows

```python
from flyto_pro_core.contract.engine import ContractEngine

engine = ContractEngine()
await engine.initialize()  # loads module catalog from flyto-core

report = await engine.validate_workflow(spec)
if not report.valid:
    for issue in report.issues:
        print(f"  {issue.severity}: {issue.message}")

# Binding resolution
bindings = await engine.get_available_bindings(spec, "node_3")

# Compile to execution plan
plan = await engine.compile(spec)
```

### Cost Controller — Budget Management

```python
from flyto_pro_core.cost.controller import CostController, BudgetConfig

# Per-tier budgets
controller = CostController(budget=BudgetConfig.for_tier("pro"))

# Record usage
controller.record_llm_usage("gpt-4o", prompt_tokens=1000, completion_tokens=500)
controller.record_tool_call()

# Check budget (raises BudgetExceededError if over)
controller.check_budget()

# Summary
print(controller.get_summary())
# {"cost_spent_usd": 0.025, "cost_budget_usd": 1.0, "tokens_used": 1500, ...}
```

### Interfaces — Bring Your Own Provider

```python
from flyto_pro_core.interfaces.llm import ILLMService, LLMResponse
from flyto_pro_core.interfaces.storage import IVectorStoreRepository

# Use built-in OpenAI provider
from flyto_pro_core.interfaces.providers.openai_llm import OpenAILLMService
llm = OpenAILLMService(model="gpt-4o")
response = await llm.generate("Hello")

# Or implement your own
class MyLLM(ILLMService):
    async def generate(self, prompt, **kwargs) -> LLMResponse:
        ...
```

### Agent Runtime — Verification & Project State

```python
from flyto_pro_core.agent_runtime.verification import DeterministicVerifier
from flyto_pro_core.agent_runtime.project import ProjectStateManager

# Deterministic verification (no LLM needed)
verifier = DeterministicVerifier()
report = await verifier.verify(assertions, evidence)

# Project state management
state = ProjectStateManager(project_dir="/path/to/project")
await state.initialize()
```

### DI Container

```python
from flyto_pro_core.core.container import container

# Register services
container.register("llm", my_llm_instance)
container.register_factory("vector_store", lambda: QdrantVectorStore())

# Retrieve
llm = container.get("llm")
```

## Architecture

```
flyto-pro-core (this package, Apache-2.0)
├── contract/        → WorkflowSpec → ValidationReport → ExecutablePlan
├── cost/            → BudgetConfig → CostController → BudgetExceededError
├── interfaces/      → ILLMService / IVectorStoreRepository / IQualityChecker
│   └── providers/   → OpenAILLMService, QdrantVectorStore (built-in)
├── agent_runtime/   → Verification, Observations, ProjectState, Interventions
├── core/            → ServiceContainer, safe_access, validators
└── config/          → Settings, constants
```

## Relationship to Flyto Ecosystem

```
flyto-pro-core (open source)     flyto-pro (proprietary)
├── contract                      ├── ems (error learning)
├── cost                          ├── evolution (module generation)
├── interfaces                    ├── knowledge (semantic search)
├── agent_runtime                 ├── agent (AI agent core)
├── core                          ├── guardian (safety)
└── config                        └── 50+ enterprise modules
         │                                    │
         └────────── flyto-ai ────────────────┘
                  (open source)
                  ProBridge connects both layers
```

- **Free users**: `flyto-ai` + `flyto-pro-core` = full contract validation, cost control, agent runtime
- **Pro users**: + `flyto-pro` = EMS error learning, module evolution, semantic knowledge search

## Requirements

- Python 3.9+
- `pydantic >= 2.0.0`
- `pyyaml >= 6.0`

Optional:
- `openai >= 1.0.0` (for OpenAI provider)
- `qdrant-client >= 1.7.0` (for Qdrant provider)
- `flyto-core >= 1.5.3` (for contract catalog loading)

## License

Apache License 2.0 — see [LICENSE](LICENSE).
