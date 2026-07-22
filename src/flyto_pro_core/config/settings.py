"""
Settings Management

Provides a centralized, type-safe configuration system using environment variables
and YAML configuration files. Implements the singleton pattern for efficiency.
"""

import os
from dataclasses import dataclass, field, fields, is_dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from .constants import (
    AGENT_CONFIG,
    CACHE_CONFIG,
    CONNECTION_POOL_CONFIG,
    DEFAULT_API_PORT,
    DEFAULT_OLLAMA_URL,
    DEFAULT_POSTGRES_PORT,
    DEFAULT_REDIS_PORT,
    QUALITY_THRESHOLDS,
    RETRY_CONFIG,
    TIMEOUT_CONFIG,
)


_ENV_FIELDS = {
    "database": {
        "host": "POSTGRES_HOST",
        "port": "POSTGRES_PORT",
        "database": "POSTGRES_DB",
        "user": "POSTGRES_USER",
        "password": "POSTGRES_PASSWORD",
        "ssl_mode": "POSTGRES_SSL_MODE",
    },
    "redis": {
        "host": "REDIS_HOST",
        "port": "REDIS_PORT",
        "password": "REDIS_PASSWORD",
        "db": "REDIS_DB",
    },
    "vector_db": {
        "url": "QDRANT_URL",
        "api_key": "QDRANT_API_KEY",
        "collection_name": "QDRANT_COLLECTION",
        "local_path": "QDRANT_PATH",
    },
    "ollama": {
        "url": "OLLAMA_URL",
        "model": "OLLAMA_MODEL",
        "embedding_model": "OLLAMA_EMBEDDING_MODEL",
    },
    "openai": {"api_key": "OPENAI_API_KEY", "model": "OPENAI_MODEL"},
    "anthropic": {
        "api_key": "ANTHROPIC_API_KEY",
        "model": "ANTHROPIC_MODEL",
    },
    "telegram": {
        "bot_token": "TELEGRAM_BOT_TOKEN",
        "allowed_users": "TELEGRAM_ALLOWED_USERS",
    },
    "api": {
        "host": "API_HOST",
        "port": "API_PORT",
        "debug": "API_DEBUG",
        "workers": "API_WORKERS",
    },
    "license": {
        "server_url": "LICENSE_SERVER_URL",
        "cache_dir": "LICENSE_CACHE_DIR",
    },
}
_ROOT_ENV_FIELDS = {"environment": "FLYTO_ENV", "debug": "DEBUG"}


def _get_env(key: str, default: Any = None, cast_type: type = str) -> Any:
    """Get environment variable with type casting."""
    value = os.getenv(key, default)
    if value is None:
        return None
    if cast_type is bool:
        return str(value).lower() in ("true", "1", "yes", "on")
    try:
        return cast_type(value)
    except (ValueError, TypeError):
        return default


def _coerce_yaml_value(value: Any, current: Any) -> Any:
    """Coerce a YAML scalar to the type of an existing setting value."""
    if isinstance(current, bool):
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes", "on")
    if current is None:
        return value
    try:
        return type(current)(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"invalid value {value!r} for {type(current).__name__}"
        ) from exc


@dataclass
class DatabaseSettings:
    """PostgreSQL database configuration."""

    host: str = field(default_factory=lambda: _get_env("POSTGRES_HOST", "localhost"))
    port: int = field(
        default_factory=lambda: _get_env("POSTGRES_PORT", DEFAULT_POSTGRES_PORT, int)
    )
    database: str = field(default_factory=lambda: _get_env("POSTGRES_DB", "flyto_jobs"))
    user: str = field(default_factory=lambda: _get_env("POSTGRES_USER", "postgres"))
    password: str = field(default_factory=lambda: _get_env("POSTGRES_PASSWORD", ""))
    ssl_mode: str = field(
        default_factory=lambda: _get_env("POSTGRES_SSL_MODE", "require")
    )
    pool_min_size: int = field(
        default_factory=lambda: CONNECTION_POOL_CONFIG["min_pool_size"]
    )
    pool_max_size: int = field(
        default_factory=lambda: CONNECTION_POOL_CONFIG["max_pool_size"]
    )
    timeout: int = field(default_factory=lambda: TIMEOUT_CONFIG["database"])
    max_retries: int = field(
        default_factory=lambda: RETRY_CONFIG["database_max_retries"]
    )

    @property
    def connection_string(self) -> str:
        """Generate PostgreSQL connection string."""
        return (
            f"postgresql://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}?sslmode={self.ssl_mode}"
        )


@dataclass
class RedisSettings:
    """Redis configuration."""

    host: str = field(default_factory=lambda: _get_env("REDIS_HOST", "localhost"))
    port: int = field(
        default_factory=lambda: _get_env("REDIS_PORT", DEFAULT_REDIS_PORT, int)
    )
    password: str = field(default_factory=lambda: _get_env("REDIS_PASSWORD", ""))
    db: int = field(default_factory=lambda: _get_env("REDIS_DB", 0, int))
    timeout: int = field(default_factory=lambda: TIMEOUT_CONFIG["redis"])
    max_retries: int = field(default_factory=lambda: RETRY_CONFIG["redis_max_retries"])


@dataclass
class VectorDBSettings:
    """Qdrant vector database configuration."""

    url: str = field(default_factory=lambda: _get_env("QDRANT_URL", ""))
    api_key: str = field(default_factory=lambda: _get_env("QDRANT_API_KEY", ""))
    collection_name: str = field(
        default_factory=lambda: _get_env("QDRANT_COLLECTION", "flyto_knowledge")
    )
    local_path: str = field(
        default_factory=lambda: _get_env("QDRANT_PATH", "./qdrant_storage")
    )
    vector_dimension: int = field(default_factory=lambda: 768)
    distance_metric: str = field(default_factory=lambda: "cosine")


@dataclass
class OllamaSettings:
    """Ollama LLM configuration."""

    url: str = field(default_factory=lambda: _get_env("OLLAMA_URL", DEFAULT_OLLAMA_URL))
    model: str = field(
        default_factory=lambda: _get_env("OLLAMA_MODEL", "llama3.2:latest")
    )
    embedding_model: str = field(
        default_factory=lambda: _get_env("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
    )
    timeout: int = field(default_factory=lambda: TIMEOUT_CONFIG["llm_inference"])
    max_retries: int = field(default_factory=lambda: RETRY_CONFIG["llm_max_retries"])


@dataclass
class OpenAISettings:
    """OpenAI API configuration."""

    api_key: str = field(default_factory=lambda: _get_env("OPENAI_API_KEY", ""))
    model: str = field(default_factory=lambda: _get_env("OPENAI_MODEL", "gpt-4o-mini"))
    timeout: int = field(default_factory=lambda: TIMEOUT_CONFIG["llm_inference"])
    max_tokens: int = field(
        default_factory=lambda: AGENT_CONFIG["max_tokens_per_request"]
    )


@dataclass
class AnthropicSettings:
    """Anthropic API configuration."""

    api_key: str = field(default_factory=lambda: _get_env("ANTHROPIC_API_KEY", ""))
    model: str = field(
        default_factory=lambda: _get_env("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
    )
    timeout: int = field(default_factory=lambda: TIMEOUT_CONFIG["llm_inference"])
    max_tokens: int = field(
        default_factory=lambda: AGENT_CONFIG["max_tokens_per_request"]
    )


@dataclass
class TelegramSettings:
    """Telegram bot configuration."""

    bot_token: str = field(default_factory=lambda: _get_env("TELEGRAM_BOT_TOKEN", ""))
    allowed_users: str = field(
        default_factory=lambda: _get_env("TELEGRAM_ALLOWED_USERS", "")
    )

    @property
    def allowed_user_ids(self) -> list[int]:
        """Parse allowed users into list of integers."""
        if not self.allowed_users:
            return []
        return [
            int(uid.strip()) for uid in self.allowed_users.split(",") if uid.strip()
        ]


@dataclass
class APISettings:
    """API server configuration."""

    host: str = field(default_factory=lambda: _get_env("API_HOST", "0.0.0.0"))
    port: int = field(
        default_factory=lambda: _get_env("API_PORT", DEFAULT_API_PORT, int)
    )
    debug: bool = field(default_factory=lambda: _get_env("API_DEBUG", False, bool))
    workers: int = field(default_factory=lambda: _get_env("API_WORKERS", 1, int))


@dataclass
class QualitySettings:
    """Quality thresholds and scoring configuration."""

    min_quality_score: float = field(
        default_factory=lambda: QUALITY_THRESHOLDS["min_quality_score"]
    )
    min_pr_score: float = field(
        default_factory=lambda: QUALITY_THRESHOLDS["min_pr_score"]
    )
    min_module_quality: float = field(
        default_factory=lambda: QUALITY_THRESHOLDS["min_module_quality"]
    )
    similarity_threshold: float = field(
        default_factory=lambda: QUALITY_THRESHOLDS["similarity_threshold"]
    )
    dedup_similarity: float = field(
        default_factory=lambda: QUALITY_THRESHOLDS["dedup_similarity"]
    )


@dataclass
class AgentSettings:
    """Agent behavior configuration."""

    max_iterations: int = field(default_factory=lambda: AGENT_CONFIG["max_iterations"])
    max_refine_attempts: int = field(
        default_factory=lambda: AGENT_CONFIG["max_refine_attempts"]
    )
    context_window: int = field(default_factory=lambda: AGENT_CONFIG["context_window"])


@dataclass
class LicenseSettings:
    """License server configuration."""

    server_url: str = field(
        default_factory=lambda: _get_env(
            "LICENSE_SERVER_URL", "https://license.flyto2.com/api/v1"
        )
    )
    timeout: int = field(default_factory=lambda: TIMEOUT_CONFIG["license_check"])
    cache_dir: str = field(
        default_factory=lambda: _get_env("LICENSE_CACHE_DIR", ".flyto2/license")
    )
    grace_days: int = field(default_factory=lambda: CACHE_CONFIG["grace_period_days"])
    cache_ttl_hours: int = field(
        default_factory=lambda: CACHE_CONFIG["license_cache_ttl_hours"]
    )


@dataclass
class Settings:
    """
    Main settings container.

    Aggregates all configuration settings into a single object.
    Use get_settings() to obtain a singleton instance.
    """

    database: DatabaseSettings = field(default_factory=DatabaseSettings)
    redis: RedisSettings = field(default_factory=RedisSettings)
    vector_db: VectorDBSettings = field(default_factory=VectorDBSettings)
    ollama: OllamaSettings = field(default_factory=OllamaSettings)
    openai: OpenAISettings = field(default_factory=OpenAISettings)
    anthropic: AnthropicSettings = field(default_factory=AnthropicSettings)
    telegram: TelegramSettings = field(default_factory=TelegramSettings)
    api: APISettings = field(default_factory=APISettings)
    quality: QualitySettings = field(default_factory=QualitySettings)
    agent: AgentSettings = field(default_factory=AgentSettings)
    license: LicenseSettings = field(default_factory=LicenseSettings)

    # Direct access to common timeout and retry values
    default_timeout: int = field(default_factory=lambda: TIMEOUT_CONFIG["default"])
    default_max_retries: int = field(
        default_factory=lambda: RETRY_CONFIG["default_max_retries"]
    )

    # Environment
    environment: str = field(
        default_factory=lambda: _get_env("FLYTO_ENV", "development")
    )
    debug: bool = field(default_factory=lambda: _get_env("DEBUG", False, bool))

    @classmethod
    def from_yaml(cls, config_path: Path) -> "Settings":
        """Load known settings from YAML, with environment values taking precedence."""
        settings = cls()
        if not config_path.exists():
            return settings

        yaml_config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(yaml_config, dict):
            raise ValueError("settings YAML must contain a mapping at the root")

        allowed_root = {item.name for item in fields(settings)}
        for section_name, section_value in yaml_config.items():
            if section_name not in allowed_root:
                raise ValueError(f"unknown settings section: {section_name}")

            current_section = getattr(settings, section_name)
            if is_dataclass(current_section):
                if not isinstance(section_value, dict):
                    raise ValueError(
                        f"settings section {section_name} must be a mapping"
                    )
                allowed_fields = {item.name for item in fields(current_section)}
                for key, value in section_value.items():
                    if key not in allowed_fields:
                        raise ValueError(f"unknown setting: {section_name}.{key}")
                    env_key = _ENV_FIELDS.get(section_name, {}).get(key)
                    if env_key and env_key in os.environ:
                        continue
                    current = getattr(current_section, key)
                    setattr(current_section, key, _coerce_yaml_value(value, current))
                continue

            env_key = _ROOT_ENV_FIELDS.get(section_name)
            if env_key and env_key in os.environ:
                continue
            setattr(
                settings,
                section_name,
                _coerce_yaml_value(section_value, current_section),
            )
        return settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get the singleton Settings instance.

    Loads environment variables from .env file if present,
    then creates and caches the Settings object.

    Returns:
        Settings: The application settings singleton.
    """
    # Load .env file if it exists
    env_file = Path(__file__).parent.parent.parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    return Settings()


def reload_settings() -> Settings:
    """
    Force reload of settings.

    Clears the cache and reloads environment variables.
    Use sparingly, mainly for testing.
    """
    get_settings.cache_clear()
    return get_settings()
