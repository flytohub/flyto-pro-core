#!/usr/bin/env python3
"""Generate and validate the environment-variable contract."""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_OUTPUT = ROOT / ".env.example"
DOC_OUTPUT = ROOT / "docs" / "reference" / "environment.md"


@dataclass(frozen=True)
class Variable:
    """One documented environment variable and its safe example value."""

    category: str
    name: str
    default: str
    description: str
    secret: bool = False


VARIABLES = [
    Variable("Runtime", "FLYTO_ENV", "development", "Runtime environment label."),
    Variable("Runtime", "DEBUG", "false", "Enable debug behavior."),
    Variable("PostgreSQL", "POSTGRES_HOST", "localhost", "Database host."),
    Variable("PostgreSQL", "POSTGRES_PORT", "5432", "Database port."),
    Variable("PostgreSQL", "POSTGRES_DB", "flyto_jobs", "Database name."),
    Variable("PostgreSQL", "POSTGRES_USER", "postgres", "Database user."),
    Variable("PostgreSQL", "POSTGRES_PASSWORD", "", "Database password.", True),
    Variable("PostgreSQL", "POSTGRES_SSL_MODE", "require", "PostgreSQL SSL mode."),
    Variable("Redis", "REDIS_HOST", "localhost", "Redis host."),
    Variable("Redis", "REDIS_PORT", "6379", "Redis port."),
    Variable("Redis", "REDIS_PASSWORD", "", "Redis password.", True),
    Variable("Redis", "REDIS_DB", "0", "Redis database number."),
    Variable(
        "Qdrant", "QDRANT_URL", "", "Remote Qdrant URL; blank keeps it unavailable."
    ),
    Variable("Qdrant", "QDRANT_API_KEY", "", "Qdrant API key.", True),
    Variable("Qdrant", "QDRANT_COLLECTION", "flyto_knowledge", "Default collection."),
    Variable("Qdrant", "QDRANT_PATH", "./qdrant_storage", "Local Qdrant path."),
    Variable("Ollama", "OLLAMA_URL", "http://localhost:11434", "Ollama base URL."),
    Variable("Ollama", "OLLAMA_MODEL", "llama3.2:latest", "Chat model."),
    Variable(
        "Ollama", "OLLAMA_EMBEDDING_MODEL", "nomic-embed-text", "Embedding model."
    ),
    Variable("OpenAI", "OPENAI_API_KEY", "", "OpenAI API key.", True),
    Variable("OpenAI", "OPENAI_MODEL", "gpt-4o-mini", "Default OpenAI model."),
    Variable("OpenAI", "OPENAI_FAST_MODEL", "gpt-4o-mini", "Fast-task model override."),
    Variable("OpenAI", "OPENAI_SMART_MODEL", "gpt-4o", "Complex-task model override."),
    Variable(
        "OpenAI",
        "OPENAI_EMBEDDING_MODEL",
        "text-embedding-3-small",
        "Embedding model override.",
    ),
    Variable("Anthropic", "ANTHROPIC_API_KEY", "", "Anthropic API key.", True),
    Variable(
        "Anthropic", "ANTHROPIC_MODEL", "claude-3-5-sonnet-latest", "Anthropic model."
    ),
    Variable("Telegram", "TELEGRAM_BOT_TOKEN", "", "Telegram bot token.", True),
    Variable(
        "Telegram", "TELEGRAM_ALLOWED_USERS", "", "Comma-separated numeric user IDs."
    ),
    Variable("API", "API_HOST", "0.0.0.0", "API bind host."),
    Variable("API", "API_PORT", "8000", "API bind port."),
    Variable("API", "API_WORKERS", "1", "API worker count."),
    Variable("API", "API_DEBUG", "false", "Enable API debug behavior."),
    Variable(
        "License",
        "LICENSE_SERVER_URL",
        "https://license.flyto2.com/api/v1",
        "License service URL.",
    ),
    Variable(
        "License",
        "LICENSE_CACHE_DIR",
        ".flyto2/license",
        "Local license-cache directory.",
    ),
    Variable("Timeouts", "TIMEOUT_HTTP", "30", "Default HTTP timeout in seconds."),
    Variable("Timeouts", "TIMEOUT_TELEGRAM", "10", "Telegram timeout in seconds."),
    Variable("Timeouts", "TIMEOUT_GITHUB", "30", "GitHub timeout in seconds."),
    Variable("Timeouts", "TIMEOUT_OPENAI", "60", "OpenAI timeout in seconds."),
    Variable("Timeouts", "TIMEOUT_ANTHROPIC", "120", "Anthropic timeout in seconds."),
    Variable("Timeouts", "TIMEOUT_QDRANT", "30", "Qdrant timeout in seconds."),
    Variable("Timeouts", "TIMEOUT_OLLAMA", "120", "Ollama timeout in seconds."),
    Variable(
        "Timeouts", "TIMEOUT_DOCKER", "180", "Docker readiness timeout in seconds."
    ),
    Variable("Timeouts", "TIMEOUT_SUBPROCESS", "60", "Subprocess timeout in seconds."),
    Variable("Timeouts", "TIMEOUT_FILE", "30", "File-operation timeout in seconds."),
    Variable("Timeouts", "TIMEOUT_GIT", "60", "Git-operation timeout in seconds."),
    Variable(
        "Agent budget",
        "AGENT_BUDGET_MAX_COST_USD",
        "1.0",
        "Maximum estimated USD cost.",
    ),
    Variable(
        "Agent budget", "AGENT_BUDGET_MAX_TOKENS", "100000", "Maximum token count."
    ),
    Variable(
        "Agent budget", "AGENT_BUDGET_MAX_TOOL_CALLS", "50", "Maximum tool calls."
    ),
    Variable("Agent budget", "AGENT_BUDGET_MAX_LLM_CALLS", "30", "Maximum LLM calls."),
    Variable(
        "Agent budget", "AGENT_BUDGET_MAX_ITERATIONS", "20", "Maximum agent iterations."
    ),
    Variable(
        "Agent budget",
        "AGENT_BUDGET_MAX_RUNTIME_SECONDS",
        "300",
        "Maximum runtime in seconds.",
    ),
    Variable(
        "Agent budget",
        "AGENT_BUDGET_WARNING_THRESHOLD",
        "0.8",
        "Fraction that triggers warnings.",
    ),
    Variable("Tier budgets", "BUDGET_FREE_MAX_COST", "0.1", "Free-tier USD limit."),
    Variable(
        "Tier budgets", "BUDGET_FREE_MAX_TOKENS", "10000", "Free-tier token limit."
    ),
    Variable(
        "Tier budgets", "BUDGET_FREE_MAX_TOOLS", "10", "Free-tier tool-call limit."
    ),
    Variable("Tier budgets", "BUDGET_FREE_MAX_LLM", "5", "Free-tier LLM-call limit."),
    Variable("Tier budgets", "BUDGET_FREE_MAX_ITER", "5", "Free-tier iteration limit."),
    Variable("Tier budgets", "BUDGET_PRO_MAX_COST", "1.0", "Pro-tier USD limit."),
    Variable(
        "Tier budgets", "BUDGET_PRO_MAX_TOKENS", "100000", "Pro-tier token limit."
    ),
    Variable("Tier budgets", "BUDGET_PRO_MAX_TOOLS", "50", "Pro-tier tool-call limit."),
    Variable("Tier budgets", "BUDGET_PRO_MAX_LLM", "30", "Pro-tier LLM-call limit."),
    Variable("Tier budgets", "BUDGET_PRO_MAX_ITER", "20", "Pro-tier iteration limit."),
    Variable(
        "Tier budgets",
        "BUDGET_ENTERPRISE_MAX_COST",
        "10.0",
        "Enterprise-tier USD limit.",
    ),
    Variable(
        "Tier budgets",
        "BUDGET_ENTERPRISE_MAX_TOKENS",
        "500000",
        "Enterprise-tier token limit.",
    ),
    Variable(
        "Tier budgets",
        "BUDGET_ENTERPRISE_MAX_TOOLS",
        "200",
        "Enterprise-tier tool-call limit.",
    ),
    Variable(
        "Tier budgets",
        "BUDGET_ENTERPRISE_MAX_LLM",
        "100",
        "Enterprise-tier LLM-call limit.",
    ),
    Variable(
        "Tier budgets",
        "BUDGET_ENTERPRISE_MAX_ITER",
        "50",
        "Enterprise-tier iteration limit.",
    ),
    Variable("Pricing", "LLM_PRICING_CONFIG", "", "JSON model-pricing map."),
    Variable(
        "Pricing",
        "LLM_DEFAULT_PROMPT_COST",
        "0.01",
        "Fallback prompt cost per 1K tokens.",
    ),
    Variable(
        "Pricing",
        "LLM_DEFAULT_COMPLETION_COST",
        "0.03",
        "Fallback completion cost per 1K tokens.",
    ),
    Variable(
        "Integration scripts",
        "FLYTO_API_BASE",
        "https://localhost:3000",
        "Local engine URL used by test_closed_loop.py.",
    ),
    Variable(
        "Integration scripts",
        "FLYTO_PRO_REPO",
        "../flyto-pro",
        "Seed-bank checkout used by test_zapier_convert.py.",
    ),
]


def referenced_variables() -> set[str]:
    """Extract literal environment-variable reads from Python source and scripts."""
    referenced = set()
    paths = [*ROOT.joinpath("src").rglob("*.py"), *ROOT.glob("*.py")]
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            function_name = ""
            if isinstance(node.func, ast.Name):
                function_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                function_name = node.func.attr
            first = node.args[0]
            if (
                function_name in {"getenv", "_get_env", "get"}
                and isinstance(first, ast.Constant)
                and isinstance(first.value, str)
                and first.value.isupper()
            ):
                referenced.add(first.value)
    return referenced


def render_env() -> str:
    """Render a secret-free dotenv example grouped by subsystem."""
    lines = [
        "# Flyto2 Pro Core configuration example.",
        "# Copy only the values your integration uses; never commit real secrets.",
    ]
    current_category = None
    for variable in VARIABLES:
        if variable.category != current_category:
            current_category = variable.category
            lines.extend(["", f"# {current_category}"])
        suffix = " (secret; leave blank in source control)" if variable.secret else ""
        lines.append(f"# {variable.description}{suffix}")
        lines.append(f"{variable.name}={variable.default}")
    return "\n".join(lines).rstrip() + "\n"


def render_docs() -> str:
    """Render the human-readable environment reference."""
    lines = [
        "# Environment Reference",
        "",
        "> Generated by `python scripts/generate-config-reference.py`. Do not edit manually.",
        "",
        "Unset variables use the defaults shown below. Secret values are deliberately blank",
        "in `.env.example`; provide them through the caller's secret manager.",
        "",
        "| Area | Variable | Default/example | Secret | Purpose |",
        "|---|---|---|---|---|",
    ]
    for variable in VARIABLES:
        default = variable.default.replace("|", "\\|") or "_(blank)_"
        description = variable.description.replace("|", "\\|")
        lines.append(
            f"| {variable.category} | `{variable.name}` | `{default}` | "
            f"{'yes' if variable.secret else 'no'} | {description} |"
        )
    lines.extend(
        [
            "",
            "## Dynamic Names",
            "",
            "`BudgetConfig.from_env(prefix)` reads the seven `AGENT_BUDGET_*` suffixes",
            "shown above under any caller-supplied prefix. Pricing also accepts",
            "`LLM_PRICING_<NORMALIZED_MODEL>_PROMPT` and",
            "`LLM_PRICING_<NORMALIZED_MODEL>_COMPLETION`; prefer",
            "`LLM_PRICING_CONFIG` when configuring several models.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    """Write generated files or verify they and the source references agree."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    catalog = {variable.name for variable in VARIABLES}
    missing = sorted(referenced_variables() - catalog)
    if missing:
        print(
            f"undocumented environment variables: {', '.join(missing)}", file=sys.stderr
        )
        return 1

    outputs = {ENV_OUTPUT: render_env(), DOC_OUTPUT: render_docs()}
    if args.check:
        stale = [
            path.relative_to(ROOT).as_posix()
            for path, content in outputs.items()
            if not path.exists() or path.read_text(encoding="utf-8") != content
        ]
        if stale:
            print(
                f"stale generated configuration files: {', '.join(stale)}",
                file=sys.stderr,
            )
            return 1
        print(f"configuration contract passed: {len(VARIABLES)} variables")
        return 0

    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
