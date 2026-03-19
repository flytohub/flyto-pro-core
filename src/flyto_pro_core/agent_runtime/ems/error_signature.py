"""
Error Signature - Fingerprinting for errors.

Creates unique signatures for errors that can be matched later.
The signature must be stable across runs but flexible enough
to match similar errors.
"""

import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class SignatureComponent(Enum):
    """Components used in signature computation."""

    ERROR_TYPE = "error_type"  # Exception class name
    ERROR_MESSAGE = "error_message"  # Normalized message
    STACK_FRAME = "stack_frame"  # Key stack frames
    MODULE_ID = "module_id"  # Module that failed
    CONTEXT_KEY = "context_key"  # Relevant context keys
    ASSERTION_TYPE = "assertion_type"  # Assertion that failed


@dataclass
class ErrorSignature:
    """
    Unique fingerprint for an error.

    The signature is designed to:
    1. Match the same error across runs
    2. Ignore transient details (line numbers, timestamps)
    3. Include enough context to avoid false matches
    """

    # Primary signature (hash)
    signature_hash: str = ""

    # Components used
    components: Dict[str, str] = field(default_factory=dict)

    # Original error info
    error_type: str = ""
    error_message: str = ""
    normalized_message: str = ""

    # Stack info
    key_frames: List[str] = field(default_factory=list)
    entry_point: str = ""

    # Context
    module_id: str = ""
    step_id: str = ""
    assertion_id: str = ""

    # Matching
    similarity_threshold: float = 0.8

    def __post_init__(self):
        if not self.signature_hash and self.components:
            self.signature_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute signature hash from components."""
        # Sort components for consistency
        sorted_items = sorted(self.components.items())
        content = "|".join(f"{k}:{v}" for k, v in sorted_items)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def matches(self, other: "ErrorSignature") -> Tuple[bool, float]:
        """
        Check if this signature matches another.

        Returns:
            Tuple of (matches, similarity_score)
        """
        if self.signature_hash == other.signature_hash:
            return True, 1.0

        # Compare components with weights
        common_keys = set(self.components.keys()) & set(other.components.keys())
        if not common_keys:
            return False, 0.0

        weights = {
            "error_type": 2.0,
            "error_message": 1.0,
            "stack_frame": 1.0,
            "module_id": 2.0,
            "assertion_type": 1.5,
            "context_key": 0.5,
        }

        total_weight = 0.0
        weighted_matches = 0.0
        for k in common_keys:
            w = weights.get(k, 1.0)
            total_weight += w
            if self.components[k] == other.components[k]:
                weighted_matches += w

        if total_weight == 0:
            return False, 0.0

        score = weighted_matches / total_weight

        return score >= self.similarity_threshold, score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signature_hash": self.signature_hash,
            "components": self.components,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "normalized_message": self.normalized_message,
            "key_frames": self.key_frames,
            "entry_point": self.entry_point,
            "module_id": self.module_id,
            "step_id": self.step_id,
            "assertion_id": self.assertion_id,
            "similarity_threshold": self.similarity_threshold,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ErrorSignature":
        return cls(
            signature_hash=data.get("signature_hash", ""),
            components=data.get("components", {}),
            error_type=data.get("error_type", ""),
            error_message=data.get("error_message", ""),
            normalized_message=data.get("normalized_message", ""),
            key_frames=data.get("key_frames", []),
            entry_point=data.get("entry_point", ""),
            module_id=data.get("module_id", ""),
            step_id=data.get("step_id", ""),
            assertion_id=data.get("assertion_id", ""),
            similarity_threshold=data.get("similarity_threshold", 0.8),
        )


class ErrorNormalizer:
    """Normalizes error messages for consistent matching."""

    # Patterns to remove (transient data)
    REMOVE_PATTERNS = [
        r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[.\d]*Z?\b",  # Timestamps
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",  # UUIDs
        r"\b0x[0-9a-fA-F]+\b",  # Memory addresses
        r"\bline \d+\b",  # Line numbers
        r"\bat \d+:\d+\b",  # Position markers
        r"\b\d+\.\d+\.\d+\.\d+\b",  # IP addresses
        r"\bport \d+\b",  # Port numbers
        r'["\']?/[^"\'\s]+["\']?',  # File paths
        r"\b\d+ms\b",  # Timing
    ]

    # Patterns to normalize
    NORMALIZE_PATTERNS = [
        (r"\s+", " "),  # Multiple spaces to single
        (r"^\s+|\s+$", ""),  # Trim
    ]

    @classmethod
    def normalize(cls, message: str) -> str:
        """Normalize an error message."""
        result = message

        # Remove transient patterns
        for pattern in cls.REMOVE_PATTERNS:
            result = re.sub(pattern, "<REMOVED>", result)

        # Apply normalizations
        for pattern, replacement in cls.NORMALIZE_PATTERNS:
            result = re.sub(pattern, replacement, result)

        return result.lower()


class StackNormalizer:
    """Normalizes stack traces for consistent matching."""

    # Frames to skip (framework internals)
    SKIP_PATTERNS = [
        r"node_modules/",
        r"site-packages/",
        r"<frozen ",
        r"asyncio/",
        r"concurrent/",
        r"threading\.py",
    ]

    @classmethod
    def extract_key_frames(
        cls,
        stack_trace: str,
        max_frames: int = 5,
    ) -> List[str]:
        """Extract key frames from stack trace."""
        lines = stack_trace.split("\n")
        frames = []

        for line in lines:
            # Skip non-frame lines
            if not line.strip().startswith(("File", "at ")):
                continue

            # Skip framework internals
            if any(re.search(p, line) for p in cls.SKIP_PATTERNS):
                continue

            # Normalize frame
            frame = cls._normalize_frame(line)
            if frame and frame not in frames:
                frames.append(frame)

            if len(frames) >= max_frames:
                break

        return frames

    @classmethod
    def _normalize_frame(cls, frame: str) -> str:
        """Normalize a single stack frame."""
        # Remove line numbers
        frame = re.sub(r":\d+", "", frame)
        # Remove memory addresses
        frame = re.sub(r"0x[0-9a-fA-F]+", "", frame)
        # Extract function name
        match = re.search(r"in (\w+)", frame)
        if match:
            return match.group(1)
        return frame.strip()


def compute_error_signature(
    error: Optional[Exception] = None,
    error_type: str = "",
    error_message: str = "",
    stack_trace: str = "",
    module_id: str = "",
    step_id: str = "",
    assertion_id: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> ErrorSignature:
    """
    Compute an error signature.

    Args:
        error: Exception object (if available)
        error_type: Error type name (if no exception)
        error_message: Error message
        stack_trace: Stack trace string
        module_id: Module that raised the error
        step_id: Step that raised the error
        assertion_id: Assertion that failed (if applicable)
        context: Additional context

    Returns:
        ErrorSignature for matching
    """
    components = {}

    # Get error type
    if error:
        etype = type(error).__name__
        emsg = str(error)
    else:
        etype = error_type
        emsg = error_message

    # Normalize message
    normalized = ErrorNormalizer.normalize(emsg)

    # Add components
    components[SignatureComponent.ERROR_TYPE.value] = etype
    components[SignatureComponent.ERROR_MESSAGE.value] = normalized[:100]

    # Extract key frames
    key_frames = []
    entry_point = ""
    if stack_trace:
        key_frames = StackNormalizer.extract_key_frames(stack_trace)
        if key_frames:
            entry_point = key_frames[0]
            components[SignatureComponent.STACK_FRAME.value] = "|".join(
                key_frames[:3]
            )

    # Add module/step info
    if module_id:
        components[SignatureComponent.MODULE_ID.value] = module_id

    if assertion_id:
        components[SignatureComponent.ASSERTION_TYPE.value] = assertion_id

    # Add context keys
    if context:
        context_keys = sorted(context.keys())[:5]
        if context_keys:
            components[SignatureComponent.CONTEXT_KEY.value] = "|".join(context_keys)

    return ErrorSignature(
        components=components,
        error_type=etype,
        error_message=emsg,
        normalized_message=normalized,
        key_frames=key_frames,
        entry_point=entry_point,
        module_id=module_id,
        step_id=step_id,
        assertion_id=assertion_id,
    )


def compute_assertion_signature(
    assertion_id: str,
    assertion_type: str,
    expression: str,
    expected: Any,
    actual: Any,
    module_id: str = "",
) -> ErrorSignature:
    """
    Compute signature for a failed assertion.

    Similar to error signature but specific to assertions.
    """
    components = {
        SignatureComponent.ASSERTION_TYPE.value: assertion_type,
        SignatureComponent.ERROR_MESSAGE.value: f"{expression}|{type(expected).__name__}|{type(actual).__name__}",
    }

    if module_id:
        components[SignatureComponent.MODULE_ID.value] = module_id

    return ErrorSignature(
        components=components,
        error_type="AssertionFailed",
        error_message=f"{assertion_type}: {expression}",
        normalized_message=f"assertion_{assertion_type}_{expression}",
        assertion_id=assertion_id,
        module_id=module_id,
    )
