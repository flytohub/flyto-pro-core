# Maintenance Scripts

- `generate-api-reference.py` parses every public Python class, function, and
  method. It fails when a public symbol has no docstring.
- `generate-config-reference.py` owns the environment-variable catalog and
  generates both `.env.example` and `docs/reference/environment.md`.
- `check-documentation.py` validates manifest targets and local Markdown links.
- `verify.py` runs the local lint, tests, generated-file checks, package build,
  artifact inspection, and Indexer gate used by CI.

Generated reference files are committed. Run scripts with `--check` in review
and regenerate only when the corresponding source contract changes.
