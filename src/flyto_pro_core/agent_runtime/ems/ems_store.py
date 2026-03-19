"""
EMS Store - Storage and matching for fix patterns.

Provides:
- Pattern storage with scope filtering
- Efficient matching algorithm
- Lifecycle management
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .error_signature import ErrorSignature, compute_error_signature
from .fix_pattern import (
    FixPattern,
    FixPatternScope,
    FixPatternStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Result of matching an error against patterns."""

    found: bool = False
    pattern: Optional[FixPattern] = None
    similarity_score: float = 0.0
    match_reason: str = ""
    alternatives: List[FixPattern] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "found": self.found,
            "pattern_id": self.pattern.pattern_id if self.pattern else None,
            "pattern_name": self.pattern.name if self.pattern else None,
            "similarity_score": self.similarity_score,
            "match_reason": self.match_reason,
            "alternative_count": len(self.alternatives),
        }


class EMSMatcher:
    """
    Matches errors against fix patterns.

    Uses a multi-level matching strategy:
    1. Exact signature match
    2. Component-based similarity
    3. Context-aware ranking
    """

    def __init__(
        self,
        similarity_threshold: float = 0.8,
        max_alternatives: int = 3,
    ):
        self.similarity_threshold = similarity_threshold
        self.max_alternatives = max_alternatives

    def find_match(
        self,
        signature: ErrorSignature,
        patterns: List[FixPattern],
        context: Optional[Dict[str, Any]] = None,
    ) -> MatchResult:
        """
        Find the best matching pattern for an error.

        Args:
            signature: Error signature to match
            patterns: Available patterns to search
            context: Additional context for ranking

        Returns:
            MatchResult with best match and alternatives
        """
        if not patterns:
            return MatchResult(
                found=False,
                match_reason="no_patterns_available",
            )

        # Filter to active/testing patterns only
        active_patterns = [
            p for p in patterns
            if p.status in (FixPatternStatus.ACTIVE, FixPatternStatus.TESTING)
        ]

        if not active_patterns:
            return MatchResult(
                found=False,
                match_reason="no_active_patterns",
            )

        # Calculate similarity for each pattern
        scored: List[Tuple[FixPattern, float, str]] = []

        for pattern in active_patterns:
            score, reason = self._calculate_similarity(
                signature, pattern, context
            )
            if score >= self.similarity_threshold:
                scored.append((pattern, score, reason))

        if not scored:
            return MatchResult(
                found=False,
                match_reason="no_patterns_above_threshold",
            )

        # Sort by score (descending), then by success rate
        scored.sort(
            key=lambda x: (x[1], x[0].success_rate),
            reverse=True,
        )

        best = scored[0]
        alternatives = [p for p, _, _ in scored[1:self.max_alternatives + 1]]

        return MatchResult(
            found=True,
            pattern=best[0],
            similarity_score=best[1],
            match_reason=best[2],
            alternatives=alternatives,
        )

    def _calculate_similarity(
        self,
        signature: ErrorSignature,
        pattern: FixPattern,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[float, str]:
        """Calculate similarity between signature and pattern."""
        pattern_sig = pattern.error_signature

        # Exact match
        if signature.signature_hash == pattern_sig.signature_hash:
            return 1.0, "exact_match"

        # Component-based matching
        common_keys = set(signature.components.keys()) & set(
            pattern_sig.components.keys()
        )
        if not common_keys:
            return 0.0, "no_common_components"

        # Calculate base score
        matches = 0
        weights = {
            "error_type": 2.0,
            "error_message": 1.0,
            "stack_frame": 1.0,
            "module_id": 2.0,
            "assertion_type": 1.5,
            "context_key": 0.5,
        }

        total_weight = 0
        weighted_matches = 0

        for key in common_keys:
            weight = weights.get(key, 1.0)
            total_weight += weight
            if signature.components[key] == pattern_sig.components[key]:
                weighted_matches += weight
                matches += 1

        if total_weight == 0:
            return 0.0, "no_weighted_components"

        base_score = weighted_matches / total_weight

        # Boost score based on pattern success rate
        if pattern.times_applied > 5:
            success_boost = pattern.success_rate * 0.1
            base_score = min(1.0, base_score + success_boost)

        # Context matching (if available)
        if context and pattern.additional_conditions:
            condition_matches = sum(
                1 for c in pattern.additional_conditions
                if self._evaluate_condition(c, context)
            )
            if condition_matches > 0:
                context_boost = 0.05 * condition_matches
                base_score = min(1.0, base_score + context_boost)

        reason = f"component_match_{matches}/{len(common_keys)}"
        return base_score, reason

    def _evaluate_condition(
        self,
        condition: str,
        context: Dict[str, Any],
    ) -> bool:
        """Evaluate an additional condition against context."""
        # Simple key=value matching for now
        if "=" in condition:
            key, value = condition.split("=", 1)
            return str(context.get(key.strip())) == value.strip()
        return False


class EMSStore:
    """
    Storage for EMS patterns.

    Supports:
    - File-based persistence
    - Scope-based filtering
    - Lifecycle management
    """

    def __init__(
        self,
        storage_path: str = "",
        project_id: Optional[str] = None,
        environment: Optional[str] = None,
    ):
        self.storage_path = storage_path
        self.project_id = project_id
        self.environment = environment
        self._patterns: Dict[str, FixPattern] = {}
        self._matcher = EMSMatcher()
        self._loaded = False

    def load(self) -> int:
        """Load patterns from storage."""
        if not self.storage_path or not os.path.exists(self.storage_path):
            return 0

        patterns_file = os.path.join(self.storage_path, "patterns.json")
        if not os.path.exists(patterns_file):
            return 0

        try:
            with open(patterns_file, "r") as f:
                data = json.load(f)

            for p_data in data.get("patterns", []):
                pattern = FixPattern.from_dict(p_data)
                self._patterns[pattern.pattern_id] = pattern

            self._loaded = True
            logger.info(f"Loaded {len(self._patterns)} EMS patterns")
            return len(self._patterns)

        except Exception as e:
            logger.error(f"Failed to load EMS patterns: {e}")
            return 0

    def save(self) -> bool:
        """Save patterns to storage."""
        if not self.storage_path:
            return False

        os.makedirs(self.storage_path, exist_ok=True)
        patterns_file = os.path.join(self.storage_path, "patterns.json")

        try:
            data = {
                "version": "1.0",
                "updated_at": datetime.utcnow().isoformat(),
                "patterns": [p.to_dict() for p in self._patterns.values()],
            }

            with open(patterns_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(self._patterns)} EMS patterns")
            return True

        except Exception as e:
            logger.error(f"Failed to save EMS patterns: {e}")
            return False

    def add_pattern(self, pattern: FixPattern) -> str:
        """Add a new pattern."""
        # Set scope context if not set
        if pattern.scope == FixPatternScope.PROJECT and not pattern.project_id:
            pattern.project_id = self.project_id
        if pattern.scope == FixPatternScope.ENVIRONMENT and not pattern.environment:
            pattern.environment = self.environment

        self._patterns[pattern.pattern_id] = pattern
        self.save()
        logger.info(f"Added EMS pattern: {pattern.pattern_id} ({pattern.name})")
        return pattern.pattern_id

    def get_pattern(self, pattern_id: str) -> Optional[FixPattern]:
        """Get pattern by ID."""
        return self._patterns.get(pattern_id)

    def find_pattern(
        self,
        signature: ErrorSignature,
        context: Optional[Dict[str, Any]] = None,
    ) -> MatchResult:
        """Find matching pattern for error."""
        applicable = self._get_applicable_patterns()
        return self._matcher.find_match(signature, applicable, context)

    def find_pattern_for_error(
        self,
        error: Optional[Exception] = None,
        error_type: str = "",
        error_message: str = "",
        stack_trace: str = "",
        module_id: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> MatchResult:
        """Convenience method to find pattern for an error."""
        signature = compute_error_signature(
            error=error,
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            module_id=module_id,
            context=context,
        )
        return self.find_pattern(signature, context)

    def _get_applicable_patterns(self) -> List[FixPattern]:
        """Get patterns applicable to current scope."""
        patterns = []

        for pattern in self._patterns.values():
            if self._is_applicable(pattern):
                patterns.append(pattern)

        return patterns

    def _is_applicable(self, pattern: FixPattern) -> bool:
        """Check if pattern is applicable to current scope."""
        if pattern.scope == FixPatternScope.GLOBAL:
            return True

        if pattern.scope == FixPatternScope.PROJECT:
            return pattern.project_id == self.project_id or pattern.project_id is None

        if pattern.scope == FixPatternScope.ENVIRONMENT:
            return (
                pattern.environment == self.environment
                or pattern.environment is None
            )

        if pattern.scope == FixPatternScope.MODULE:
            # Module scope always applicable (checked during matching)
            return True

        return True

    def promote_pattern(self, pattern_id: str) -> bool:
        """Promote pattern from pending/testing to active."""
        pattern = self._patterns.get(pattern_id)
        if not pattern:
            return False

        pattern.promote_to_active()
        self.save()
        logger.info(f"Promoted pattern to active: {pattern_id}")
        return True

    def deprecate_pattern(
        self,
        pattern_id: str,
        superseded_by: Optional[str] = None,
    ) -> bool:
        """Deprecate a pattern."""
        pattern = self._patterns.get(pattern_id)
        if not pattern:
            return False

        pattern.deprecate(superseded_by)
        self.save()
        logger.info(f"Deprecated pattern: {pattern_id}")
        return True

    def reject_pattern(
        self,
        pattern_id: str,
        reason: str = "",
    ) -> bool:
        """Reject a pattern."""
        pattern = self._patterns.get(pattern_id)
        if not pattern:
            return False

        pattern.reject(reason)
        self.save()
        logger.info(f"Rejected pattern: {pattern_id}")
        return True

    def record_application(
        self,
        pattern_id: str,
        succeeded: bool,
    ) -> bool:
        """Record that a pattern was applied."""
        pattern = self._patterns.get(pattern_id)
        if not pattern:
            return False

        pattern.record_application(succeeded)

        # Auto-promote if success rate is good after enough applications
        if (
            pattern.status == FixPatternStatus.TESTING
            and pattern.times_applied >= 3
            and pattern.success_rate >= 0.8
        ):
            pattern.promote_to_active()

        # Auto-deprecate if success rate drops
        if (
            pattern.status == FixPatternStatus.ACTIVE
            and pattern.times_applied >= 5
            and pattern.success_rate < 0.5
        ):
            pattern.deprecate()
            logger.warning(
                f"Auto-deprecated pattern due to low success rate: {pattern_id}"
            )

        self.save()
        return True

    def get_statistics(self) -> Dict[str, Any]:
        """Get EMS statistics."""
        by_status = {}
        by_scope = {}
        total_applications = 0
        total_successes = 0

        for pattern in self._patterns.values():
            # Count by status
            status = pattern.status.value
            by_status[status] = by_status.get(status, 0) + 1

            # Count by scope
            scope = pattern.scope.value
            by_scope[scope] = by_scope.get(scope, 0) + 1

            # Count applications
            total_applications += pattern.times_applied
            total_successes += pattern.times_succeeded

        return {
            "total_patterns": len(self._patterns),
            "by_status": by_status,
            "by_scope": by_scope,
            "total_applications": total_applications,
            "total_successes": total_successes,
            "overall_success_rate": (
                total_successes / total_applications
                if total_applications > 0
                else 0
            ),
        }

    def list_patterns(
        self,
        status: Optional[FixPatternStatus] = None,
        scope: Optional[FixPatternScope] = None,
        tag: Optional[str] = None,
    ) -> List[FixPattern]:
        """List patterns with optional filters."""
        result = []

        for pattern in self._patterns.values():
            if status and pattern.status != status:
                continue
            if scope and pattern.scope != scope:
                continue
            if tag and tag not in pattern.tags:
                continue
            result.append(pattern)

        return result

    def get_pending_patterns(self) -> List[FixPattern]:
        """Get patterns waiting for verification."""
        return self.list_patterns(status=FixPatternStatus.PENDING)


# Global store instances per project
_stores: Dict[str, EMSStore] = {}


def get_ems_store(
    storage_path: str = "",
    project_id: Optional[str] = None,
) -> EMSStore:
    """Get or create EMS store for project."""
    key = storage_path or "default"

    if key not in _stores:
        _stores[key] = EMSStore(
            storage_path=storage_path,
            project_id=project_id,
        )
        _stores[key].load()

    return _stores[key]
