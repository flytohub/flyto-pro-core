"""
Verification Module - Deterministic verification.

The core of "trust but verify" - verification must be deterministic,
not LLM judgment.
"""

from .verification_report import (
    VerificationReport,
    AssertionResult,
    Evidence,
    FailureAnalysis,
    VerificationRules,
)
from .evidence_pipeline import (
    EvidenceType,
    RawEvidence,
    DerivedEvidence,
    EvidencePipeline,
    get_evidence_pipeline,
)
from .deterministic_verifier import (
    DeterministicVerifier,
    AssertionExecutor,
)

__all__ = [
    # Report
    "VerificationReport",
    "AssertionResult",
    "Evidence",
    "FailureAnalysis",
    "VerificationRules",
    # Evidence
    "EvidenceType",
    "RawEvidence",
    "DerivedEvidence",
    "EvidencePipeline",
    "get_evidence_pipeline",
    # Verifier
    "DeterministicVerifier",
    "AssertionExecutor",
]
