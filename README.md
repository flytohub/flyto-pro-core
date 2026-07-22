# Flyto2 Pro Core

[![PyPI](https://img.shields.io/pypi/v/flyto-pro-core.svg)](https://pypi.org/project/flyto-pro-core/)
[![Python](https://img.shields.io/pypi/pyversions/flyto-pro-core.svg)](https://pypi.org/project/flyto-pro-core/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Website](https://img.shields.io/badge/website-flyto2.com-8B5CF6)](https://flyto2.com)

Open-source foundation for [Flyto2](https://flyto2.com) commercial-grade
automation: workflow contract validation, deterministic agent runtime, budget
and token metering, provider interfaces, project state, and evidence-backed
verification.

Use Flyto2 Pro Core when you need bring-your-own LLM providers, Qdrant/OpenAI
integrations, budget enforcement, deterministic workflow validation, or a clean
boundary between Apache-2.0 runtime primitives and private enterprise modules.

Official links: [flyto2.com](https://flyto2.com) ·
[Docs](https://docs.flyto2.com) ·
[Flyto2 Core](https://github.com/flytohub/flyto-core) ·
[Flyto2 Indexer](https://github.com/flytohub/flyto-indexer) ·
[Security](mailto:security@flyto2.com)

## What's Inside

| Module | Purpose | Reference |
|--------|---------|-----------|
| `contract` | Workflow models, validation, binding resolution, registry, and compilation | [Contract engine](docs/FEATURES.md#contract-engine) |
| `cost` | Cost, token, tool-call, and iteration budgets | [Cost control](docs/FEATURES.md#cost-and-budget-control) |
| `interfaces` | LLM, embedding, storage, vector, and quality ports plus optional providers | [Provider interfaces](docs/FEATURES.md#provider-and-storage-interfaces) |
| `agent_runtime` | Contracts, evidence, observations, project state, intervention, EMS, and UI data | [Agent runtime](docs/FEATURES.md#deterministic-agent-runtime) |
| `factory` | Recipe selection and deterministic workflow composition | [Factory pipeline](docs/FEATURES.md#factory-pipeline) |
| `core` | Dependency injection, safe access, and validation helpers | [Core utilities](docs/FEATURES.md#core-utilities) |
| `config` | Environment-backed settings, constants, and timeouts | [Configuration](docs/CONFIGURATION.md) |

## Install

```bash
pip install flyto-pro-core
```

With optional providers:

```bash
pip install flyto-pro-core[openai]    # OpenAI LLM + embeddings
pip install flyto-pro-core[qdrant]    # Qdrant vector store
pip install flyto-pro-core[core]      # Flyto2 Core module catalog
pip install flyto-pro-core[factory]   # Blueprint composition + OpenAI fallback
pip install flyto-pro-core[full]      # All providers
```

## Usage

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

### Factory - Compose A Workflow

```python
from flyto_blueprint import BlueprintEngine
from flyto_blueprint.storage.memory import MemoryBackend
from flyto_pro_core.factory import generate_v2

blueprints = BlueprintEngine(storage=MemoryBackend())
result = await generate_v2(
    "Fetch an API and save it to a file",
    blueprint_engine=blueprints,
)
if result.ok:
    print(result.steps)
else:
    print(result.error)
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

## Relationship to Flyto2 Ecosystem

```
flyto-pro-core (open source)     flyto-pro (proprietary)
├── contract                      ├── ems (error learning)
├── cost                          ├── evolution (module generation)
├── interfaces                    ├── knowledge (semantic search)
├── agent_runtime                 ├── agent (AI agent core)
├── core                          ├── guardian (safety)
└── config                        └── enterprise runtime extensions
         │                                    │
         └────────── flyto-ai ────────────────┘
                  (open source)
                  ProBridge connects both layers
```

- **Free users**: `flyto-ai` + `flyto-pro-core` = full contract validation, cost control, agent runtime
- **Pro users**: + `flyto-pro` = EMS error learning, module evolution, semantic knowledge search

## Requirements

- Python 3.10+
- `pydantic >= 2.0.0`
- `pyyaml >= 6.0`

Optional:
- `openai >= 1.0.0` (for OpenAI provider)
- `qdrant-client >= 1.7.0` (for Qdrant provider)
- `flyto-core >= 2.26.9, < 3` (for contract catalog loading)
- `flyto-blueprint >= 0.2.1, < 0.3` (for Factory composition)

## API Reference

The [generated Python API reference](docs/reference/python-api.md) inventories
all 923 public classes, functions, and methods with signatures, purposes, and
source links. Domain guides explain contracts and operational boundaries:
[contract engine](docs/CONTRACT_ENGINE.md),
[agent runtime](docs/AGENT_RUNTIME.md),
[cost control](docs/COST_CONTROL.md),
[providers](docs/PROVIDERS.md), and [Factory](docs/FACTORY.md).

## Configuration

Start with [Configuration](docs/CONFIGURATION.md) and the generated
[environment reference](docs/reference/environment.md). `.env.example` contains
safe examples for every literal environment-variable read; credentials remain
blank.

## Testing

```bash
python -m pytest
python -m ruff check .
python scripts/generate-api-reference.py --check
python scripts/generate-config-reference.py --check
python scripts/check-documentation.py
python -m build
```

The verification boundary and optional live-service exclusions are mapped in
[Features](docs/FEATURES.md) and [Testing](tests/README.md).

## Contributing

Pull requests are welcome for contract validation, budget controls, provider
interfaces, deterministic verification, docs, and examples. Security reports
should go to `security@flyto2.com`.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
