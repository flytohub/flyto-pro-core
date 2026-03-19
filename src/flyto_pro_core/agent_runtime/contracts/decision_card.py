"""
Decision Card - Human intervention interface.

Makes it easy for non-engineers to make technical decisions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .contract_meta import ContractMeta


class DecisionType(Enum):
    """Types of decisions."""

    TECH_CHOICE = "tech_choice"  # Technical choice (framework, tool)
    RISK_CONFIRMATION = "risk_confirmation"  # Confirm risky action
    DIRECTION_CHANGE = "direction_change"  # Change project direction
    APPROVAL = "approval"  # Approve/reject result
    CLARIFICATION = "clarification"  # Need more info


@dataclass
class DecisionOption:
    """A single decision option."""

    option_id: str = ""
    label: str = ""  # Human-readable label
    description: str = ""  # Detailed explanation
    technical_detail: str = ""  # Technical details (expandable)

    # Impact analysis
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    consequences: List[str] = field(default_factory=list)  # For builder compatibility

    # Risk
    risk_level: str = "low"  # low, medium, high

    # Builder compatibility fields
    is_recommended: bool = False
    is_dangerous: bool = False
    action: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Effort estimate
    estimated_effort: str = ""  # e.g. "2-3 hours"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "option_id": self.option_id,
            "label": self.label,
            "description": self.description,
            "technical_detail": self.technical_detail,
            "pros": self.pros,
            "cons": self.cons,
            "consequences": self.consequences,
            "risk_level": self.risk_level,
            "is_recommended": self.is_recommended,
            "is_dangerous": self.is_dangerous,
            "action": self.action,
            "metadata": self.metadata,
            "estimated_effort": self.estimated_effort,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DecisionOption":
        """Create from dictionary."""
        return cls(
            option_id=data.get("option_id", ""),
            label=data.get("label", ""),
            description=data.get("description", ""),
            technical_detail=data.get("technical_detail", ""),
            pros=data.get("pros", []),
            cons=data.get("cons", []),
            consequences=data.get("consequences", []),
            risk_level=data.get("risk_level", "low"),
            is_recommended=data.get("is_recommended", False),
            is_dangerous=data.get("is_dangerous", False),
            action=data.get("action", {}),
            metadata=data.get("metadata", {}),
            estimated_effort=data.get("estimated_effort", ""),
        )


@dataclass
class DecisionContext:
    """Context for a decision card."""

    source: str = ""  # Where the decision came from
    step_id: str = ""  # Current step
    task_id: str = ""  # Current task
    goal_id: str = ""  # Current goal
    previous_decisions: List[str] = field(default_factory=list)  # Related decision IDs
    extra: Dict[str, Any] = field(default_factory=dict)
    # Builder compatibility fields
    additional_context: Dict[str, Any] = field(default_factory=dict)
    relevant_evidence: List[str] = field(default_factory=list)
    current_state: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "step_id": self.step_id,
            "task_id": self.task_id,
            "goal_id": self.goal_id,
            "previous_decisions": self.previous_decisions,
            "extra": self.extra,
            "additional_context": self.additional_context,
            "relevant_evidence": self.relevant_evidence,
            "current_state": self.current_state,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DecisionContext":
        """Create from dictionary."""
        return cls(
            source=data.get("source", ""),
            step_id=data.get("step_id", ""),
            task_id=data.get("task_id", ""),
            goal_id=data.get("goal_id", ""),
            previous_decisions=data.get("previous_decisions", []),
            extra=data.get("extra", {}),
            additional_context=data.get("additional_context", {}),
            relevant_evidence=data.get("relevant_evidence", []),
            current_state=data.get("current_state", ""),
        )


@dataclass
class UserDecision:
    """User's response to a decision card."""

    card_id: str = ""
    selected_option_id: str = ""
    text_input: str = ""
    decided_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    decided_by: str = "user"  # "user", "timeout", "auto"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "card_id": self.card_id,
            "selected_option_id": self.selected_option_id,
            "text_input": self.text_input,
            "decided_at": self.decided_at,
            "decided_by": self.decided_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserDecision":
        """Create from dictionary."""
        return cls(
            card_id=data.get("card_id", ""),
            selected_option_id=data.get("selected_option_id", ""),
            text_input=data.get("text_input", ""),
            decided_at=data.get("decided_at", ""),
            decided_by=data.get("decided_by", "user"),
        )


@dataclass
class DecisionCard:
    """
    Human-machine intervention interface.

    Designed for non-engineers to understand and make technical decisions.
    """

    # Metadata
    meta: ContractMeta = field(
        default_factory=lambda: ContractMeta(
            contract_name="DecisionCard",
            version="1.0.0",
            compatible_with=["^1.0"],
        )
    )

    # Identity
    card_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Decision type
    decision_type: Any = DecisionType.TECH_CHOICE  # Can be DecisionType or str

    # Question (human-readable)
    question: str = ""

    # Builder compatibility - title and description
    title: str = ""  # Alternative to question
    description: str = ""  # Additional description

    # Options
    options: List[DecisionOption] = field(default_factory=list)

    # AI recommendation
    recommendation: Optional[str] = None  # option_id
    recommendation_reason: str = ""

    # Impact analysis
    consequences: Dict[str, str] = field(default_factory=dict)  # {option_id: impact}

    # Timeout handling
    timeout_seconds: int = 300  # 5 minutes default
    timeout_ms: int = 300000  # Builder compatibility (ms)
    default_option: Optional[str] = None  # Auto-select on timeout
    default_option_id: Optional[str] = None  # Builder compatibility

    # Priority
    priority: str = "medium"  # critical, high, medium, low

    # Reversibility
    reversible: bool = True
    reversal_cost: str = "low"  # low, medium, high

    # Context - can be Dict or DecisionContext
    context: Any = field(default_factory=dict)

    # Builder compatibility fields
    is_blocking: bool = True
    allow_text_input: bool = False
    text_input_prompt: str = ""

    # Result (filled after decision)
    selected_option: Optional[str] = None
    selected_by: Optional[str] = None  # "user" or "timeout"
    selected_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "meta": self.meta.to_dict(),
            "card_id": self.card_id,
            "timestamp": self.timestamp,
            "decision_type": self.decision_type.value,
            "question": self.question,
            "options": [o.to_dict() for o in self.options],
            "recommendation": self.recommendation,
            "recommendation_reason": self.recommendation_reason,
            "consequences": self.consequences,
            "timeout_seconds": self.timeout_seconds,
            "default_option": self.default_option,
            "reversible": self.reversible,
            "reversal_cost": self.reversal_cost,
            "context": self.context,
            "selected_option": self.selected_option,
            "selected_by": self.selected_by,
            "selected_at": self.selected_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DecisionCard":
        """Create from dictionary."""
        return cls(
            meta=ContractMeta.from_dict(data.get("meta", {})),
            card_id=data.get("card_id", ""),
            timestamp=data.get("timestamp", ""),
            decision_type=DecisionType(data.get("decision_type", "tech_choice")),
            question=data.get("question", ""),
            options=[DecisionOption.from_dict(o) for o in data.get("options", [])],
            recommendation=data.get("recommendation"),
            recommendation_reason=data.get("recommendation_reason", ""),
            consequences=data.get("consequences", {}),
            timeout_seconds=data.get("timeout_seconds", 300),
            default_option=data.get("default_option"),
            reversible=data.get("reversible", True),
            reversal_cost=data.get("reversal_cost", "low"),
            context=data.get("context", {}),
            selected_option=data.get("selected_option"),
            selected_by=data.get("selected_by"),
            selected_at=data.get("selected_at"),
        )

    def select(self, option_id: str, by: str = "user") -> None:
        """Record a decision selection."""
        self.selected_option = option_id
        self.selected_by = by
        self.selected_at = datetime.utcnow().isoformat()

    def is_decided(self) -> bool:
        """Check if decision has been made."""
        return self.selected_option is not None

    def validate(self) -> List[str]:
        """Validate the decision card."""
        errors = []

        if not self.card_id:
            errors.append("card_id is required")

        if not self.question:
            errors.append("question is required")

        if len(self.options) < 2:
            errors.append("At least 2 options required")

        option_ids = [o.option_id for o in self.options]
        if self.recommendation and self.recommendation not in option_ids:
            errors.append(f"recommendation '{self.recommendation}' not in options")

        if self.default_option and self.default_option not in option_ids:
            errors.append(f"default_option '{self.default_option}' not in options")

        return errors


class DecisionCardBuilder:
    """Builder for creating decision cards."""

    @staticmethod
    def for_tech_choice(
        card_id: str,
        question: str,
        options: List[Dict[str, Any]],
        recommendation: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> DecisionCard:
        """Create a tech choice decision card."""
        return DecisionCard(
            card_id=card_id,
            decision_type=DecisionType.TECH_CHOICE,
            question=question,
            options=[
                DecisionOption(
                    option_id=opt["id"],
                    label=opt["label"],
                    description=opt.get("description", ""),
                    pros=opt.get("pros", []),
                    cons=opt.get("cons", []),
                )
                for opt in options
            ],
            recommendation=recommendation,
            context=context or {},
        )

    @staticmethod
    def for_risk_confirmation(
        card_id: str,
        action: str,
        risk_description: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> DecisionCard:
        """Create a risk confirmation decision card."""
        return DecisionCard(
            card_id=card_id,
            decision_type=DecisionType.RISK_CONFIRMATION,
            question=f"Are you sure you want to: {action}?",
            options=[
                DecisionOption(
                    option_id="confirm",
                    label="Confirm",
                    description=risk_description,
                    risk_level="high",
                ),
                DecisionOption(
                    option_id="cancel",
                    label="Cancel",
                    description="Do not perform this action",
                    risk_level="low",
                ),
            ],
            reversible=False,
            reversal_cost="high",
            context=context or {},
        )

    @staticmethod
    def for_approval(
        card_id: str,
        what: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> DecisionCard:
        """Create an approval decision card."""
        return DecisionCard(
            card_id=card_id,
            decision_type=DecisionType.APPROVAL,
            question=f"Do you approve: {what}?",
            options=[
                DecisionOption(
                    option_id="approve",
                    label="Approve",
                    description="Accept this result",
                ),
                DecisionOption(
                    option_id="reject",
                    label="Reject",
                    description="Reject and try again",
                ),
                DecisionOption(
                    option_id="modify",
                    label="Modify",
                    description="Make changes before proceeding",
                ),
            ],
            context=context or {},
        )


# JSON Schema for validation
DECISION_CARD_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "card_id": {"type": "string", "minLength": 1},
        "timestamp": {"type": "string"},
        "decision_type": {
            "enum": [
                "tech_choice",
                "risk_confirmation",
                "direction_change",
                "approval",
                "clarification",
            ]
        },
        "question": {"type": "string", "minLength": 1},
        "options": {
            "type": "array",
            "minItems": 2,
            "items": {
                "type": "object",
                "properties": {
                    "option_id": {"type": "string"},
                    "label": {"type": "string"},
                    "description": {"type": "string"},
                    "technical_detail": {"type": "string"},
                    "pros": {"type": "array", "items": {"type": "string"}},
                    "cons": {"type": "array", "items": {"type": "string"}},
                    "risk_level": {"enum": ["low", "medium", "high"]},
                    "estimated_effort": {"type": "string"},
                },
                "required": ["option_id", "label"],
            },
        },
        "recommendation": {"type": ["string", "null"]},
        "recommendation_reason": {"type": "string"},
        "timeout_seconds": {"type": "integer", "minimum": 0},
        "default_option": {"type": ["string", "null"]},
        "reversible": {"type": "boolean"},
        "reversal_cost": {"enum": ["low", "medium", "high"]},
    },
    "required": ["card_id", "question", "options"],
}
