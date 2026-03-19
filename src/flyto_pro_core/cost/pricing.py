"""
Model Pricing

Pricing configuration for LLM models.
All values from environment or dynamic config - no hardcoding.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ModelPricing:
    """Pricing for a single model."""
    model_id: str
    prompt_cost_per_1k: float  # USD per 1K prompt tokens
    completion_cost_per_1k: float  # USD per 1K completion tokens
    context_window: int = 128000
    max_output: int = 4096

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost for given token counts."""
        prompt_cost = (prompt_tokens / 1000) * self.prompt_cost_per_1k
        completion_cost = (completion_tokens / 1000) * self.completion_cost_per_1k
        return prompt_cost + completion_cost


# Default pricing loaded from environment
_pricing_cache: Dict[str, ModelPricing] = {}


def _load_pricing_from_env() -> Dict[str, ModelPricing]:
    """Load pricing from environment variable."""
    global _pricing_cache

    if _pricing_cache:
        return _pricing_cache

    # Try to load from JSON env var
    pricing_json = os.getenv("LLM_PRICING_CONFIG")
    if pricing_json:
        try:
            config = json.loads(pricing_json)
            for model_id, values in config.items():
                _pricing_cache[model_id] = ModelPricing(
                    model_id=model_id,
                    prompt_cost_per_1k=values.get("prompt", 0.0),
                    completion_cost_per_1k=values.get("completion", 0.0),
                    context_window=values.get("context_window", 128000),
                    max_output=values.get("max_output", 4096),
                )
            return _pricing_cache
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM_PRICING_CONFIG: {e}")

    # Fallback: load from individual env vars
    # Format: LLM_PRICING_<MODEL>_PROMPT, LLM_PRICING_<MODEL>_COMPLETION
    default_models = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "claude-3-5-sonnet-20241022",
        "claude-3-haiku-20240307",
    ]

    for model in default_models:
        env_key = model.upper().replace("-", "_").replace(".", "_")
        prompt = os.getenv(f"LLM_PRICING_{env_key}_PROMPT")
        completion = os.getenv(f"LLM_PRICING_{env_key}_COMPLETION")

        if prompt and completion:
            _pricing_cache[model] = ModelPricing(
                model_id=model,
                prompt_cost_per_1k=float(prompt),
                completion_cost_per_1k=float(completion),
            )

    # If still empty, use conservative defaults from env or zeros
    if not _pricing_cache:
        default_prompt = float(os.getenv("LLM_DEFAULT_PROMPT_COST", "0.01"))
        default_completion = float(os.getenv("LLM_DEFAULT_COMPLETION_COST", "0.03"))

        _pricing_cache["default"] = ModelPricing(
            model_id="default",
            prompt_cost_per_1k=default_prompt,
            completion_cost_per_1k=default_completion,
        )

    return _pricing_cache


def get_model_pricing(model_id: str) -> ModelPricing:
    """Get pricing for a specific model."""
    pricing = _load_pricing_from_env()

    # Try exact match
    if model_id in pricing:
        return pricing[model_id]

    # Try partial match
    for key, value in pricing.items():
        if key in model_id or model_id in key:
            return value

    # Return default
    if "default" in pricing:
        return pricing["default"]

    # Ultimate fallback
    return ModelPricing(
        model_id=model_id,
        prompt_cost_per_1k=0.01,
        completion_cost_per_1k=0.03,
    )


def get_model_cost(
    model_id: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Calculate cost for a model call."""
    pricing = get_model_pricing(model_id)
    return pricing.calculate_cost(prompt_tokens, completion_tokens)


def estimate_cost(
    model_id: str,
    estimated_prompt_tokens: int,
    estimated_completion_tokens: int,
) -> Dict[str, Any]:
    """Estimate cost before making a call."""
    pricing = get_model_pricing(model_id)
    estimated_cost = pricing.calculate_cost(
        estimated_prompt_tokens,
        estimated_completion_tokens,
    )

    return {
        "model_id": model_id,
        "estimated_prompt_tokens": estimated_prompt_tokens,
        "estimated_completion_tokens": estimated_completion_tokens,
        "estimated_cost_usd": estimated_cost,
        "pricing": {
            "prompt_per_1k": pricing.prompt_cost_per_1k,
            "completion_per_1k": pricing.completion_cost_per_1k,
        },
    }


def reload_pricing() -> None:
    """Reload pricing from environment (for config updates)."""
    global _pricing_cache
    _pricing_cache = {}
    _load_pricing_from_env()
