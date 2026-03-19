"""
Verification Adapter - Bridges new verification with existing VerificationGate.

Provides adapters to convert between:
- Assertion <-> Goal (existing system)
- VerificationReport <-> VerificationResult (existing system)
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..contracts import (
    Assertion,
    AssertionType,
    AssertionLevel,
)
from ..verification import (
    VerificationReport,
    AssertionResult,
)

logger = logging.getLogger(__name__)


def adapt_assertion_to_goal(assertion: Assertion) -> Dict[str, Any]:
    """
    Convert an Assertion to the existing goal format.

    The existing GoalChecker uses a different format:
    {
        "type": "MATCH" | "EXISTS" | "COUNT" | etc.,
        "target": "...",
        "expected": ...,
        "threshold": ...,
    }
    """
    # Map assertion types to goal types
    type_mapping = {
        AssertionType.EQUALS: "MATCH",
        AssertionType.CONTAINS: "MATCH",
        AssertionType.EXISTS: "EXISTS",
        AssertionType.NOT_EXISTS: "NOT_EXISTS",
        AssertionType.GREATER_THAN: "THRESHOLD",
        AssertionType.LESS_THAN: "THRESHOLD",
        AssertionType.REGEX_MATCH: "MATCH",
        AssertionType.CUSTOM: "CUSTOM",
    }

    goal_type = type_mapping.get(assertion.assertion_type, "CUSTOM")

    return {
        "goal_id": assertion.assertion_id,
        "type": goal_type,
        "target": assertion.expression,
        "expected": assertion.expected_value,
        "threshold": assertion.threshold,
        "level": assertion.level.value,
        "metadata": {
            "original_type": assertion.assertion_type.value,
            "description": assertion.description,
        },
    }


def adapt_goal_to_assertion(goal: Dict[str, Any]) -> Assertion:
    """
    Convert an existing goal format to Assertion.
    """
    # Reverse type mapping
    type_mapping = {
        "MATCH": AssertionType.CONTAINS,
        "EXISTS": AssertionType.EXISTS,
        "NOT_EXISTS": AssertionType.NOT_EXISTS,
        "THRESHOLD": AssertionType.GREATER_THAN,
        "COUNT": AssertionType.EQUALS,
        "SIZE": AssertionType.EQUALS,
        "SCHEMA": AssertionType.CUSTOM,
        "STATE_CHANGE": AssertionType.CUSTOM,
        "ALL": AssertionType.CUSTOM,
        "ANY": AssertionType.CUSTOM,
    }

    goal_type = goal.get("type", "CUSTOM")
    assertion_type = type_mapping.get(goal_type, AssertionType.CUSTOM)

    # Check metadata for original type
    metadata = goal.get("metadata", {})
    if "original_type" in metadata:
        try:
            assertion_type = AssertionType(metadata["original_type"])
        except ValueError:
            pass

    level_str = goal.get("level", "hard")
    level = AssertionLevel.HARD if level_str == "hard" else AssertionLevel.SOFT

    return Assertion(
        assertion_id=goal.get("goal_id", ""),
        assertion_type=assertion_type,
        expression=goal.get("target", ""),
        expected_value=goal.get("expected"),
        threshold=goal.get("threshold"),
        level=level,
        description=metadata.get("description", ""),
    )


def adapt_assertion_result_to_goal_result(
    result: AssertionResult,
) -> Dict[str, Any]:
    """
    Convert AssertionResult to goal check result format.
    """
    return {
        "goal_id": result.assertion_id,
        "achieved": result.passed,
        "evidence": {
            "expected": result.expected,
            "actual": result.actual,
            "score": result.score,
            "error": result.error_message,
        },
        "execution_time_ms": result.execution_time_ms,
    }


class VerificationAdapter:
    """
    Adapts between VerificationReport and existing VerificationGate.

    Usage:
        adapter = VerificationAdapter(verification_gate)

        # Convert new report to existing format
        gate_result = adapter.to_gate_format(report)

        # Update gate with our verification
        await adapter.update_gate(report)
    """

    def __init__(self, verification_gate=None):
        """
        Initialize adapter.

        Args:
            verification_gate: Existing VerificationGate instance (optional)
        """
        self._gate = verification_gate

    def to_gate_format(
        self,
        report: VerificationReport,
    ) -> Dict[str, Any]:
        """
        Convert VerificationReport to gate's expected format.
        """
        return {
            "verification_id": report.verification_id,
            "timestamp": report.timestamp,
            "success": report.passed,
            "confidence": report.confidence,
            "evidence": {
                "assertions": len(report.assertions),
                "passed": sum(1 for a in report.assertions if a.passed),
                "failed": sum(1 for a in report.assertions if not a.passed),
                "evidence_count": len(report.evidence),
            },
            "details": {
                "hard_failures": len(report.get_hard_failures()),
                "soft_failures": len(report.get_soft_failures()),
                "failure_analysis": (
                    report.failure_analysis.to_dict()
                    if report.failure_analysis
                    else None
                ),
            },
            "execution_time_ms": report.execution_time_ms,
            "observation_id": report.observation_id,
        }

    async def update_gate(
        self,
        report: VerificationReport,
        item_key: str,
    ) -> bool:
        """
        Update the existing VerificationGate with our verification result.

        This bridges the new deterministic verification with the existing
        trust-based verification system.
        """
        if not self._gate:
            logger.warning("No verification gate configured")
            return False

        try:
            # Record execution result to gate
            await self._gate.record_execution_result(
                key=item_key,
                success=report.passed,
                execution_evidence={
                    "verification_id": report.verification_id,
                    "confidence": report.confidence,
                    "assertions": [a.to_dict() for a in report.assertions],
                    "evidence": [e.to_dict() for e in report.evidence],
                },
            )

            logger.info(
                f"Updated verification gate for {item_key}: "
                f"{'success' if report.passed else 'failure'}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to update verification gate: {e}")
            return False

    def from_gate_format(
        self,
        gate_result: Dict[str, Any],
    ) -> VerificationReport:
        """
        Convert gate result to VerificationReport.

        Useful for reading existing verification results.
        """
        assertions = []

        # Extract assertion results if available
        evidence = gate_result.get("evidence", {})
        if isinstance(evidence, dict):
            # Create synthetic assertion results
            passed_count = evidence.get("passed", 0)
            failed_count = evidence.get("failed", 0)

            for i in range(passed_count):
                assertions.append(
                    AssertionResult(
                        assertion_id=f"gate-pass-{i}",
                        assertion_type="gate",
                        expression="",
                        expected=None,
                        actual=None,
                        passed=True,
                        level=AssertionLevel.HARD,
                    )
                )

            for i in range(failed_count):
                assertions.append(
                    AssertionResult(
                        assertion_id=f"gate-fail-{i}",
                        assertion_type="gate",
                        expression="",
                        expected=None,
                        actual=None,
                        passed=False,
                        level=AssertionLevel.HARD,
                    )
                )

        return VerificationReport(
            verification_id=gate_result.get("verification_id", ""),
            timestamp=gate_result.get("timestamp", ""),
            passed=gate_result.get("success", False),
            confidence=gate_result.get("confidence", 0.0),
            assertions=assertions,
            execution_time_ms=gate_result.get("execution_time_ms", 0),
        )


def merge_verifications(
    deterministic: VerificationReport,
    trust_based: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Merge deterministic and trust-based verification results.

    The final result combines:
    - Deterministic assertions (from DeterministicVerifier)
    - Trust level (from VerificationGate)
    - Evidence (from both)

    Returns combined result for final decision.
    """
    trust_level = trust_based.get("trust_level", 0.0)
    gate_success = trust_based.get("success", False)

    # Combined confidence: weight deterministic more heavily
    combined_confidence = (
        deterministic.confidence * 0.7 +
        trust_level * 0.3
    )

    # Final decision: deterministic has veto power
    final_passed = deterministic.passed and (
        gate_success or trust_level >= 0.5
    )

    return {
        "passed": final_passed,
        "confidence": combined_confidence,
        "deterministic": {
            "passed": deterministic.passed,
            "confidence": deterministic.confidence,
            "hard_failures": len(deterministic.get_hard_failures()),
            "soft_failures": len(deterministic.get_soft_failures()),
        },
        "trust_based": {
            "passed": gate_success,
            "trust_level": trust_level,
        },
        "evidence": {
            "deterministic_evidence": len(deterministic.evidence),
            "trust_evidence": len(trust_based.get("evidence", [])),
        },
        "recommendation": (
            "proceed" if final_passed else
            "retry" if combined_confidence > 0.5 else
            "abort"
        ),
    }
