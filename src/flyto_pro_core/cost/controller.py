"""
Cost Controller

Budget management and cost tracking for Agent executions.
All limits from environment or config - no hardcoding.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .pricing import get_model_cost

logger = logging.getLogger(__name__)


class BudgetExceededError(Exception):
    """Raised when execution budget is exceeded."""

    def __init__(
        self,
        message: str,
        spent: float,
        budget: float,
        resource_type: str = "cost",
    ):
        super().__init__(message)
        self.spent = spent
        self.budget = budget
        self.resource_type = resource_type


@dataclass
class UsageRecord:
    """Record of resource usage."""
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    timestamp: float


@dataclass
class BudgetConfig:
    """Budget configuration for an execution."""
    max_cost_usd: float = 1.0
    max_tokens: int = 100000
    max_tool_calls: int = 50
    max_llm_calls: int = 30
    max_iterations: int = 20
    max_runtime_seconds: int = 300
    warning_threshold: float = 0.8  # Warn at 80% of budget

    @classmethod
    def from_env(cls, prefix: str = "AGENT_BUDGET") -> BudgetConfig:
        """Load budget config from environment."""
        return cls(
            max_cost_usd=float(os.getenv(f"{prefix}_MAX_COST_USD", "1.0")),
            max_tokens=int(os.getenv(f"{prefix}_MAX_TOKENS", "100000")),
            max_tool_calls=int(os.getenv(f"{prefix}_MAX_TOOL_CALLS", "50")),
            max_llm_calls=int(os.getenv(f"{prefix}_MAX_LLM_CALLS", "30")),
            max_iterations=int(os.getenv(f"{prefix}_MAX_ITERATIONS", "20")),
            max_runtime_seconds=int(os.getenv(f"{prefix}_MAX_RUNTIME_SECONDS", "300")),
            warning_threshold=float(os.getenv(f"{prefix}_WARNING_THRESHOLD", "0.8")),
        )

    @classmethod
    def for_tier(cls, tier: str) -> BudgetConfig:
        """Get budget config for a license tier."""
        tier_configs = {
            "free": cls(
                max_cost_usd=float(os.getenv("BUDGET_FREE_MAX_COST", "0.1")),
                max_tokens=int(os.getenv("BUDGET_FREE_MAX_TOKENS", "10000")),
                max_tool_calls=int(os.getenv("BUDGET_FREE_MAX_TOOLS", "10")),
                max_llm_calls=int(os.getenv("BUDGET_FREE_MAX_LLM", "5")),
                max_iterations=int(os.getenv("BUDGET_FREE_MAX_ITER", "5")),
            ),
            "pro": cls(
                max_cost_usd=float(os.getenv("BUDGET_PRO_MAX_COST", "1.0")),
                max_tokens=int(os.getenv("BUDGET_PRO_MAX_TOKENS", "100000")),
                max_tool_calls=int(os.getenv("BUDGET_PRO_MAX_TOOLS", "50")),
                max_llm_calls=int(os.getenv("BUDGET_PRO_MAX_LLM", "30")),
                max_iterations=int(os.getenv("BUDGET_PRO_MAX_ITER", "20")),
            ),
            "enterprise": cls(
                max_cost_usd=float(os.getenv("BUDGET_ENTERPRISE_MAX_COST", "10.0")),
                max_tokens=int(os.getenv("BUDGET_ENTERPRISE_MAX_TOKENS", "500000")),
                max_tool_calls=int(os.getenv("BUDGET_ENTERPRISE_MAX_TOOLS", "200")),
                max_llm_calls=int(os.getenv("BUDGET_ENTERPRISE_MAX_LLM", "100")),
                max_iterations=int(os.getenv("BUDGET_ENTERPRISE_MAX_ITER", "50")),
            ),
        }
        return tier_configs.get(tier.lower(), tier_configs["pro"])


class CostController:
    """
    Controls and tracks costs during Agent execution.

    Usage:
        controller = CostController(budget=BudgetConfig.for_tier("pro"))
        controller.check_budget()  # Raises BudgetExceededError if over
        controller.record_llm_usage(model, prompt_tokens, completion_tokens)
        controller.record_tool_call()
    """

    def __init__(self, budget: Optional[BudgetConfig] = None):
        self.budget = budget or BudgetConfig.from_env()
        self._cost_spent: float = 0.0
        self._tokens_used: int = 0
        self._tool_calls: int = 0
        self._llm_calls: int = 0
        self._iterations: int = 0
        self._usage_history: List[UsageRecord] = []
        self._warnings_emitted: set = set()

    def check_budget(self) -> None:
        """
        Check if any budget limit is exceeded.

        Raises:
            BudgetExceededError: If any limit is exceeded
        """
        # Check cost
        if self._cost_spent >= self.budget.max_cost_usd:
            raise BudgetExceededError(
                f"Cost budget exceeded: ${self._cost_spent:.4f} >= ${self.budget.max_cost_usd:.2f}",
                spent=self._cost_spent,
                budget=self.budget.max_cost_usd,
                resource_type="cost",
            )

        # Check tokens
        if self._tokens_used >= self.budget.max_tokens:
            raise BudgetExceededError(
                f"Token budget exceeded: {self._tokens_used} >= {self.budget.max_tokens}",
                spent=self._tokens_used,
                budget=self.budget.max_tokens,
                resource_type="tokens",
            )

        # Check tool calls
        if self._tool_calls >= self.budget.max_tool_calls:
            raise BudgetExceededError(
                f"Tool call limit exceeded: {self._tool_calls} >= {self.budget.max_tool_calls}",
                spent=self._tool_calls,
                budget=self.budget.max_tool_calls,
                resource_type="tool_calls",
            )

        # Check LLM calls
        if self._llm_calls >= self.budget.max_llm_calls:
            raise BudgetExceededError(
                f"LLM call limit exceeded: {self._llm_calls} >= {self.budget.max_llm_calls}",
                spent=self._llm_calls,
                budget=self.budget.max_llm_calls,
                resource_type="llm_calls",
            )

        # Check iterations
        if self._iterations >= self.budget.max_iterations:
            raise BudgetExceededError(
                f"Iteration limit exceeded: {self._iterations} >= {self.budget.max_iterations}",
                spent=self._iterations,
                budget=self.budget.max_iterations,
                resource_type="iterations",
            )

        # Emit warnings at threshold
        self._check_warnings()

    def _check_warnings(self) -> None:
        """Emit warnings when approaching limits."""
        threshold = self.budget.warning_threshold

        if (
            "cost" not in self._warnings_emitted
            and self._cost_spent >= self.budget.max_cost_usd * threshold
        ):
            logger.warning(
                f"Cost approaching limit: ${self._cost_spent:.4f} / ${self.budget.max_cost_usd:.2f} "
                f"({self._cost_spent / self.budget.max_cost_usd * 100:.0f}%)"
            )
            self._warnings_emitted.add("cost")

        if (
            "tokens" not in self._warnings_emitted
            and self._tokens_used >= self.budget.max_tokens * threshold
        ):
            logger.warning(
                f"Tokens approaching limit: {self._tokens_used} / {self.budget.max_tokens} "
                f"({self._tokens_used / self.budget.max_tokens * 100:.0f}%)"
            )
            self._warnings_emitted.add("tokens")

    def record_llm_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        timestamp: Optional[float] = None,
    ) -> float:
        """
        Record LLM usage and return cost.

        Returns:
            Cost in USD for this call
        """
        import time

        cost = get_model_cost(model, prompt_tokens, completion_tokens)

        self._cost_spent += cost
        self._tokens_used += prompt_tokens + completion_tokens
        self._llm_calls += 1

        self._usage_history.append(
            UsageRecord(
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=cost,
                timestamp=timestamp or time.time(),
            )
        )

        logger.debug(
            f"LLM usage: {model} {prompt_tokens}+{completion_tokens} tokens, "
            f"${cost:.4f}, total=${self._cost_spent:.4f}"
        )

        return cost

    def record_tool_call(self, cost_usd: float = 0.0) -> None:
        """Record a tool call."""
        self._tool_calls += 1
        self._cost_spent += cost_usd

    def record_iteration(self) -> None:
        """Record an iteration."""
        self._iterations += 1

    @property
    def cost_spent(self) -> float:
        """Total cost spent."""
        return self._cost_spent

    @property
    def tokens_used(self) -> int:
        """Total tokens used."""
        return self._tokens_used

    @property
    def remaining_budget(self) -> float:
        """Remaining cost budget."""
        return max(0, self.budget.max_cost_usd - self._cost_spent)

    @property
    def remaining_tokens(self) -> int:
        """Remaining token budget."""
        return max(0, self.budget.max_tokens - self._tokens_used)

    def get_summary(self) -> Dict[str, Any]:
        """Get usage summary."""
        return {
            "cost_spent_usd": self._cost_spent,
            "cost_budget_usd": self.budget.max_cost_usd,
            "cost_remaining_usd": self.remaining_budget,
            "tokens_used": self._tokens_used,
            "tokens_budget": self.budget.max_tokens,
            "tokens_remaining": self.remaining_tokens,
            "tool_calls": self._tool_calls,
            "tool_calls_limit": self.budget.max_tool_calls,
            "llm_calls": self._llm_calls,
            "llm_calls_limit": self.budget.max_llm_calls,
            "iterations": self._iterations,
            "iterations_limit": self.budget.max_iterations,
        }

    def can_afford(self, estimated_cost: float) -> bool:
        """Check if we can afford an estimated cost."""
        return self._cost_spent + estimated_cost <= self.budget.max_cost_usd

    def can_afford_tokens(self, estimated_tokens: int) -> bool:
        """Check if we can afford estimated tokens."""
        return self._tokens_used + estimated_tokens <= self.budget.max_tokens


def get_cost_controller(
    tier: Optional[str] = None,
    budget: Optional[BudgetConfig] = None,
) -> CostController:
    """Create a cost controller."""
    if budget:
        return CostController(budget=budget)
    if tier:
        return CostController(budget=BudgetConfig.for_tier(tier))
    return CostController()
