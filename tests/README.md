# Test Map

| File | Contract |
|---|---|
| `test_factory.py` | Recipe models, selection, conversion, autofix, and composition units |
| `test_factory_integration.py` | Current Blueprint catalog to enriched workflow behavior |
| `test_factory_output.py` | Representative wiring and output-shape regressions |
| `test_settings.py` | YAML shape, coercion, and environment precedence |
| `test_params_schema.py` | Flyto2 Core type aliases, unions, sensitive fields, and round trips |
| `test_contract_registry.py` | Current Flyto2 Core catalog compatibility |

The default suite is offline. Live OpenAI, Qdrant, PostgreSQL, Redis, Telegram,
and local-engine behavior is excluded because it requires caller-owned services
or credentials. Run `python test_closed_loop.py` only against a trusted local
Flyto2 Core endpoint.
