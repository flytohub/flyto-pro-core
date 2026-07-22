# Claude Code notes

`flyto-pro-core` participates in: cloud_apps_automation, security, zero_person_agent.

Start with:

1. `PROJECT.md`
2. `ARCHITECTURE.md`
3. `STATE.md`
4. `DECISIONS.md`
5. `/Users/chester/flytohub/CODEX_HANDOFF_FLYTO_AUDIT.md`

Never infer or reuse credentials from repository files or handoffs.

Before editing, refresh the local index with `flyto-index scan .` and inspect
affected symbols with `flyto-index impact` or `flyto-index context`. After
editing, run the full `python scripts/verify.py` gate. Do not report completion
from lint alone: tests, generated references, package artifacts, example drift,
and strict Indexer verification are required.

## Flyto2 Project Memory Contract

Every Flyto2 repository must keep this project-memory scaffold current:

- `AGENTS.md`: agent operating rules, repo-specific constraints, verification commands.
- `CLAUDE.md`: Claude-facing handoff rules when this repo is edited outside Codex.
- `PROJECT.md`: product purpose, owned surfaces, users, and non-goals.
- `ARCHITECTURE.md`: module boundaries, runtime shape, data flow, and integration points.
- `STATE.md`: current status, known risks, release/deploy state, and last verification.
- `ROADMAP.md`: near-term, later, and explicitly out-of-scope work.
- `tasks.md`: actionable checklist with owners/status when known.
- `DECISIONS.md`: durable architectural/product decisions with dates and rationale.
- `CHANGELOG.md`: user-visible or operator-visible changes.
- `docs/README.md`: index for durable docs in this repo.
- `workflows/*.md`: repeatable agent workflows for idea capture, planning, implementation, bugfix, refactor, investigation, and wrap-up.
- `handoffs/_registry.md`: index of handoffs; new handoffs use `YYYY-MM-DD-topic.md`.

When changing behavior, public copy, deployment, security posture, or frontend UX, update the relevant memory files in the same change. Do not leave stale brand, email, module count, route, or deployment information behind.

## Flyto2 Frontend Quality Gate

Any frontend, website, dashboard, extension webview, app screen, or generated UI in this repository must avoid these eight failures:

1. Ignoring accessibility: every interactive control needs keyboard access, visible focus, semantic HTML or ARIA, sufficient contrast, and useful alt/labels.
2. Missing responsive design: verify mobile, tablet, and desktop; no clipped text, overflow, hidden primary actions, or broken navigation.
3. Weak visual hierarchy: users must immediately see page purpose, primary action, status, and next step.
4. Template-looking UI: reuse Flyto2 design tokens and local components, but tailor layout and copy to the actual product surface.
5. Useless elements: remove decorative or placeholder UI that does not help the workflow, trust, navigation, or comprehension.
6. Unclear hierarchy: controls, cards, tables, panels, and modals must have clear grouping, spacing, headings, and state.
7. Unintuitive navigation: current location, back/forward paths, and cross-links to docs/blog/product pages must be obvious.
8. Hard-to-understand content: copy must be concrete, scannable, current, and consistent with Flyto2 terminology.

Frontend verification must include the relevant automated checks plus manual or screenshot review for responsive layout, accessibility states, navigation clarity, loading/empty/error states, and content readability. Public pages must preserve SEO basics: canonical URL, sitemap coverage, metadata, structured data when relevant, and no broken internal or external links.
