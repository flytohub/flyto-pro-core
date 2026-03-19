"""
Integration Module - Bridges agent_runtime with existing agent.

Provides adapters and helpers to integrate the new deterministic
verification system with the existing AgentLoop and VerificationGate.
"""

from .agent_loop_adapter import (
    AgentLoopAdapter,
    RuntimeContext,
)
from .verification_adapter import (
    VerificationAdapter,
    adapt_assertion_to_goal,
    adapt_goal_to_assertion,
)
from .observation_adapter import (
    ObservationAdapter,
    capture_browser_observation,
    capture_execution_observation,
)

__all__ = [
    # Agent Loop
    "AgentLoopAdapter",
    "RuntimeContext",
    # Verification
    "VerificationAdapter",
    "adapt_assertion_to_goal",
    "adapt_goal_to_assertion",
    # Observation
    "ObservationAdapter",
    "capture_browser_observation",
    "capture_execution_observation",
]
