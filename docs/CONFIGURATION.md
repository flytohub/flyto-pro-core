# Configuration

`get_settings()` creates and caches the typed settings object. It loads a root
`.env` file when present; process environment values take precedence. Call
`reload_settings()` after changing environment values in a running process.

`Settings.from_yaml(path)` accepts the same root sections as the `Settings`
dataclass. Known YAML values are applied first and matching process environment
variables win. Unknown sections or fields fail closed with `ValueError` so a
misspelled production setting is not silently ignored.

## Environment Variables

The generated [environment reference](reference/environment.md) lists all 72
runtime and integration-script variables, safe examples, defaults, dynamic
prefix rules, and secret classifications. `.env.example` is generated from the
same catalog.

Empty credentials disable or make the corresponding provider unavailable. Do
not commit `.env` files, API keys, bot tokens, database passwords, or Qdrant
keys. Use repository/environment secrets in CI and deployment systems.

## Optional Dependencies

| Extra | Enables |
|---|---|
| `openai` | OpenAI chat, streaming, and embedding adapters |
| `qdrant` | Qdrant vector-store adapter |
| `blueprint` | Flyto2 Blueprint contracts used by Factory |
| `integration` | `aiohttp` for the opt-in local closed-loop script |
| `factory` | Blueprint and OpenAI dependencies for the Factory pipeline |
| `full` | OpenAI, Qdrant, and Blueprint integrations |
| `dev` | Pytest, pytest-asyncio, and Ruff |

Provider credentials are read at runtime and remain the caller's responsibility.
The package does not provision external services.

Run `python scripts/generate-config-reference.py --check` after changing any
environment read. The check extracts literal reads from source and fails if a
new variable is absent from the catalog.
