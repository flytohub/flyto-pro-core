"""
Verification Report - Deterministic verification result.

This is NOT LLM judgment. It's based on evidence.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..contracts.contract_meta import ContractMeta
from ..contracts.plan_contract import AssertionLevel


@dataclass
class AssertionResult:
    """Result of a single assertion."""

    assertion_id: str
    assertion_type: str
    expression: str
    expected: Any
    actual: Any
    passed: bool
    level: AssertionLevel = AssertionLevel.HARD
    threshold: Optional[float] = None
    score: Optional[float] = None  # For soft assertions: similarity score
    error_message: Optional[str] = None
    execution_time_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "assertion_id": self.assertion_id,
            "assertion_type": self.assertion_type,
            "expression": self.expression,
            "expected": self.expected,
            "actual": self.actual,
            "passed": self.passed,
            "level": self.level.value,
            "threshold": self.threshold,
            "score": self.score,
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AssertionResult":
        """Create from dictionary."""
        return cls(
            assertion_id=data["assertion_id"],
            assertion_type=data["assertion_type"],
            expression=data["expression"],
            expected=data.get("expected"),
            actual=data.get("actual"),
            passed=data["passed"],
            level=AssertionLevel(data.get("level", "hard")),
            threshold=data.get("threshold"),
            score=data.get("score"),
            error_message=data.get("error_message"),
            execution_time_ms=data.get("execution_time_ms", 0),
        )


@dataclass
class Evidence:
    """Evidence supporting verification."""

    evidence_id: str
    evidence_type: str  # screenshot, db_snapshot, console_log, etc.
    timestamp: str
    data: Any  # Actual content or path
    hash: str  # For reproducibility verification

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "timestamp": self.timestamp,
            "data": self.data,
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Evidence":
        """Create from dictionary."""
        return cls(
            evidence_id=data["evidence_id"],
            evidence_type=data["evidence_type"],
            timestamp=data["timestamp"],
            data=data.get("data"),
            hash=data.get("hash", ""),
        )


@dataclass
class FailureAnalysis:
    """Analysis of verification failure."""

    failure_type: str  # assertion_failed, timeout, exception, etc.
    root_cause: str  # Deterministic analysis, not LLM guess
    affected_assertions: List[str]
    suggested_fix: Optional[str] = None  # From EMS
    ems_match: Optional[str] = None  # Matched EMS pattern

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "failure_type": self.failure_type,
            "root_cause": self.root_cause,
            "affected_assertions": self.affected_assertions,
            "suggested_fix": self.suggested_fix,
            "ems_match": self.ems_match,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FailureAnalysis":
        """Create from dictionary."""
        return cls(
            failure_type=data["failure_type"],
            root_cause=data["root_cause"],
            affected_assertions=data.get("affected_assertions", []),
            suggested_fix=data.get("suggested_fix"),
            ems_match=data.get("ems_match"),
        )


class VerificationRules:
    """
    Deterministic rules for calculating verification results.

    These rules are fixed and do not depend on LLM.
    """

    # Minimum soft assertion pass rate to pass overall
    SOFT_PASS_RATE_THRESHOLD = 0.8

    @staticmethod
    def calculate_passed(assertions: List[AssertionResult]) -> bool:
        """
        Calculate if verification passed.

        Rules:
        1. All HARD assertions must pass 100%
        2. SOFT assertions must have pass rate >= threshold
        """
        if not assertions:
            return True

        hard_assertions = [a for a in assertions if a.level == AssertionLevel.HARD]
        soft_assertions = [a for a in assertions if a.level == AssertionLevel.SOFT]

        # HARD must all pass
        if hard_assertions and not all(a.passed for a in hard_assertions):
            return False

        # SOFT must meet threshold
        if soft_assertions:
            pass_rate = sum(1 for a in soft_assertions if a.passed) / len(
                soft_assertions
            )
            if pass_rate < VerificationRules.SOFT_PASS_RATE_THRESHOLD:
                return False

        return True

    @staticmethod
    def calculate_confidence(assertions: List[AssertionResult]) -> float:
        """
        Calculate confidence score.

        Formula:
        - Base score: 0.5 if all HARD pass, 0 otherwise
        - SOFT contribution: 0.5 * (weighted soft pass rate)
        """
        if not assertions:
            return 1.0

        hard_assertions = [a for a in assertions if a.level == AssertionLevel.HARD]
        soft_assertions = [a for a in assertions if a.level == AssertionLevel.SOFT]

        # Base score from HARD assertions
        if hard_assertions:
            hard_pass = all(a.passed for a in hard_assertions)
            base_score = 0.5 if hard_pass else 0.0
        else:
            base_score = 0.5

        # SOFT contribution
        if soft_assertions:
            total_weight = sum(1.0 for _ in soft_assertions)  # Equal weight
            weighted_pass = sum(
                (a.score if a.score is not None else (1.0 if a.passed else 0.0))
                for a in soft_assertions
            )
            soft_score = 0.5 * (weighted_pass / total_weight)
        else:
            soft_score = 0.5

        return min(1.0, base_score + soft_score)


@dataclass
class VerificationReport:
    """
    Deterministic verification report.

    This is the output of verification - based on evidence, not LLM.
    """

    # Metadata
    meta: ContractMeta = field(
        default_factory=lambda: ContractMeta(
            contract_name="VerificationReport",
            version="1.0.0",
            compatible_with=["^1.0"],
        )
    )

    # Identity
    verification_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Overall result
    passed: bool = False
    confidence: float = 0.0

    # Assertion results
    assertions: List[AssertionResult] = field(default_factory=list)

    # Evidence chain
    evidence: List[Evidence] = field(default_factory=list)

    # Failure analysis (if any)
    failure_analysis: Optional[FailureAnalysis] = None

    # Execution stats
    execution_time_ms: int = 0
    observation_id: Optional[str] = None  # Link to ObservationPacket

    def __post_init__(self):
        """Calculate passed and confidence after init."""
        if self.assertions and not self.passed:
            self.passed = VerificationRules.calculate_passed(self.assertions)
            self.confidence = VerificationRules.calculate_confidence(self.assertions)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "meta": self.meta.to_dict(),
            "verification_id": self.verification_id,
            "timestamp": self.timestamp,
            "passed": self.passed,
            "confidence": self.confidence,
            "assertions": [a.to_dict() for a in self.assertions],
            "evidence": [e.to_dict() for e in self.evidence],
            "failure_analysis": (
                self.failure_analysis.to_dict() if self.failure_analysis else None
            ),
            "execution_time_ms": self.execution_time_ms,
            "observation_id": self.observation_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerificationReport":
        """Create from dictionary."""
        return cls(
            meta=ContractMeta.from_dict(data.get("meta", {})),
            verification_id=data.get("verification_id", ""),
            timestamp=data.get("timestamp", ""),
            passed=data.get("passed", False),
            confidence=data.get("confidence", 0.0),
            assertions=[
                AssertionResult.from_dict(a) for a in data.get("assertions", [])
            ],
            evidence=[Evidence.from_dict(e) for e in data.get("evidence", [])],
            failure_analysis=(
                FailureAnalysis.from_dict(data["failure_analysis"])
                if data.get("failure_analysis")
                else None
            ),
            execution_time_ms=data.get("execution_time_ms", 0),
            observation_id=data.get("observation_id"),
        )

    def get_failed_assertions(self) -> List[AssertionResult]:
        """Get all failed assertions."""
        return [a for a in self.assertions if not a.passed]

    def get_hard_failures(self) -> List[AssertionResult]:
        """Get failed HARD assertions."""
        return [
            a
            for a in self.assertions
            if not a.passed and a.level == AssertionLevel.HARD
        ]

    def get_soft_failures(self) -> List[AssertionResult]:
        """Get failed SOFT assertions."""
        return [
            a
            for a in self.assertions
            if not a.passed and a.level == AssertionLevel.SOFT
        ]

    def get_summary(self) -> Dict[str, Any]:
        """Get a compact summary."""
        return {
            "verification_id": self.verification_id,
            "passed": self.passed,
            "confidence": round(self.confidence, 3),
            "total_assertions": len(self.assertions),
            "passed_assertions": sum(1 for a in self.assertions if a.passed),
            "failed_assertions": sum(1 for a in self.assertions if not a.passed),
            "hard_failures": len(self.get_hard_failures()),
            "soft_failures": len(self.get_soft_failures()),
            "evidence_count": len(self.evidence),
            "has_failure_analysis": self.failure_analysis is not None,
        }

    def get_hash(self) -> str:
        """Get hash of report for integrity verification."""
        import json

        content = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:32]


# JSON Schema for validation
VERIFICATION_REPORT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "verification_id": {"type": "string"},
        "timestamp": {"type": "string"},
        "passed": {"type": "boolean"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "assertions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "assertion_id": {"type": "string"},
                    "assertion_type": {"type": "string"},
                    "passed": {"type": "boolean"},
                    "level": {"enum": ["hard", "soft"]},
                },
                "required": ["assertion_id", "passed"],
            },
        },
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "evidence_id": {"type": "string"},
                    "evidence_type": {"type": "string"},
                    "hash": {"type": "string"},
                },
            },
        },
        "failure_analysis": {
            "type": ["object", "null"],
            "properties": {
                "failure_type": {"type": "string"},
                "root_cause": {"type": "string"},
            },
        },
    },
    "required": ["verification_id", "passed"],
}
