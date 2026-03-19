"""
Centralized Timeout Configuration

All timeout values should be defined here to:
1. Allow environment variable overrides
2. Provide consistent defaults
3. Make tuning for different deployments easy
"""
import os

# Timeout values in seconds
TIMEOUTS = {
    # HTTP/API timeouts
    "http_default": int(os.getenv("TIMEOUT_HTTP", "30")),
    "telegram_api": int(os.getenv("TIMEOUT_TELEGRAM", "10")),
    "github_api": int(os.getenv("TIMEOUT_GITHUB", "30")),
    "openai_api": int(os.getenv("TIMEOUT_OPENAI", "60")),
    "anthropic_api": int(os.getenv("TIMEOUT_ANTHROPIC", "120")),

    # Service timeouts
    "qdrant_request": int(os.getenv("TIMEOUT_QDRANT", "30")),
    "ollama_request": int(os.getenv("TIMEOUT_OLLAMA", "120")),

    # Infrastructure timeouts
    "docker_ready": int(os.getenv("TIMEOUT_DOCKER", "180")),
    "subprocess": int(os.getenv("TIMEOUT_SUBPROCESS", "60")),

    # Operation timeouts
    "file_operation": int(os.getenv("TIMEOUT_FILE", "30")),
    "git_operation": int(os.getenv("TIMEOUT_GIT", "60")),
}


def get_timeout(key: str, default: int = None) -> int:
    """
    Get timeout value by key.

    Args:
        key: Timeout key from TIMEOUTS dict
        default: Default value if key not found (defaults to http_default)

    Returns:
        Timeout value in seconds
    """
    if default is None:
        default = TIMEOUTS.get("http_default", 30)
    return TIMEOUTS.get(key, default)
