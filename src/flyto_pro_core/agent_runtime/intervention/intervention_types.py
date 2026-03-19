"""
Intervention Types - Types and points for user intervention.

Defines when the AI should pause and ask the user.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class InterventionType(Enum):
    """Types of user intervention."""

    # Confirmation
    CONFIRM_DANGEROUS = "confirm_dangerous"  # Destructive actions
    CONFIRM_COST = "confirm_cost"  # High cost operations
    CONFIRM_SCOPE = "confirm_scope"  # Scope changes

    # Decision
    CHOOSE_APPROACH = "choose_approach"  # Multiple solutions
    CHOOSE_PRIORITY = "choose_priority"  # Task prioritization
    CHOOSE_TRADEOFF = "choose_tradeoff"  # Trade-off decisions

    # Clarification
    CLARIFY_REQUIREMENT = "clarify_requirement"  # Unclear requirements
    CLARIFY_CONTEXT = "clarify_context"  # Missing context
    CLARIFY_EXPECTATION = "clarify_expectation"  # Expected behavior

    # Error handling
    RETRY_OR_ABORT = "retry_or_abort"  # After failure
    FIX_SUGGESTION = "fix_suggestion"  # Suggest fix from EMS

    # Progress
    CHECKPOINT = "checkpoint"  # Regular checkpoint
    MILESTONE = "milestone"  # Major milestone reached


class InterventionPriority(Enum):
    """Priority levels for interventions."""

    CRITICAL = "critical"  # Must stop immediately
    HIGH = "high"  # Stop at next safe point
    MEDIUM = "medium"  # Can batch with others
    LOW = "low"  # Can skip if auto-approve enabled


@dataclass
class InterventionPoint:
    """
    Defines a point where intervention may occur.

    These are registered in the workflow.
    """

    point_id: str = ""
    point_type: InterventionType = InterventionType.CHECKPOINT
    priority: InterventionPriority = InterventionPriority.MEDIUM

    # Conditions
    trigger_condition: str = ""  # Expression to evaluate
    auto_approve_after_ms: int = 0  # Auto-approve timeout (0 = wait forever)

    # Context
    step_id: Optional[str] = None
    task_id: Optional[str] = None
    goal_id: Optional[str] = None

    # Message
    title: str = ""
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.point_id:
            self.point_id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "point_id": self.point_id,
            "point_type": self.point_type.value,
            "priority": self.priority.value,
            "trigger_condition": self.trigger_condition,
            "auto_approve_after_ms": self.auto_approve_after_ms,
            "step_id": self.step_id,
            "task_id": self.task_id,
            "goal_id": self.goal_id,
            "title": self.title,
            "description": self.description,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InterventionPoint":
        return cls(
            point_id=data.get("point_id", ""),
            point_type=InterventionType(data.get("point_type", "checkpoint")),
            priority=InterventionPriority(data.get("priority", "medium")),
            trigger_condition=data.get("trigger_condition", ""),
            auto_approve_after_ms=data.get("auto_approve_after_ms", 0),
            step_id=data.get("step_id"),
            task_id=data.get("task_id"),
            goal_id=data.get("goal_id"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            details=data.get("details", {}),
        )


@dataclass
class InterventionOption:
    """An option for user to choose."""

    option_id: str = ""
    label: str = ""
    description: str = ""
    is_recommended: bool = False
    is_dangerous: bool = False
    consequences: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.option_id:
            self.option_id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "option_id": self.option_id,
            "label": self.label,
            "description": self.description,
            "is_recommended": self.is_recommended,
            "is_dangerous": self.is_dangerous,
            "consequences": self.consequences,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InterventionOption":
        return cls(
            option_id=data.get("option_id", ""),
            label=data.get("label", ""),
            description=data.get("description", ""),
            is_recommended=data.get("is_recommended", False),
            is_dangerous=data.get("is_dangerous", False),
            consequences=data.get("consequences", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class InterventionRequest:
    """
    Request for user intervention.

    Sent to the UI for display.
    """

    request_id: str = ""
    intervention_point: InterventionPoint = field(default_factory=InterventionPoint)
    options: List[InterventionOption] = field(default_factory=list)

    # Timing
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    timeout_at: Optional[str] = None
    is_blocking: bool = True

    # Context
    current_state_summary: Dict[str, Any] = field(default_factory=dict)
    relevant_evidence: List[str] = field(default_factory=list)

    # Free-form input
    allow_text_input: bool = False
    text_input_prompt: str = ""

    def __post_init__(self):
        if not self.request_id:
            self.request_id = str(uuid.uuid4())[:12]

        if self.intervention_point.auto_approve_after_ms > 0:
            from datetime import timedelta

            timeout = datetime.fromisoformat(self.created_at) + timedelta(
                milliseconds=self.intervention_point.auto_approve_after_ms
            )
            self.timeout_at = timeout.isoformat()

    def is_expired(self) -> bool:
        """Check if request has expired."""
        if not self.timeout_at:
            return False
        return datetime.utcnow() > datetime.fromisoformat(self.timeout_at)

    def get_default_option(self) -> Optional[InterventionOption]:
        """Get recommended or first option."""
        for opt in self.options:
            if opt.is_recommended:
                return opt
        return self.options[0] if self.options else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "intervention_point": self.intervention_point.to_dict(),
            "options": [o.to_dict() for o in self.options],
            "created_at": self.created_at,
            "timeout_at": self.timeout_at,
            "is_blocking": self.is_blocking,
            "current_state_summary": self.current_state_summary,
            "relevant_evidence": self.relevant_evidence,
            "allow_text_input": self.allow_text_input,
            "text_input_prompt": self.text_input_prompt,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InterventionRequest":
        return cls(
            request_id=data.get("request_id", ""),
            intervention_point=InterventionPoint.from_dict(
                data.get("intervention_point", {})
            ),
            options=[
                InterventionOption.from_dict(o) for o in data.get("options", [])
            ],
            created_at=data.get("created_at", ""),
            timeout_at=data.get("timeout_at"),
            is_blocking=data.get("is_blocking", True),
            current_state_summary=data.get("current_state_summary", {}),
            relevant_evidence=data.get("relevant_evidence", []),
            allow_text_input=data.get("allow_text_input", False),
            text_input_prompt=data.get("text_input_prompt", ""),
        )


@dataclass
class InterventionResponse:
    """
    User's response to intervention request.

    Received from the UI.
    """

    request_id: str = ""
    selected_option_id: Optional[str] = None
    text_input: Optional[str] = None
    response_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Auto-response
    is_auto_response: bool = False
    auto_response_reason: Optional[str] = None  # timeout, default, etc.

    # Metadata
    response_time_ms: int = 0
    user_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "selected_option_id": self.selected_option_id,
            "text_input": self.text_input,
            "response_at": self.response_at,
            "is_auto_response": self.is_auto_response,
            "auto_response_reason": self.auto_response_reason,
            "response_time_ms": self.response_time_ms,
            "user_id": self.user_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InterventionResponse":
        return cls(
            request_id=data.get("request_id", ""),
            selected_option_id=data.get("selected_option_id"),
            text_input=data.get("text_input"),
            response_at=data.get("response_at", ""),
            is_auto_response=data.get("is_auto_response", False),
            auto_response_reason=data.get("auto_response_reason"),
            response_time_ms=data.get("response_time_ms", 0),
            user_id=data.get("user_id"),
        )


# Pre-defined intervention points
DANGEROUS_ACTION_POINT = InterventionPoint(
    point_type=InterventionType.CONFIRM_DANGEROUS,
    priority=InterventionPriority.CRITICAL,
    title="Dangerous Action",
    description="This action may have irreversible consequences.",
)

HIGH_COST_POINT = InterventionPoint(
    point_type=InterventionType.CONFIRM_COST,
    priority=InterventionPriority.HIGH,
    title="High Cost Operation",
    description="This operation may incur significant costs.",
)

APPROACH_DECISION_POINT = InterventionPoint(
    point_type=InterventionType.CHOOSE_APPROACH,
    priority=InterventionPriority.MEDIUM,
    title="Choose Approach",
    description="Multiple solutions are available.",
)

RETRY_POINT = InterventionPoint(
    point_type=InterventionType.RETRY_OR_ABORT,
    priority=InterventionPriority.HIGH,
    title="Operation Failed",
    description="The operation failed. Choose how to proceed.",
)
