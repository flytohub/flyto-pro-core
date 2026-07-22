# Contributing

Contributions should stay within the package boundary in
[ARCHITECTURE.md](ARCHITECTURE.md). Add or update tests for behavioral changes
and update [docs/FEATURES.md](docs/FEATURES.md) when a feature surface changes.

From the repository root:

```bash
python -m pip install -e '.[dev,full]'
python -m ruff check src/ tests/ scripts/
python -m pytest
python scripts/generate-api-reference.py
python scripts/generate-api-reference.py --check
python scripts/generate-config-reference.py --check
```

The generated API reference must be committed with public Python API changes.
Use placeholders in examples and send security reports privately to
`security@flyto2.com`.
