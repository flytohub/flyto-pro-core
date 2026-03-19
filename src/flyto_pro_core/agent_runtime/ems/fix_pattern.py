"""
Fix Pattern - Verified behavior corrections with lifecycle.

Fix patterns go through a lifecycle:
1. pending - Proposed fix, not yet verified
2. testing - Being tested
3. active - Verified and in use
4. deprecated - Superseded by newer pattern
5. rejected - Did not work

Each pattern tracks side effects to prevent regressions.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .error_signature import ErrorSignature


class FixPatternStatus(Enum):
    """Lifecycle status of a fix pattern."""

    PENDING = "pending"  # Proposed, not verified
    TESTING = "testing"  # Being tested
    ACTIVE = "active"  # Verified and in use
    DEPRECATED = "deprecated"  # Superseded
    REJECTED = "rejected"  # Did not work


class FixPatternScope(Enum):
    """Scope of fix pattern applicability."""

    GLOBAL = "global"  # Applies everywhere
    PROJECT = "project"  # Project-specific
    ENVIRONMENT = "environment"  # Environment-specific (dev/staging/prod)
    MODULE = "module"  # Specific to a module


class SideEffectType(Enum):
    """Types of side effects a fix may have."""

    FILE_CREATE = "file_create"
    FILE_MODIFY = "file_modify"
    FILE_DELETE = "file_delete"
    DB_INSERT = "db_insert"
    DB_UPDATE = "db_update"
    DB_DELETE = "db_delete"
    CONFIG_CHANGE = "config_change"
    DEPENDENCY_ADD = "dependency_add"
    DEPENDENCY_REMOVE = "dependency_remove"
    PERMISSION_CHANGE = "permission_change"
    NETWORK_CALL = "network_call"
    CACHE_INVALIDATE = "cache_invalidate"


@dataclass
class SideEffect:
    """
    A recorded side effect of applying a fix.

    Side effects help predict what will happen when a fix is applied.
    """

    effect_id: str = ""
    effect_type: SideEffectType = SideEffectType.FILE_MODIFY
    target: str = ""  # File path, table name, etc.
    description: str = ""
    reversible: bool = True
    severity: str = "low"  # low, medium, high
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.effect_id:
            self.effect_id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "effect_id": self.effect_id,
            "effect_type": self.effect_type.value,
            "target": self.target,
            "description": self.description,
            "reversible": self.reversible,
            "severity": self.severity,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SideEffect":
        return cls(
            effect_id=data.get("effect_id", ""),
            effect_type=SideEffectType(data.get("effect_type", "file_modify")),
            target=data.get("target", ""),
            description=data.get("description", ""),
            reversible=data.get("reversible", True),
            severity=data.get("severity", "low"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class FixAction:
    """An action that constitutes a fix."""

    action_id: str = ""
    action_type: str = ""  # module_call, code_change, config_update, etc.
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    order: int = 0

    def __post_init__(self):
        if not self.action_id:
            self.action_id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "description": self.description,
            "parameters": self.parameters,
            "order": self.order,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FixAction":
        return cls(
            action_id=data.get("action_id", ""),
            action_type=data.get("action_type", ""),
            description=data.get("description", ""),
            parameters=data.get("parameters", {}),
            order=data.get("order", 0),
        )


@dataclass
class FixPattern:
    """
    A verified fix pattern for an error.

    This is the core of EMS - patterns that HAVE BEEN VERIFIED to work.
    """

    # Identity
    pattern_id: str = ""
    name: str = ""
    description: str = ""

    # Matching
    error_signature: ErrorSignature = field(default_factory=ErrorSignature)
    additional_conditions: List[str] = field(default_factory=list)

    # Fix definition
    actions: List[FixAction] = field(default_factory=list)

    # Side effects
    side_effects: List[SideEffect] = field(default_factory=list)
    requires_confirmation: bool = False

    # Lifecycle
    status: FixPatternStatus = FixPatternStatus.PENDING
    scope: FixPatternScope = FixPatternScope.PROJECT

    # Scope context
    project_id: Optional[str] = None
    environment: Optional[str] = None
    module_id: Optional[str] = None

    # Statistics
    times_applied: int = 0
    times_succeeded: int = 0
    times_failed: int = 0
    last_applied: Optional[str] = None

    # History
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    created_by: str = ""  # user or ai
    verified_at: Optional[str] = None
    deprecated_at: Optional[str] = None
    superseded_by: Optional[str] = None

    # Metadata
    tags: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    related_patterns: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.pattern_id:
            self.pattern_id = str(uuid.uuid4())[:12]

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.times_succeeded + self.times_failed
        if total == 0:
            return 0.0
        return self.times_succeeded / total

    def matches(self, signature: ErrorSignature) -> bool:
        """Check if this pattern matches an error."""
        if self.status not in (FixPatternStatus.ACTIVE, FixPatternStatus.TESTING):
            return False

        matches, score = self.error_signature.matches(signature)
        return matches

    def record_application(self, succeeded: bool) -> None:
        """Record an application of this pattern."""
        self.times_applied += 1
        if succeeded:
            self.times_succeeded += 1
        else:
            self.times_failed += 1
        self.last_applied = datetime.utcnow().isoformat()

    def promote_to_active(self) -> None:
        """Promote pattern from pending/testing to active."""
        if self.status in (FixPatternStatus.PENDING, FixPatternStatus.TESTING):
            self.status = FixPatternStatus.ACTIVE
            self.verified_at = datetime.utcnow().isoformat()

    def deprecate(self, superseded_by: Optional[str] = None) -> None:
        """Deprecate this pattern."""
        self.status = FixPatternStatus.DEPRECATED
        self.deprecated_at = datetime.utcnow().isoformat()
        self.superseded_by = superseded_by

    def reject(self, reason: str = "") -> None:
        """Reject this pattern."""
        self.status = FixPatternStatus.REJECTED
        if reason:
            self.notes.append(f"Rejected: {reason}")

    def add_side_effect(self, effect: SideEffect) -> None:
        """Add a side effect."""
        self.side_effects.append(effect)
        # Auto-require confirmation for dangerous effects
        if effect.severity == "high" or not effect.reversible:
            self.requires_confirmation = True

    def get_dangerous_effects(self) -> List[SideEffect]:
        """Get dangerous or irreversible side effects."""
        return [
            e for e in self.side_effects
            if e.severity == "high" or not e.reversible
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "name": self.name,
            "description": self.description,
            "error_signature": self.error_signature.to_dict(),
            "additional_conditions": self.additional_conditions,
            "actions": [a.to_dict() for a in self.actions],
            "side_effects": [e.to_dict() for e in self.side_effects],
            "requires_confirmation": self.requires_confirmation,
            "status": self.status.value,
            "scope": self.scope.value,
            "project_id": self.project_id,
            "environment": self.environment,
            "module_id": self.module_id,
            "times_applied": self.times_applied,
            "times_succeeded": self.times_succeeded,
            "times_failed": self.times_failed,
            "last_applied": self.last_applied,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "verified_at": self.verified_at,
            "deprecated_at": self.deprecated_at,
            "superseded_by": self.superseded_by,
            "tags": self.tags,
            "notes": self.notes,
            "related_patterns": self.related_patterns,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FixPattern":
        return cls(
            pattern_id=data.get("pattern_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            error_signature=ErrorSignature.from_dict(
                data.get("error_signature", {})
            ),
            additional_conditions=data.get("additional_conditions", []),
            actions=[FixAction.from_dict(a) for a in data.get("actions", [])],
            side_effects=[
                SideEffect.from_dict(e) for e in data.get("side_effects", [])
            ],
            requires_confirmation=data.get("requires_confirmation", False),
            status=FixPatternStatus(data.get("status", "pending")),
            scope=FixPatternScope(data.get("scope", "project")),
            project_id=data.get("project_id"),
            environment=data.get("environment"),
            module_id=data.get("module_id"),
            times_applied=data.get("times_applied", 0),
            times_succeeded=data.get("times_succeeded", 0),
            times_failed=data.get("times_failed", 0),
            last_applied=data.get("last_applied"),
            created_at=data.get("created_at", ""),
            created_by=data.get("created_by", ""),
            verified_at=data.get("verified_at"),
            deprecated_at=data.get("deprecated_at"),
            superseded_by=data.get("superseded_by"),
            tags=data.get("tags", []),
            notes=data.get("notes", []),
            related_patterns=data.get("related_patterns", []),
        )


class FixPatternBuilder:
    """Fluent builder for FixPattern."""

    def __init__(self):
        self._pattern = FixPattern()

    def name(self, name: str) -> "FixPatternBuilder":
        """Set pattern name."""
        self._pattern.name = name
        return self

    def description(self, desc: str) -> "FixPatternBuilder":
        """Set description."""
        self._pattern.description = desc
        return self

    def for_error(self, signature: ErrorSignature) -> "FixPatternBuilder":
        """Set error signature to match."""
        self._pattern.error_signature = signature
        return self

    def condition(self, condition: str) -> "FixPatternBuilder":
        """Add additional condition."""
        self._pattern.additional_conditions.append(condition)
        return self

    def action(
        self,
        action_type: str,
        description: str = "",
        **params,
    ) -> "FixPatternBuilder":
        """Add an action."""
        self._pattern.actions.append(
            FixAction(
                action_type=action_type,
                description=description,
                parameters=params,
                order=len(self._pattern.actions),
            )
        )
        return self

    def side_effect(
        self,
        effect_type: SideEffectType,
        target: str,
        description: str = "",
        reversible: bool = True,
        severity: str = "low",
    ) -> "FixPatternBuilder":
        """Add a side effect."""
        self._pattern.add_side_effect(
            SideEffect(
                effect_type=effect_type,
                target=target,
                description=description,
                reversible=reversible,
                severity=severity,
            )
        )
        return self

    def scope(
        self,
        scope: FixPatternScope,
        project_id: Optional[str] = None,
        environment: Optional[str] = None,
        module_id: Optional[str] = None,
    ) -> "FixPatternBuilder":
        """Set scope."""
        self._pattern.scope = scope
        self._pattern.project_id = project_id
        self._pattern.environment = environment
        self._pattern.module_id = module_id
        return self

    def tag(self, tag: str) -> "FixPatternBuilder":
        """Add a tag."""
        self._pattern.tags.append(tag)
        return self

    def created_by(self, creator: str) -> "FixPatternBuilder":
        """Set creator."""
        self._pattern.created_by = creator
        return self

    def build(self) -> FixPattern:
        """Build the pattern."""
        return self._pattern
