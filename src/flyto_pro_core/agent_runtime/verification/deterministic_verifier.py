"""
Deterministic Verifier - Execute assertions against observations.

This is the core "kernel" that verifies LLM actions deterministically.
No LLM judgment here - only rule-based verification.
"""

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..contracts.plan_contract import Assertion, AssertionLevel, AssertionType
from ..observation.observation_packet import ObservationPacket
from .evidence_pipeline import DerivedEvidence, EvidencePipeline, get_evidence_pipeline
from .verification_report import (
    AssertionResult,
    Evidence,
    FailureAnalysis,
    VerificationReport,
    VerificationRules,
)

logger = logging.getLogger(__name__)


def _get_assertion_type_str(assertion_type: Any) -> str:
    """Get assertion type as string, whether it's an enum or string."""
    if hasattr(assertion_type, 'value'):
        return assertion_type.value
    return str(assertion_type)


@dataclass
class ExecutionContext:
    """Context for assertion execution."""

    observation: ObservationPacket
    variables: Dict[str, Any] = field(default_factory=dict)
    evidence_pipeline: Optional[EvidencePipeline] = None

    def get_value(self, path: str) -> Any:
        """
        Get value from observation using dot notation.

        Examples:
            "browser.url" -> observation.browser.url
            "database.tables.users.row_count" -> ...
        """
        parts = path.split(".")
        current: Any = self.observation

        for part in parts:
            if current is None:
                return None

            if hasattr(current, part):
                current = getattr(current, part)
            elif isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current


def _get_assertion_type_enum(assertion_type: Any) -> Optional[AssertionType]:
    """Convert assertion type to enum, whether it's already an enum or a string."""
    if isinstance(assertion_type, AssertionType):
        return assertion_type
    if isinstance(assertion_type, str):
        # Try to match by value
        for at in AssertionType:
            if at.value == assertion_type:
                return at
    return None


class AssertionExecutor:
    """
    Executes individual assertions.

    Each assertion type has a dedicated executor method.
    """

    def __init__(self):
        self._executors: Dict[AssertionType, Callable] = {
            AssertionType.EQUALS: self._execute_equals,
            AssertionType.CONTAINS: self._execute_contains,
            AssertionType.EXISTS: self._execute_exists,
            AssertionType.NOT_EXISTS: self._execute_not_exists,
            AssertionType.GREATER_THAN: self._execute_greater_than,
            AssertionType.LESS_THAN: self._execute_less_than,
            AssertionType.REGEX_MATCH: self._execute_regex_match,
            AssertionType.CUSTOM: self._execute_custom,
        }
        self._custom_executors: Dict[str, Callable] = {}

    def register_custom(
        self,
        name: str,
        executor: Callable[[ExecutionContext, Assertion], AssertionResult],
    ) -> None:
        """Register a custom assertion executor."""
        self._custom_executors[name] = executor

    def execute(
        self,
        assertion: Assertion,
        context: ExecutionContext,
    ) -> AssertionResult:
        """
        Execute a single assertion.

        Returns:
            AssertionResult with pass/fail and details
        """
        start_time = time.time()

        try:
            # Convert assertion_type to enum (handles both string and enum)
            assertion_type_enum = _get_assertion_type_enum(assertion.assertion_type)
            executor = self._executors.get(assertion_type_enum) if assertion_type_enum else None

            if not executor:
                return AssertionResult(
                    assertion_id=assertion.assertion_id,
                    assertion_type=_get_assertion_type_str(assertion.assertion_type),
                    expression=assertion.expression,
                    expected=assertion.expected,
                    actual=None,
                    passed=False,
                    level=assertion.level,
                    error_message=f"Unknown assertion type: {assertion.assertion_type}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            result = executor(context, assertion)
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            return result

        except Exception as e:
            logger.exception(f"Assertion execution failed: {assertion.assertion_id}")
            return AssertionResult(
                assertion_id=assertion.assertion_id,
                assertion_type=_get_assertion_type_str(assertion.assertion_type),
                expression=assertion.expression,
                expected=assertion.expected,
                actual=None,
                passed=False,
                level=assertion.level,
                error_message=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    def _execute_equals(
        self,
        context: ExecutionContext,
        assertion: Assertion,
    ) -> AssertionResult:
        """Execute equals assertion."""
        actual = context.get_value(assertion.expression)
        expected = assertion.expected
        threshold = assertion.threshold

        # Exact match
        if threshold is None:
            passed = actual == expected
            score = 1.0 if passed else 0.0
        else:
            # Threshold-based comparison
            if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
                diff = abs(actual - expected)
                max_val = max(abs(actual), abs(expected), 1)
                score = 1.0 - (diff / max_val)
                passed = score >= threshold
            elif isinstance(actual, str) and isinstance(expected, str):
                from difflib import SequenceMatcher

                score = SequenceMatcher(None, actual, expected).ratio()
                passed = score >= threshold
            else:
                passed = actual == expected
                score = 1.0 if passed else 0.0

        return AssertionResult(
            assertion_id=assertion.assertion_id,
            assertion_type=_get_assertion_type_str(assertion.assertion_type),
            expression=assertion.expression,
            expected=expected,
            actual=actual,
            passed=passed,
            level=assertion.level,
            threshold=threshold,
            score=score,
        )

    def _execute_contains(
        self,
        context: ExecutionContext,
        assertion: Assertion,
    ) -> AssertionResult:
        """Execute contains assertion."""
        actual = context.get_value(assertion.expression)
        expected = assertion.expected

        if actual is None:
            passed = False
        elif isinstance(actual, str):
            passed = str(expected) in actual
        elif isinstance(actual, (list, tuple)):
            passed = expected in actual
        elif isinstance(actual, dict):
            passed = expected in actual.values()
        else:
            passed = False

        return AssertionResult(
            assertion_id=assertion.assertion_id,
            assertion_type=_get_assertion_type_str(assertion.assertion_type),
            expression=assertion.expression,
            expected=expected,
            actual=actual,
            passed=passed,
            level=assertion.level,
        )

    def _execute_exists(
        self,
        context: ExecutionContext,
        assertion: Assertion,
    ) -> AssertionResult:
        """Execute exists assertion."""
        actual = context.get_value(assertion.expression)
        passed = actual is not None

        # For file checks
        if assertion.expression.startswith("filesystem."):
            if context.observation.filesystem:
                path = assertion.expected
                created = [
                    f.path for f in context.observation.filesystem.files_created
                ]
                modified = [
                    f.path for f in context.observation.filesystem.files_modified
                ]
                passed = path in created or path in modified

        return AssertionResult(
            assertion_id=assertion.assertion_id,
            assertion_type=_get_assertion_type_str(assertion.assertion_type),
            expression=assertion.expression,
            expected=True,
            actual=passed,
            passed=passed,
            level=assertion.level,
        )

    def _execute_not_exists(
        self,
        context: ExecutionContext,
        assertion: Assertion,
    ) -> AssertionResult:
        """Execute not_exists assertion."""
        actual = context.get_value(assertion.expression)
        passed = actual is None

        # For file checks
        if assertion.expression.startswith("filesystem."):
            if context.observation.filesystem:
                path = assertion.expected
                deleted = context.observation.filesystem.files_deleted
                passed = path in deleted

        return AssertionResult(
            assertion_id=assertion.assertion_id,
            assertion_type=_get_assertion_type_str(assertion.assertion_type),
            expression=assertion.expression,
            expected=False,
            actual=not passed,
            passed=passed,
            level=assertion.level,
        )

    def _execute_greater_than(
        self,
        context: ExecutionContext,
        assertion: Assertion,
    ) -> AssertionResult:
        """Execute greater_than assertion."""
        actual = context.get_value(assertion.expression)
        expected = assertion.expected

        try:
            passed = float(actual) > float(expected)
        except (TypeError, ValueError):
            passed = False

        return AssertionResult(
            assertion_id=assertion.assertion_id,
            assertion_type=_get_assertion_type_str(assertion.assertion_type),
            expression=assertion.expression,
            expected=expected,
            actual=actual,
            passed=passed,
            level=assertion.level,
        )

    def _execute_less_than(
        self,
        context: ExecutionContext,
        assertion: Assertion,
    ) -> AssertionResult:
        """Execute less_than assertion."""
        actual = context.get_value(assertion.expression)
        expected = assertion.expected

        try:
            passed = float(actual) < float(expected)
        except (TypeError, ValueError):
            passed = False

        return AssertionResult(
            assertion_id=assertion.assertion_id,
            assertion_type=_get_assertion_type_str(assertion.assertion_type),
            expression=assertion.expression,
            expected=expected,
            actual=actual,
            passed=passed,
            level=assertion.level,
        )

    def _execute_regex_match(
        self,
        context: ExecutionContext,
        assertion: Assertion,
    ) -> AssertionResult:
        """Execute regex_match assertion."""
        actual = context.get_value(assertion.expression)
        pattern = assertion.expected

        try:
            if isinstance(actual, str):
                match = re.search(pattern, actual)
                passed = match is not None
            else:
                passed = False
        except re.error:
            passed = False

        return AssertionResult(
            assertion_id=assertion.assertion_id,
            assertion_type=_get_assertion_type_str(assertion.assertion_type),
            expression=assertion.expression,
            expected=pattern,
            actual=actual,
            passed=passed,
            level=assertion.level,
        )

    def _execute_custom(
        self,
        context: ExecutionContext,
        assertion: Assertion,
    ) -> AssertionResult:
        """Execute custom assertion."""
        custom_name = assertion.expression.split(":")[0] if ":" in assertion.expression else assertion.expression

        executor = self._custom_executors.get(custom_name)
        if not executor:
            return AssertionResult(
                assertion_id=assertion.assertion_id,
                assertion_type=_get_assertion_type_str(assertion.assertion_type),
                expression=assertion.expression,
                expected=assertion.expected,
                actual=None,
                passed=False,
                level=assertion.level,
                error_message=f"Unknown custom assertion: {custom_name}",
            )

        return executor(context, assertion)


class DeterministicVerifier:
    """
    The core verification engine.

    Takes observations and assertions, produces verification reports.
    No LLM involved - purely deterministic.
    """

    def __init__(self):
        self._executor = AssertionExecutor()
        self._evidence_pipeline = get_evidence_pipeline()

    def verify(
        self,
        observation: ObservationPacket,
        assertions: List[Assertion],
        variables: Optional[Dict[str, Any]] = None,
    ) -> VerificationReport:
        """
        Verify observation against assertions.

        Args:
            observation: The world state observation
            assertions: List of assertions to verify
            variables: Optional variables for assertion expressions

        Returns:
            VerificationReport with all results
        """
        start_time = time.time()

        context = ExecutionContext(
            observation=observation,
            variables=variables or {},
            evidence_pipeline=self._evidence_pipeline,
        )

        # Execute all assertions
        results: List[AssertionResult] = []
        for assertion in assertions:
            result = self._executor.execute(assertion, context)
            results.append(result)
            logger.debug(
                f"Assertion {assertion.assertion_id}: "
                f"{'PASS' if result.passed else 'FAIL'}"
            )

        # Build evidence list
        evidence_list = self._collect_evidence(observation)

        # Analyze failures if any
        failure_analysis = None
        failed = [r for r in results if not r.passed]
        if failed:
            failure_analysis = self._analyze_failures(failed, observation)

        # Build report
        report = VerificationReport(
            verification_id=f"v-{observation.observation_id}",
            timestamp=datetime.utcnow().isoformat(),
            assertions=results,
            evidence=evidence_list,
            failure_analysis=failure_analysis,
            execution_time_ms=int((time.time() - start_time) * 1000),
            observation_id=observation.observation_id,
        )

        # passed and confidence are calculated in __post_init__
        logger.info(
            f"Verification {report.verification_id}: "
            f"{'PASSED' if report.passed else 'FAILED'} "
            f"(confidence: {report.confidence:.2f})"
        )

        return report

    def _collect_evidence(
        self,
        observation: ObservationPacket,
    ) -> List[Evidence]:
        """Collect evidence from observation."""
        evidence_list = []

        # Browser evidence
        if observation.browser:
            if observation.browser.screenshot_path:
                evidence_list.append(
                    Evidence(
                        evidence_id=f"e-screenshot-{observation.observation_id}",
                        evidence_type="screenshot",
                        timestamp=observation.timestamp,
                        data=observation.browser.screenshot_path,
                        hash=observation.browser.screenshot_hash,
                    )
                )

            if observation.browser.dom_snapshot:
                import hashlib
                import json

                dom_hash = hashlib.sha256(
                    json.dumps(observation.browser.dom_snapshot, sort_keys=True).encode()
                ).hexdigest()[:16]

                evidence_list.append(
                    Evidence(
                        evidence_id=f"e-dom-{observation.observation_id}",
                        evidence_type="dom_snapshot",
                        timestamp=observation.timestamp,
                        data=observation.browser.dom_snapshot,
                        hash=dom_hash,
                    )
                )

        # Database evidence
        if observation.database:
            for table_name, snapshot in observation.database.tables_snapshot.items():
                evidence_list.append(
                    Evidence(
                        evidence_id=f"e-db-{table_name}-{observation.observation_id}",
                        evidence_type="db_snapshot",
                        timestamp=observation.timestamp,
                        data={
                            "table": table_name,
                            "row_count": snapshot.row_count,
                            "sample_rows": snapshot.sample_rows,
                        },
                        hash=snapshot.checksum,
                    )
                )

        # Filesystem evidence
        if observation.filesystem:
            for f in observation.filesystem.files_created:
                evidence_list.append(
                    Evidence(
                        evidence_id=f"e-file-{f.path.replace('/', '_')}",
                        evidence_type="file_created",
                        timestamp=observation.timestamp,
                        data={"path": f.path, "size": f.size},
                        hash=f.hash,
                    )
                )

        # Runtime evidence
        if observation.runtime and observation.runtime.error_stacks:
            import hashlib

            error_hash = hashlib.sha256(
                "\n".join(observation.runtime.error_stacks).encode()
            ).hexdigest()[:16]

            evidence_list.append(
                Evidence(
                    evidence_id=f"e-errors-{observation.observation_id}",
                    evidence_type="error_stack",
                    timestamp=observation.timestamp,
                    data=observation.runtime.error_stacks,
                    hash=error_hash,
                )
            )

        return evidence_list

    def _analyze_failures(
        self,
        failed_results: List[AssertionResult],
        observation: ObservationPacket,
    ) -> FailureAnalysis:
        """
        Analyze failures deterministically.

        This is NOT LLM analysis - it's rule-based pattern matching.
        """
        affected_ids = [r.assertion_id for r in failed_results]

        # Determine failure type
        has_hard_failures = any(
            r.level == AssertionLevel.HARD for r in failed_results
        )
        has_errors = observation.has_errors()

        if has_errors and observation.runtime and observation.runtime.error_stacks:
            failure_type = "exception"
            root_cause = "Runtime exceptions detected"
        elif has_hard_failures:
            failure_type = "assertion_failed"
            root_cause = "Hard assertion(s) failed"
        else:
            failure_type = "soft_threshold"
            root_cause = "Soft assertion threshold not met"

        # Check for common patterns
        browser_failures = [
            r for r in failed_results if "browser" in r.expression
        ]
        db_failures = [r for r in failed_results if "database" in r.expression]
        file_failures = [r for r in failed_results if "filesystem" in r.expression]

        if browser_failures and observation.browser:
            if observation.browser.console_errors:
                root_cause = f"Browser errors: {observation.browser.console_errors[0]}"
            elif observation.browser.network_failed:
                root_cause = f"Network failures: {observation.browser.network_failed[0]}"

        if db_failures and observation.database:
            if observation.database.connection_status != "connected":
                root_cause = f"Database connection: {observation.database.connection_status}"

        return FailureAnalysis(
            failure_type=failure_type,
            root_cause=root_cause,
            affected_assertions=affected_ids,
        )

    def register_custom_assertion(
        self,
        name: str,
        executor: Callable[[ExecutionContext, Assertion], AssertionResult],
    ) -> None:
        """Register a custom assertion type."""
        self._executor.register_custom(name, executor)


# Singleton instance
_verifier_instance: Optional[DeterministicVerifier] = None


def get_deterministic_verifier() -> DeterministicVerifier:
    """Get the singleton deterministic verifier."""
    global _verifier_instance
    if _verifier_instance is None:
        _verifier_instance = DeterministicVerifier()
    return _verifier_instance
