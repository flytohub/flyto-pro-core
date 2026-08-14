# Decisions

## 2026-08-14 - Library changes use the governed coding route

Decision: keep isolated environment creation, project installation, and the
complete `scripts/verify.py` suite in `.flyto/coding.yaml`. Public package copy
and contract behavior require an independent Codex audit after that gate.

Reason: this library validates workflows, evidence, and budgets but does not
execute them. A committed verifier protects that boundary and the built package
from drifting together.

## 2026-06-21 - Project memory bootstrapped

Decision: track Flyto2 product-line role, repo boundary, state, roadmap, tasks,
and handoffs in this repo.

Reason: `flyto-pro-core` must be maintainable by future agents without relying on
conversation memory.

## 2026-07-22 - Generated contracts are release gates

Decision: generate the public Python API and environment-variable references
from source-owned catalogs, and fail verification when generated files drift or
a public callable lacks a docstring.

Reason: a large contract library cannot keep method-level documentation current
through manual prose review alone.

## 2026-07-22 - Factory generation is deterministic and fails closed

Decision: derive generated IDs from stable content, preserve caller-provided
edges and descriptions, and reject requests when the installed Blueprint
catalog cannot support every selected intent.

Reason: hidden time/random inputs break reproducibility, while substituting an
unrelated blueprint creates a valid-looking but incorrect workflow.

## 2026-07-22 - Normalize upstream parameter metadata at the boundary

Decision: accept the type aliases and union forms emitted by current Flyto2 Core
metadata, normalize them into `ParamType` plus `allowed_types`, and preserve
nested/UI metadata through serialization.

Reason: rejecting valid upstream forms silently reduced a 427-module catalog to
a partial registry and made validation disagree with the execution engine.

## 2026-07-22 - Environment values override validated YAML

Decision: `Settings.from_yaml()` accepts only known sections and fields,
coerces scalar types, applies YAML values, and then preserves explicit
environment-variable precedence.

Reason: the previous method parsed YAML but returned default settings, which
made configuration files appear supported while having no effect.

## 2026-07-22 - Package publishing uses GitHub release plus PyPI OIDC

Decision: publish only from a published GitHub release whose tag matches the
package version, using PyPI Trusted Publishing and immutable action revisions.

Reason: this removes long-lived repository tokens and prevents a mismatched tag
from publishing the wrong artifact.
