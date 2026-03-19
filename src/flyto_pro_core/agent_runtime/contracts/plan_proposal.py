"""
Plan Proposal - Multi-Agent interface for plan submission.

This is the standardized format for AI #1 (Planner) to submit plans
to AI #2 (Executor) for review and execution.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .contract_meta import ContractMeta
from .plan_contract import Assertion, PlanContract


class ProposalStatus(Enum):
    """Status of a plan proposal."""

    DRAFT = "draft"  # Being created
    SUBMITTED = "submitted"  # Awaiting review
    APPROVED = "approved"  # Approved for execution
    REJECTED = "rejected"  # Rejected
    EXECUTING = "executing"  # Currently executing
    COMPLETED = "completed"  # Execution completed
    FAILED = "failed"  # Execution failed


class ProposalPriority(Enum):
    """Priority of a proposal."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class ProposalMetadata:
    """Metadata about the proposal."""

    # Source AI
    source_agent_id: str = ""
    source_agent_type: str = ""  # "planner", "analyzer", etc.
    source_model: str = ""

    # Target AI
    target_agent_id: str = ""
    target_agent_type: str = ""  # "executor", "verifier", etc.

    # Context
    conversation_id: str = ""
    user_id: str = ""
    session_id: str = ""

    # Intent
    original_user_request: str = ""
    interpreted_intent: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_agent_id": self.source_agent_id,
            "source_agent_type": self.source_agent_type,
            "source_model": self.source_model,
            "target_agent_id": self.target_agent_id,
            "target_agent_type": self.target_agent_type,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "original_user_request": self.original_user_request,
            "interpreted_intent": self.interpreted_intent,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProposalMetadata":
        return cls(
            source_agent_id=data.get("source_agent_id", ""),
            source_agent_type=data.get("source_agent_type", ""),
            source_model=data.get("source_model", ""),
            target_agent_id=data.get("target_agent_id", ""),
            target_agent_type=data.get("target_agent_type", ""),
            conversation_id=data.get("conversation_id", ""),
            user_id=data.get("user_id", ""),
            session_id=data.get("session_id", ""),
            original_user_request=data.get("original_user_request", ""),
            interpreted_intent=data.get("interpreted_intent", ""),
        )


@dataclass
class ProposalRevision:
    """A revision of a proposal."""

    revision_id: str = ""
    revision_number: int = 0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    reason: str = ""  # Why was this revision created
    changes: List[str] = field(default_factory=list)  # What changed
    previous_revision_id: str = ""

    def __post_init__(self):
        if not self.revision_id:
            self.revision_id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "revision_id": self.revision_id,
            "revision_number": self.revision_number,
            "created_at": self.created_at,
            "reason": self.reason,
            "changes": self.changes,
            "previous_revision_id": self.previous_revision_id,
        }


@dataclass
class ProposalFeedback:
    """Feedback on a proposal."""

    feedback_id: str = ""
    feedback_type: str = ""  # "approval", "rejection", "suggestion"
    message: str = ""
    suggestions: List[str] = field(default_factory=list)
    created_by: str = ""  # "user", "executor_ai", "verifier_ai"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def __post_init__(self):
        if not self.feedback_id:
            self.feedback_id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feedback_id": self.feedback_id,
            "feedback_type": self.feedback_type,
            "message": self.message,
            "suggestions": self.suggestions,
            "created_by": self.created_by,
            "created_at": self.created_at,
        }


@dataclass
class PlanProposal:
    """
    A plan proposal from AI #1 to AI #2.

    This is the standardized interface for multi-agent communication.
    AI #1 (Planner) creates proposals, AI #2 (Executor) reviews and executes.
    """

    # Metadata
    meta: ContractMeta = field(
        default_factory=lambda: ContractMeta(
            contract_name="PlanProposal",
            version="1.0.0",
            compatible_with=["^1.0"],
        )
    )

    # Identity
    proposal_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = ""

    # Status
    status: ProposalStatus = ProposalStatus.DRAFT
    priority: ProposalPriority = ProposalPriority.NORMAL

    # Source metadata
    proposal_metadata: ProposalMetadata = field(default_factory=ProposalMetadata)

    # The plan itself
    plan: PlanContract = field(default_factory=PlanContract)

    # Human-readable summary
    title: str = ""
    summary: str = ""
    estimated_steps: int = 0
    estimated_duration_ms: int = 0

    # Risk assessment
    risk_level: str = "low"  # low, medium, high, critical
    risk_factors: List[str] = field(default_factory=list)
    requires_user_approval: bool = False

    # Revisions
    current_revision: int = 0
    revisions: List[ProposalRevision] = field(default_factory=list)

    # Feedback
    feedback: List[ProposalFeedback] = field(default_factory=list)

    # Execution tracking
    execution_started_at: Optional[str] = None
    execution_completed_at: Optional[str] = None
    execution_result: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not self.proposal_id:
            self.proposal_id = str(uuid.uuid4())[:12]
        if not self.updated_at:
            self.updated_at = self.created_at

    def submit(self) -> None:
        """Submit the proposal for review."""
        self.status = ProposalStatus.SUBMITTED
        self.updated_at = datetime.utcnow().isoformat()

    def approve(self, by: str = "user") -> None:
        """Approve the proposal."""
        self.status = ProposalStatus.APPROVED
        self.updated_at = datetime.utcnow().isoformat()
        self.add_feedback(
            feedback_type="approval",
            message="Proposal approved",
            created_by=by,
        )

    def reject(self, reason: str, by: str = "user") -> None:
        """Reject the proposal."""
        self.status = ProposalStatus.REJECTED
        self.updated_at = datetime.utcnow().isoformat()
        self.add_feedback(
            feedback_type="rejection",
            message=reason,
            created_by=by,
        )

    def start_execution(self) -> None:
        """Mark execution as started."""
        self.status = ProposalStatus.EXECUTING
        self.execution_started_at = datetime.utcnow().isoformat()
        self.updated_at = self.execution_started_at

    def complete_execution(self, success: bool, result: Dict[str, Any]) -> None:
        """Mark execution as completed."""
        self.status = ProposalStatus.COMPLETED if success else ProposalStatus.FAILED
        self.execution_completed_at = datetime.utcnow().isoformat()
        self.execution_result = result
        self.updated_at = self.execution_completed_at

    def add_revision(self, reason: str, changes: List[str]) -> ProposalRevision:
        """Add a new revision."""
        previous_id = self.revisions[-1].revision_id if self.revisions else ""
        revision = ProposalRevision(
            revision_number=self.current_revision + 1,
            reason=reason,
            changes=changes,
            previous_revision_id=previous_id,
        )
        self.revisions.append(revision)
        self.current_revision = revision.revision_number
        self.updated_at = revision.created_at
        return revision

    def add_feedback(
        self,
        feedback_type: str,
        message: str,
        created_by: str = "user",
        suggestions: Optional[List[str]] = None,
    ) -> ProposalFeedback:
        """Add feedback to the proposal."""
        feedback = ProposalFeedback(
            feedback_type=feedback_type,
            message=message,
            suggestions=suggestions or [],
            created_by=created_by,
        )
        self.feedback.append(feedback)
        return feedback

    def to_dict(self) -> Dict[str, Any]:
        return {
            "meta": self.meta.to_dict(),
            "proposal_id": self.proposal_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status.value,
            "priority": self.priority.value,
            "proposal_metadata": self.proposal_metadata.to_dict(),
            "plan": self.plan.to_dict(),
            "title": self.title,
            "summary": self.summary,
            "estimated_steps": self.estimated_steps,
            "estimated_duration_ms": self.estimated_duration_ms,
            "risk_level": self.risk_level,
            "risk_factors": self.risk_factors,
            "requires_user_approval": self.requires_user_approval,
            "current_revision": self.current_revision,
            "revisions": [r.to_dict() for r in self.revisions],
            "feedback": [f.to_dict() for f in self.feedback],
            "execution_started_at": self.execution_started_at,
            "execution_completed_at": self.execution_completed_at,
            "execution_result": self.execution_result,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlanProposal":
        return cls(
            meta=ContractMeta.from_dict(data.get("meta", {})),
            proposal_id=data.get("proposal_id", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            status=ProposalStatus(data.get("status", "draft")),
            priority=ProposalPriority(data.get("priority", "normal")),
            proposal_metadata=ProposalMetadata.from_dict(
                data.get("proposal_metadata", {})
            ),
            plan=PlanContract.from_dict(data.get("plan", {})),
            title=data.get("title", ""),
            summary=data.get("summary", ""),
            estimated_steps=data.get("estimated_steps", 0),
            estimated_duration_ms=data.get("estimated_duration_ms", 0),
            risk_level=data.get("risk_level", "low"),
            risk_factors=data.get("risk_factors", []),
            requires_user_approval=data.get("requires_user_approval", False),
            current_revision=data.get("current_revision", 0),
            revisions=[
                ProposalRevision(**r) for r in data.get("revisions", [])
            ],
            feedback=[
                ProposalFeedback(**f) for f in data.get("feedback", [])
            ],
            execution_started_at=data.get("execution_started_at"),
            execution_completed_at=data.get("execution_completed_at"),
            execution_result=data.get("execution_result"),
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get a compact summary."""
        return {
            "proposal_id": self.proposal_id,
            "title": self.title,
            "status": self.status.value,
            "priority": self.priority.value,
            "risk_level": self.risk_level,
            "requires_approval": self.requires_user_approval,
            "revisions": self.current_revision,
            "feedback_count": len(self.feedback),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class PlanProposalBuilder:
    """Builder for creating plan proposals."""

    def __init__(self):
        self._proposal = PlanProposal()

    def title(self, title: str) -> "PlanProposalBuilder":
        """Set title."""
        self._proposal.title = title
        return self

    def summary(self, summary: str) -> "PlanProposalBuilder":
        """Set summary."""
        self._proposal.summary = summary
        return self

    def plan(self, plan: PlanContract) -> "PlanProposalBuilder":
        """Set the plan."""
        self._proposal.plan = plan
        return self

    def from_agent(
        self,
        agent_id: str,
        agent_type: str = "planner",
        model: str = "",
    ) -> "PlanProposalBuilder":
        """Set source agent."""
        self._proposal.proposal_metadata.source_agent_id = agent_id
        self._proposal.proposal_metadata.source_agent_type = agent_type
        self._proposal.proposal_metadata.source_model = model
        return self

    def to_agent(
        self,
        agent_id: str,
        agent_type: str = "executor",
    ) -> "PlanProposalBuilder":
        """Set target agent."""
        self._proposal.proposal_metadata.target_agent_id = agent_id
        self._proposal.proposal_metadata.target_agent_type = agent_type
        return self

    def for_user(self, user_id: str) -> "PlanProposalBuilder":
        """Set user context."""
        self._proposal.proposal_metadata.user_id = user_id
        return self

    def with_request(
        self,
        original_request: str,
        interpreted_intent: str = "",
    ) -> "PlanProposalBuilder":
        """Set user request."""
        self._proposal.proposal_metadata.original_user_request = original_request
        self._proposal.proposal_metadata.interpreted_intent = (
            interpreted_intent or original_request
        )
        return self

    def priority(self, priority: ProposalPriority) -> "PlanProposalBuilder":
        """Set priority."""
        self._proposal.priority = priority
        return self

    def risk(
        self,
        level: str,
        factors: Optional[List[str]] = None,
    ) -> "PlanProposalBuilder":
        """Set risk level."""
        self._proposal.risk_level = level
        self._proposal.risk_factors = factors or []
        if level in ("high", "critical"):
            self._proposal.requires_user_approval = True
        return self

    def estimate(
        self,
        steps: int,
        duration_ms: int = 0,
    ) -> "PlanProposalBuilder":
        """Set estimates."""
        self._proposal.estimated_steps = steps
        self._proposal.estimated_duration_ms = duration_ms
        return self

    def require_approval(self, required: bool = True) -> "PlanProposalBuilder":
        """Set approval requirement."""
        self._proposal.requires_user_approval = required
        return self

    def build(self) -> PlanProposal:
        """Build the proposal."""
        return self._proposal


# JSON Schema for validation
PLAN_PROPOSAL_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "proposal_id": {"type": "string"},
        "status": {
            "enum": ["draft", "submitted", "approved", "rejected", "executing", "completed", "failed"]
        },
        "priority": {"enum": ["low", "normal", "high", "urgent"]},
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "plan": {"type": "object"},
        "risk_level": {"enum": ["low", "medium", "high", "critical"]},
        "requires_user_approval": {"type": "boolean"},
    },
    "required": ["proposal_id", "plan"],
}
