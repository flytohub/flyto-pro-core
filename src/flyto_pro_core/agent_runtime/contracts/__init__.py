"""
Agent Runtime Contracts

Core contracts for flyto-pro and flyto-cloud communication.
All contracts are versioned and validated.
"""

from .contract_meta import ContractMeta, validate_contract_version
from .plan_contract import (
    PlanContract,
    Assertion,
    AssertionType,
    AssertionLevel,
    ObservationSpec,
    StopCondition,
)
from .execution_bundle import ExecutionBundle, EnvironmentFingerprint
from .decision_card import DecisionCard, DecisionOption, DecisionContext
from .stop_policy import StopPolicy, FallbackPolicy, StopPolicyChecker
from .capability_token import (
    CapabilityToken,
    CapabilityScope,
    CapabilityGuard,
    CapabilityTokenBuilder,
)
from .plan_proposal import (
    PlanProposal,
    ProposalStatus,
    ProposalPriority,
    ProposalMetadata,
    PlanProposalBuilder,
)

__all__ = [
    # Meta
    "ContractMeta",
    "validate_contract_version",
    # Plan
    "PlanContract",
    "Assertion",
    "AssertionType",
    "AssertionLevel",
    "ObservationSpec",
    "StopCondition",
    # Execution
    "ExecutionBundle",
    "EnvironmentFingerprint",
    # Decision
    "DecisionCard",
    "DecisionOption",
    "DecisionContext",
    # Stop
    "StopPolicy",
    "FallbackPolicy",
    "StopPolicyChecker",
    # Capability
    "CapabilityToken",
    "CapabilityScope",
    "CapabilityGuard",
    "CapabilityTokenBuilder",
    # Proposal
    "PlanProposal",
    "ProposalStatus",
    "ProposalPriority",
    "ProposalMetadata",
    "PlanProposalBuilder",
]
