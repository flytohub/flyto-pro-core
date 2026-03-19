"""
Centralized Configuration System for Flyto Pro

This module provides a unified configuration management system that:
- Loads configuration from environment variables and YAML files
- Provides type-safe access to configuration values
- Supports multiple environments (development, staging, production)
- Enables dependency injection for all services
"""

from .settings import Settings, get_settings, reload_settings
from .constants import (
    # Network defaults
    DEFAULT_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_API_PORT,
    DEFAULT_METRICS_PORT,
    DEFAULT_OLLAMA_URL,
    DEFAULT_OLLAMA_PORT,
    DEFAULT_REDIS_PORT,
    DEFAULT_POSTGRES_PORT,
    # Configuration dictionaries
    TIMEOUT_CONFIG,
    RETRY_CONFIG,
    QUALITY_THRESHOLDS,
    AGENT_CONFIG,
    CONNECTION_POOL_CONFIG,
    CACHE_CONFIG,
    FILE_SIZE_LIMITS,
    LANGUAGE_DETECTION,
    BATCH_CONFIG,
    SCORING_WEIGHTS,
    MEMORY_CONFIG,
    TRAINING_CONFIG,
    LLM_MODELS,
    EMBEDDING_CONFIG,
    VECTOR_DB_CONFIG,
    API_BASE_URLS,
    CONVERSATION_CONFIG,
    CIRCUIT_BREAKER_CONFIG,
    TEXT_PROCESSING_CONFIG,
    SCHEDULER_CONFIG,
)

__all__ = [
    # Settings
    "Settings",
    "get_settings",
    "reload_settings",
    # Network defaults
    "DEFAULT_TIMEOUT",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_API_PORT",
    "DEFAULT_METRICS_PORT",
    "DEFAULT_OLLAMA_URL",
    "DEFAULT_OLLAMA_PORT",
    "DEFAULT_REDIS_PORT",
    "DEFAULT_POSTGRES_PORT",
    # Configuration dictionaries
    "TIMEOUT_CONFIG",
    "RETRY_CONFIG",
    "QUALITY_THRESHOLDS",
    "AGENT_CONFIG",
    "CONNECTION_POOL_CONFIG",
    "CACHE_CONFIG",
    "FILE_SIZE_LIMITS",
    "LANGUAGE_DETECTION",
    "BATCH_CONFIG",
    "SCORING_WEIGHTS",
    "MEMORY_CONFIG",
    "TRAINING_CONFIG",
    "LLM_MODELS",
    "EMBEDDING_CONFIG",
    "VECTOR_DB_CONFIG",
    "API_BASE_URLS",
    "CONVERSATION_CONFIG",
    "CIRCUIT_BREAKER_CONFIG",
    "TEXT_PROCESSING_CONFIG",
    "SCHEDULER_CONFIG",
]
