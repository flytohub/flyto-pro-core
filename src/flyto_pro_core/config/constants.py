"""
Application Constants

All magic numbers, default values, and thresholds are defined here.
These can be overridden by environment variables or configuration files.
"""

# ============================================
# Network Defaults
# ============================================
DEFAULT_API_PORT = 8000
DEFAULT_METRICS_PORT = 9002
DEFAULT_REDIS_PORT = 6379
DEFAULT_POSTGRES_PORT = 5432
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_OLLAMA_PORT = 11434
DEFAULT_QDRANT_URL = "http://localhost:6333"

# ============================================
# Timeout Configuration (in seconds)
# ============================================
TIMEOUT_CONFIG = {
    "default": 30,
    "api_call": 30,
    "database": 60,
    "file_upload": 60,
    "file_download": 60,
    "cloud_operation": 300,
    "llm_inference": 120,
    "embedding": 10,
    "redis": 5,
    "health_check": 5,
    "license_check": 10,
}

DEFAULT_TIMEOUT = TIMEOUT_CONFIG["default"]

# ============================================
# Retry Configuration
# ============================================
RETRY_CONFIG = {
    "default_max_retries": 3,
    "database_max_retries": 3,
    "redis_max_retries": 2,
    "api_max_retries": 3,
    "llm_max_retries": 2,
    "retry_delay_base": 1.0,
    "retry_delay_max": 30.0,
    "retry_exponential_base": 2.0,
}

DEFAULT_MAX_RETRIES = RETRY_CONFIG["default_max_retries"]

# ============================================
# Quality Thresholds
# ============================================
QUALITY_THRESHOLDS = {
    "min_quality_score": 8.0,
    "min_pr_score": 9.5,
    "min_module_quality": 8.0,
    "similarity_threshold": 0.8,
    "dedup_similarity": 0.99,
    "convergence_plateau": 0.1,
    "auto_escalate": 0.3,
    "human_guidance": 0.5,
    "auto_approve": 0.8,
}

# ============================================
# Agent Configuration
# ============================================
AGENT_CONFIG = {
    "max_iterations": 10,
    "max_refine_attempts": 5,
    "context_window": 4000,
    "max_tokens_per_request": 4096,
}

# ============================================
# Connection Pool Configuration
# ============================================
CONNECTION_POOL_CONFIG = {
    "max_connections": 100,
    "max_per_host": 10,
    "pool_timeout": 30,
    "min_pool_size": 2,
    "max_pool_size": 10,
}

# ============================================
# Cache Configuration
# ============================================
CACHE_CONFIG = {
    "default_ttl": 3600,
    "embedding_cache_ttl": 3600,
    "embedding_cache_max_size": 10000,
    "update_check_interval": 3600,
    "license_cache_ttl_hours": 24,
    "grace_period_days": 7,
}

# ============================================
# File Size Limits
# ============================================
FILE_SIZE_LIMITS = {
    "max_download_size": 50 * 1024 * 1024,  # 50 MB
    "max_upload_size": 100 * 1024 * 1024,  # 100 MB
    "max_chunk_size": 1024 * 1024,  # 1 MB
}

# ============================================
# Language Detection Thresholds
# ============================================
LANGUAGE_DETECTION = {
    "cjk_primary_threshold": 0.3,
    "cjk_secondary_threshold": 0.1,
    "latin_threshold": 0.3,
    "default_confidence": 0.3,
}

# ============================================
# Batch Processing
# ============================================
BATCH_CONFIG = {
    "default_batch_size": 50,
    "embedding_batch_size": 10,
    "max_concurrent_queries": 10,
    "max_concurrent_requests": 5,
}

# ============================================
# Scoring Weights
# ============================================
SCORING_WEIGHTS = {
    "success_rate_weight": 0.5,
    "recovery_rate_weight": 0.3,
    "quality_weight": 0.2,
}

# ============================================
# Memory Configuration
# ============================================
MEMORY_CONFIG = {
    "completed_jobs_retention_days": 7,
    "failed_jobs_retention_days": 30,
    "in_progress_timeout_days": 3,
    "max_messages_per_job": 500,
    "context_limit": 20,
    "compression_threshold": 100,
    "cleanup_interval_seconds": 86400,
}

# ============================================
# Training Configuration
# ============================================
TRAINING_CONFIG = {
    "default_interval_minutes": 60,
    "min_quality_for_extraction": 0.8,
    "error_log_ttl_days": 90,
}

# ============================================
# LLM Model Defaults
# ============================================
LLM_MODELS = {
    "openai_default": "gpt-4o-mini",
    "openai_fast": "gpt-4o-mini",  # For quick tasks
    "openai_smart": "gpt-4o",      # For complex tasks
    "openai_embedding": "text-embedding-3-small",
    "anthropic_default": "claude-3-5-sonnet-latest",
}


def get_llm_model(model_type: str = "openai_default") -> str:
    """
    Get LLM model name with environment variable override.

    Priority: ENV > constants

    Args:
        model_type: Key from LLM_MODELS dict

    Returns:
        Model name string

    Usage:
        model = get_llm_model("openai_default")  # Returns gpt-4o-mini or OPENAI_MODEL env
    """
    import os

    # Environment variable mapping
    env_map = {
        "openai_default": "OPENAI_MODEL",
        "openai_fast": "OPENAI_FAST_MODEL",
        "openai_smart": "OPENAI_SMART_MODEL",
        "openai_embedding": "OPENAI_EMBEDDING_MODEL",
        "anthropic_default": "ANTHROPIC_MODEL",
    }

    env_key = env_map.get(model_type)
    if env_key:
        env_value = os.getenv(env_key)
        if env_value:
            return env_value

    return LLM_MODELS.get(model_type, LLM_MODELS["openai_default"])

# ============================================
# Embedding Configuration
# ============================================
EMBEDDING_CONFIG = {
    "nomic_dimension": 768,
    "openai_dimension": 1536,
    "default_dimension": 768,
}

# ============================================
# Vector Database Configuration
# ============================================
VECTOR_DB_CONFIG = {
    "default_collection": "flyto2_memory",
    "knowledge_collection": "flyto2_knowledge",
    "distance_metric": "cosine",
}

# ============================================
# API Base URLs (for third-party services)
# ============================================
API_BASE_URLS = {
    "airtable": "https://api.airtable.com/v0",
    "notion": "https://api.notion.com/v1",
    "telegram": "https://api.telegram.org",
    "anthropic": "https://api.anthropic.com/v1",
    "openai": "https://api.openai.com/v1",
    "google_gemini": "https://generativelanguage.googleapis.com/v1",
    "twilio": "https://api.twilio.com/2010-04-01",
    "stripe": "https://api.stripe.com/v1",
}

# ============================================
# Conversation Limits
# ============================================
CONVERSATION_CONFIG = {
    "max_history_messages": 20,
    "max_short_term_memory": 10,
    "cost_estimate_per_query": 0.15,
}

# ============================================
# Circuit Breaker Defaults
# ============================================
CIRCUIT_BREAKER_CONFIG = {
    "failure_threshold": 5,
    "recovery_timeout": 30.0,
    "half_open_max_calls": 3,
    "success_threshold": 2,
}

# ============================================
# Text Processing
# ============================================
TEXT_PROCESSING_CONFIG = {
    "max_chunk_chars": 1500,
    "chunk_overlap": 100,
    "min_chunk_size": 100,
    "max_chunk_size": 2000,
}

# ============================================
# Scheduler Defaults
# ============================================
SCHEDULER_CONFIG = {
    "default_run_hour": 2,
    "max_concurrent_tasks": 2,
    "weekday_schedule": [0, 1, 2, 3, 4],  # Monday to Friday
}

# ============================================
# Scoring Router Configuration
# ============================================
SCORING_ROUTER_CONFIG = {
    "evidence_threshold": 30,       # Below this → COLLECT tier
    "evidence_strong_threshold": 55,  # Strong evidence threshold
    "difficulty_low_threshold": 40,  # Below this + low risk → QUICK_PATCH
    "difficulty_high_threshold": 70,  # Above this → SPEC_FIRST
    "risk_high_threshold": 70,       # Above this → SPEC_FIRST
    "risk_low_threshold": 40,        # Below this + low difficulty → QUICK_PATCH
    "intent_confidence_min": 50,     # Min intent score to be considered
    "pressure_to_multistep": 50,     # Pressure above this → MULTI_STEP
    "pressure_to_spec_first": 75,    # Pressure above this → SPEC_FIRST
}
