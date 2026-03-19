"""
Stop Policy - Prevents infinite iteration and runaway costs.

This is a critical safety mechanism that must be deterministic.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .contract_meta import ContractMeta


class StopReason(Enum):
    """Reasons for stopping execution."""

    MAX_ITERATIONS = "max_iterations_reached"
    MAX_COST = "max_cost_reached"
    MAX_TIME = "max_time_reached"
    CONSECUTIVE_FAILURES = "consecutive_failures"
    REPEATED_ERROR = "repeated_error_pattern"
    USER_CANCEL = "user_cancel"
    GOAL_ACHIEVED = "goal_achieved"
    CAPABILITY_DENIED = "capability_denied"


class FallbackAction(Enum):
    """Actions to take when fallback is triggered."""

    STOP = "stop"
    SWITCH_STRATEGY = "switch_strategy"
    DOWNGRADE_VERIFICATION = "downgrade_verification"
    ASK_USER = "ask_user"
    RETRY_WITH_DELAY = "retry_with_delay"


@dataclass
class FallbackPolicy:
    """Policy for fallback actions."""

    trigger: str  # e.g. "consecutive_failures >= 2"
    action: FallbackAction
    params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trigger": self.trigger,
            "action": self.action.value,
            "params": self.params,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FallbackPolicy":
        """Create from dictionary."""
        return cls(
            trigger=data["trigger"],
            action=FallbackAction(data["action"]),
            params=data.get("params", {}),
        )


@dataclass
class StopPolicy:
    """
    Deterministic stop policy for agent execution.

    All decisions are based on measurable thresholds, not LLM judgment.
    """

    # Metadata
    meta: ContractMeta = field(
        default_factory=lambda: ContractMeta(
            contract_name="StopPolicy",
            version="1.0.0",
            compatible_with=["^1.0"],
        )
    )

    # Hard limits
    max_iterations: int = 20
    max_cost_usd: float = 10.0
    max_time_seconds: int = 3600  # 1 hour

    # Error thresholds
    max_consecutive_failures: int = 3
    repeated_error_threshold: int = 3  # Same error N times = stop

    # User confirmation required for these actions
    require_confirmation_for: List[str] = field(
        default_factory=lambda: [
            "delete_data",
            "payment",
            "send_email",
            "deploy_production",
            "modify_permissions",
        ]
    )

    # Fallback policies
    fallback_policies: List[FallbackPolicy] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "meta": self.meta.to_dict(),
            "max_iterations": self.max_iterations,
            "max_cost_usd": self.max_cost_usd,
            "max_time_seconds": self.max_time_seconds,
            "max_consecutive_failures": self.max_consecutive_failures,
            "repeated_error_threshold": self.repeated_error_threshold,
            "require_confirmation_for": self.require_confirmation_for,
            "fallback_policies": [p.to_dict() for p in self.fallback_policies],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StopPolicy":
        """Create from dictionary."""
        return cls(
            meta=ContractMeta.from_dict(data.get("meta", {})),
            max_iterations=data.get("max_iterations", 20),
            max_cost_usd=data.get("max_cost_usd", 10.0),
            max_time_seconds=data.get("max_time_seconds", 3600),
            max_consecutive_failures=data.get("max_consecutive_failures", 3),
            repeated_error_threshold=data.get("repeated_error_threshold", 3),
            require_confirmation_for=data.get("require_confirmation_for", []),
            fallback_policies=[
                FallbackPolicy.from_dict(p)
                for p in data.get("fallback_policies", [])
            ],
        )


class StopPolicyChecker:
    """
    Stateful checker for stop policy.

    Tracks execution state and determines when to stop.
    """

    def __init__(self, policy: StopPolicy):
        self.policy = policy
        self.iteration_count = 0
        self.total_cost = 0.0
        self.start_time: Optional[float] = None
        self.failure_history: List[str] = []
        self.error_counts: Dict[str, int] = {}

    def start(self) -> None:
        """Mark execution start."""
        self.start_time = time.time()
        self.iteration_count = 0
        self.total_cost = 0.0
        self.failure_history = []
        self.error_counts = {}

    def record_iteration(self, cost: float = 0.0) -> None:
        """Record a completed iteration."""
        self.iteration_count += 1
        self.total_cost += cost

    def record_failure(self, error: str) -> None:
        """Record a failure."""
        self.failure_history.append(error)

        # Track error counts
        error_key = self._normalize_error(error)
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

    def record_success(self) -> None:
        """Record a success (resets consecutive failures)."""
        self.failure_history = []

    def _normalize_error(self, error: str) -> str:
        """Normalize error message for comparison."""
        # Remove line numbers, timestamps, etc.
        import re

        normalized = re.sub(r"\d+", "N", error)
        normalized = re.sub(r"0x[0-9a-fA-F]+", "ADDR", normalized)
        return normalized[:200]  # Truncate for comparison

    def _count_consecutive_failures(self) -> int:
        """Count consecutive failures."""
        return len(self.failure_history)

    def _has_repeated_error(self) -> bool:
        """Check if any error has repeated too many times."""
        for count in self.error_counts.values():
            if count >= self.policy.repeated_error_threshold:
                return True
        return False

    def should_stop(self) -> Tuple[bool, StopReason, str]:
        """
        Check if execution should stop.

        Returns:
            Tuple of (should_stop, reason, details)
        """
        # Check iteration limit
        if self.iteration_count >= self.policy.max_iterations:
            return (
                True,
                StopReason.MAX_ITERATIONS,
                f"Reached {self.policy.max_iterations} iterations",
            )

        # Check cost limit
        if self.total_cost >= self.policy.max_cost_usd:
            return (
                True,
                StopReason.MAX_COST,
                f"Reached ${self.policy.max_cost_usd} cost",
            )

        # Check time limit
        if self.start_time:
            elapsed = time.time() - self.start_time
            if elapsed >= self.policy.max_time_seconds:
                return (
                    True,
                    StopReason.MAX_TIME,
                    f"Reached {self.policy.max_time_seconds}s time limit",
                )

        # Check consecutive failures
        consecutive = self._count_consecutive_failures()
        if consecutive >= self.policy.max_consecutive_failures:
            return (
                True,
                StopReason.CONSECUTIVE_FAILURES,
                f"{consecutive} consecutive failures",
            )

        # Check repeated errors
        if self._has_repeated_error():
            repeated_errors = [
                k for k, v in self.error_counts.items()
                if v >= self.policy.repeated_error_threshold
            ]
            return (
                True,
                StopReason.REPEATED_ERROR,
                f"Error repeated {self.policy.repeated_error_threshold}+ times: {repeated_errors[0][:50]}",
            )

        return False, StopReason.GOAL_ACHIEVED, ""

    def needs_user_confirmation(self, action: str) -> bool:
        """Check if an action requires user confirmation."""
        return action in self.policy.require_confirmation_for

    def get_fallback(self, trigger: str) -> Optional[FallbackPolicy]:
        """Get applicable fallback policy for a trigger."""
        for policy in self.policy.fallback_policies:
            if self._matches_trigger(trigger, policy.trigger):
                return policy
        return None

    def _matches_trigger(self, actual: str, pattern: str) -> bool:
        """Check if actual trigger matches pattern."""
        # Simple matching for now
        # Pattern format: "variable operator value"
        # e.g. "consecutive_failures >= 2"
        import re

        match = re.match(r"(\w+)\s*(>=|<=|==|>|<)\s*(\d+)", pattern)
        if not match:
            return actual == pattern

        var_name, op, threshold = match.groups()
        threshold = int(threshold)

        # Get actual value
        if var_name == "consecutive_failures":
            actual_value = self._count_consecutive_failures()
        elif var_name == "iteration_count":
            actual_value = self.iteration_count
        elif var_name == "total_cost":
            actual_value = self.total_cost
        else:
            return False

        # Compare
        if op == ">=":
            return actual_value >= threshold
        elif op == "<=":
            return actual_value <= threshold
        elif op == "==":
            return actual_value == threshold
        elif op == ">":
            return actual_value > threshold
        elif op == "<":
            return actual_value < threshold

        return False

    def get_status(self) -> Dict[str, Any]:
        """Get current status."""
        elapsed = time.time() - self.start_time if self.start_time else 0

        return {
            "iteration_count": self.iteration_count,
            "max_iterations": self.policy.max_iterations,
            "total_cost": self.total_cost,
            "max_cost": self.policy.max_cost_usd,
            "elapsed_seconds": elapsed,
            "max_time_seconds": self.policy.max_time_seconds,
            "consecutive_failures": self._count_consecutive_failures(),
            "max_consecutive_failures": self.policy.max_consecutive_failures,
            "error_counts": dict(self.error_counts),
        }


# JSON Schema for validation
STOP_POLICY_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "max_iterations": {"type": "integer", "minimum": 1, "maximum": 100},
        "max_cost_usd": {"type": "number", "minimum": 0},
        "max_time_seconds": {"type": "integer", "minimum": 1},
        "max_consecutive_failures": {"type": "integer", "minimum": 1},
        "repeated_error_threshold": {"type": "integer", "minimum": 1},
        "require_confirmation_for": {
            "type": "array",
            "items": {"type": "string"},
        },
        "fallback_policies": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "trigger": {"type": "string"},
                    "action": {
                        "enum": [
                            "stop",
                            "switch_strategy",
                            "downgrade_verification",
                            "ask_user",
                            "retry_with_delay",
                        ]
                    },
                    "params": {"type": "object"},
                },
                "required": ["trigger", "action"],
            },
        },
    },
}
