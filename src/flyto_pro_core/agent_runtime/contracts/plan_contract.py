"""
Plan Contract - LLM planning output contract.

This is the contract between flyto-pro (AI #1) and flyto-cloud (AI #2).
Defines what the LLM planner must output for the runtime to execute.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .contract_meta import ContractMeta


class AssertionLevel(Enum):
    """Assertion strictness level."""

    HARD = "hard"  # Must pass 100%
    SOFT = "soft"  # Allow threshold


class AssertionType(Enum):
    """Types of assertions for verification."""

    EQUALS = "equals"
    CONTAINS = "contains"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    REGEX_MATCH = "regex_match"
    DOM_EXISTS = "dom_exists"
    DOM_VISIBLE = "dom_visible"
    URL_MATCH = "url_match"
    DB_QUERY = "db_query"
    SCREENSHOT_SIMILAR = "screenshot_similar"
    CUSTOM = "custom"


class ObservationType(Enum):
    """Types of observations to collect."""

    BROWSER = "browser"
    DATABASE = "database"
    FILESYSTEM = "filesystem"
    NETWORK = "network"
    RUNTIME = "runtime"


class StopConditionType(Enum):
    """Types of stop conditions."""

    ASSERTION_PASSED = "assertion_passed"
    ASSERTION_FAILED = "assertion_failed"
    MAX_ITERATIONS = "max_iterations"
    COST_LIMIT = "cost_limit"
    TIME_LIMIT = "time_limit"
    USER_CANCEL = "user_cancel"


@dataclass
class Assertion:
    """
    A single assertion to verify.

    Assertions are the core of deterministic verification.
    Hard assertions must pass 100%, soft assertions allow thresholds.
    """

    assertion_id: str
    assertion_type: str  # dom_exists, db_query, screenshot_similar, etc.
    expression: str  # e.g. "assert_dom_exists('#success-message')"
    expected: Any = None
    level: AssertionLevel = AssertionLevel.HARD
    threshold: Optional[float] = None  # For soft assertions
    weight: float = 1.0  # For confidence calculation
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "assertion_id": self.assertion_id,
            "assertion_type": self.assertion_type,
            "expression": self.expression,
            "expected": self.expected,
            "level": self.level.value,
            "threshold": self.threshold,
            "weight": self.weight,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Assertion":
        """Create from dictionary."""
        return cls(
            assertion_id=data["assertion_id"],
            assertion_type=data["assertion_type"],
            expression=data["expression"],
            expected=data.get("expected"),
            level=AssertionLevel(data.get("level", "hard")),
            threshold=data.get("threshold"),
            weight=data.get("weight", 1.0),
            description=data.get("description", ""),
        )


@dataclass
class ObservationSpec:
    """
    Specification for what to observe after execution.

    Tells the runtime what evidence to collect.
    """

    observation_type: ObservationType
    targets: List[str] = field(default_factory=list)  # e.g. ["#login-button"]
    capture_mode: str = "snapshot"  # snapshot, diff, stream

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "observation_type": self.observation_type.value,
            "targets": self.targets,
            "capture_mode": self.capture_mode,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ObservationSpec":
        """Create from dictionary."""
        return cls(
            observation_type=ObservationType(data["observation_type"]),
            targets=data.get("targets", []),
            capture_mode=data.get("capture_mode", "snapshot"),
        )


@dataclass
class StopCondition:
    """
    Condition for when to stop iteration.
    """

    condition_type: StopConditionType
    threshold: Any = None
    action: str = "stop"  # stop, fallback, ask_user

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "condition_type": self.condition_type.value,
            "threshold": self.threshold,
            "action": self.action,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StopCondition":
        """Create from dictionary."""
        return cls(
            condition_type=StopConditionType(data["condition_type"]),
            threshold=data.get("threshold"),
            action=data.get("action", "stop"),
        )


@dataclass
class PlanContract:
    """
    The contract between flyto-pro (planner) and flyto-cloud (executor).

    This is what the LLM must output, and what the runtime expects to receive.
    """

    # Metadata
    meta: ContractMeta = field(
        default_factory=lambda: ContractMeta(
            contract_name="PlanContract",
            version="1.0.0",
            compatible_with=["^1.0"],
        )
    )

    # Identity
    plan_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # The workflow to execute
    workflow_yaml: str = ""

    # Verification conditions
    assertions: List[Assertion] = field(default_factory=list)

    # What to observe after execution
    required_observations: List[ObservationSpec] = field(default_factory=list)

    # Risk assessment
    risk_level: str = "low"  # low, medium, high, critical
    needs_user_confirmation: bool = False

    # Stop conditions
    stop_conditions: List[StopCondition] = field(default_factory=list)

    # Expected outcome
    expected_outcome: Dict[str, Any] = field(default_factory=dict)

    # Fallback strategy
    fallback_strategy: Optional[str] = None

    # Required capabilities
    required_capabilities: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (JSON serializable)."""
        return {
            "meta": self.meta.to_dict(),
            "plan_id": self.plan_id,
            "timestamp": self.timestamp,
            "workflow_yaml": self.workflow_yaml,
            "assertions": [a.to_dict() for a in self.assertions],
            "required_observations": [o.to_dict() for o in self.required_observations],
            "risk_level": self.risk_level,
            "needs_user_confirmation": self.needs_user_confirmation,
            "stop_conditions": [s.to_dict() for s in self.stop_conditions],
            "expected_outcome": self.expected_outcome,
            "fallback_strategy": self.fallback_strategy,
            "required_capabilities": self.required_capabilities,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlanContract":
        """Create from dictionary."""
        return cls(
            meta=ContractMeta.from_dict(data.get("meta", {})),
            plan_id=data.get("plan_id", ""),
            timestamp=data.get("timestamp", ""),
            workflow_yaml=data.get("workflow_yaml", ""),
            assertions=[Assertion.from_dict(a) for a in data.get("assertions", [])],
            required_observations=[
                ObservationSpec.from_dict(o)
                for o in data.get("required_observations", [])
            ],
            risk_level=data.get("risk_level", "low"),
            needs_user_confirmation=data.get("needs_user_confirmation", False),
            stop_conditions=[
                StopCondition.from_dict(s) for s in data.get("stop_conditions", [])
            ],
            expected_outcome=data.get("expected_outcome", {}),
            fallback_strategy=data.get("fallback_strategy"),
            required_capabilities=data.get("required_capabilities", []),
        )

    def validate(self) -> List[str]:
        """
        Validate the plan contract.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not self.plan_id:
            errors.append("plan_id is required")

        if not self.workflow_yaml:
            errors.append("workflow_yaml is required")

        if self.risk_level not in ("low", "medium", "high", "critical"):
            errors.append(f"Invalid risk_level: {self.risk_level}")

        # High risk without confirmation
        if self.risk_level in ("high", "critical") and not self.needs_user_confirmation:
            errors.append("High/critical risk plans should require user confirmation")

        # Validate assertions
        for i, assertion in enumerate(self.assertions):
            if not assertion.assertion_id:
                errors.append(f"Assertion {i} missing assertion_id")
            if not assertion.assertion_type:
                errors.append(f"Assertion {i} missing assertion_type")
            if assertion.level == AssertionLevel.SOFT and assertion.threshold is None:
                errors.append(f"Soft assertion {assertion.assertion_id} missing threshold")

        return errors

    def get_hard_assertions(self) -> List[Assertion]:
        """Get all hard assertions."""
        return [a for a in self.assertions if a.level == AssertionLevel.HARD]

    def get_soft_assertions(self) -> List[Assertion]:
        """Get all soft assertions."""
        return [a for a in self.assertions if a.level == AssertionLevel.SOFT]


# JSON Schema for validation
PLAN_CONTRACT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "meta": {
            "type": "object",
            "properties": {
                "contract_name": {"type": "string"},
                "version": {"type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$"},
                "compatible_with": {"type": "array", "items": {"type": "string"}},
                "checksum": {"type": "string"},
                "generated_by": {"type": "string"},
                "created_at": {"type": "string"},
            },
            "required": ["contract_name", "version"],
        },
        "plan_id": {"type": "string", "minLength": 1},
        "timestamp": {"type": "string"},
        "workflow_yaml": {"type": "string", "minLength": 1},
        "assertions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "assertion_id": {"type": "string"},
                    "assertion_type": {"type": "string"},
                    "expression": {"type": "string"},
                    "expected": {},
                    "level": {"enum": ["hard", "soft"]},
                    "threshold": {"type": ["number", "null"]},
                    "weight": {"type": "number"},
                    "description": {"type": "string"},
                },
                "required": ["assertion_id", "assertion_type", "expression"],
            },
        },
        "required_observations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "observation_type": {
                        "enum": ["browser", "database", "filesystem", "network", "runtime"]
                    },
                    "targets": {"type": "array", "items": {"type": "string"}},
                    "capture_mode": {"enum": ["snapshot", "diff", "stream"]},
                },
                "required": ["observation_type"],
            },
        },
        "risk_level": {"enum": ["low", "medium", "high", "critical"]},
        "needs_user_confirmation": {"type": "boolean"},
        "stop_conditions": {"type": "array"},
        "expected_outcome": {"type": "object"},
        "fallback_strategy": {"type": ["string", "null"]},
        "required_capabilities": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["plan_id", "workflow_yaml"],
}
