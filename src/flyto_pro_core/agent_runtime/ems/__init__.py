"""
EMS (Error Memory System) - Verified behavior corrections.

EMS stores patterns that have been VERIFIED to work.
Not LLM guesses - proven fixes with side effect tracking.
"""

from .error_signature import (
    ErrorSignature,
    SignatureComponent,
    compute_error_signature,
)
from .fix_pattern import (
    FixPattern,
    FixPatternStatus,
    FixPatternScope,
    SideEffect,
    SideEffectType,
)
from .ems_store import (
    EMSStore,
    EMSMatcher,
    MatchResult,
)

__all__ = [
    # Signature
    "ErrorSignature",
    "SignatureComponent",
    "compute_error_signature",
    # Pattern
    "FixPattern",
    "FixPatternStatus",
    "FixPatternScope",
    "SideEffect",
    "SideEffectType",
    # Store
    "EMSStore",
    "EMSMatcher",
    "MatchResult",
]
