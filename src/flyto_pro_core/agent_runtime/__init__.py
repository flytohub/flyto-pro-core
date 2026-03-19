"""
Flyto Agent Runtime

AI Kernel for deterministic execution and verification.
LLM is User space, Runtime is Kernel space.

Architecture:
- contracts/: Core data contracts (PlanContract, ExecutionBundle, etc.)
- observation/: World state observation (ObservationPacket, Collector)
- verification/: Deterministic verification (Verifier, Evidence Pipeline)
- project/: Project state management (Goal/Task/Step, .flyto/)
- intervention/: User intervention handling (DecisionCard, Handler)
- ems/: Error Memory System (Signatures, FixPatterns)
- ui/: Frontend communication (Progress, Risk Cards, Task API)
"""

__version__ = "0.1.0"

# Contracts
from .contracts import (
    ContractMeta,
    PlanContract,
    Assertion,
    AssertionType,
    AssertionLevel,
    StopPolicy,
    StopCondition,
    StopPolicyChecker,
    ExecutionBundle,
    DecisionCard,
    DecisionOption,
    CapabilityToken,
    CapabilityScope,
    CapabilityGuard,
)

# Observation
from .observation import (
    ObservationPacket,
    BrowserObservation,
    DatabaseObservation,
    FileSystemObservation,
    NetworkObservation,
    RuntimeObservation,
    ObservationCollector,
    get_observation_collector,
)

# Verification
from .verification import (
    VerificationReport,
    AssertionResult,
    Evidence,
    FailureAnalysis,
    VerificationRules,
    RawEvidence,
    DerivedEvidence,
    EvidencePipeline,
    DeterministicVerifier,
    AssertionExecutor,
)

# Project
from .project import (
    Goal,
    Task,
    Step,
    StepStatus,
    TaskStatus,
    GoalStatus,
    StepArtifact,
    TaskChecklist,
    ProjectState,
    ProjectConfig,
    ProjectStateManager,
    FlytoDirectory,
)

# Intervention
from .intervention import (
    InterventionType,
    InterventionPriority,
    InterventionPoint,
    InterventionRequest,
    InterventionResponse,
    DecisionCardBuilder,
    InterventionHandler,
)

# EMS
from .ems import (
    ErrorSignature,
    compute_error_signature,
    FixPattern,
    FixPatternStatus,
    FixPatternScope,
    SideEffect,
    SideEffectType,
    EMSStore,
    EMSMatcher,
    MatchResult,
)

# UI
from .ui import (
    ProgressTracker,
    ProgressUpdate,
    ProgressLevel,
    TechDecisionTranslator,
    RiskCard,
    RiskLevel,
    RiskCardBuilder,
    TaskAPI,
)

__all__ = [
    # Version
    "__version__",
    # Contracts
    "ContractMeta",
    "PlanContract",
    "Assertion",
    "AssertionType",
    "AssertionLevel",
    "StopPolicy",
    "StopCondition",
    "StopPolicyChecker",
    "ExecutionBundle",
    "DecisionCard",
    "DecisionOption",
    "CapabilityToken",
    "CapabilityScope",
    "CapabilityGuard",
    # Observation
    "ObservationPacket",
    "BrowserObservation",
    "DatabaseObservation",
    "FileSystemObservation",
    "NetworkObservation",
    "RuntimeObservation",
    "ObservationCollector",
    "get_observation_collector",
    # Verification
    "VerificationReport",
    "AssertionResult",
    "Evidence",
    "FailureAnalysis",
    "VerificationRules",
    "RawEvidence",
    "DerivedEvidence",
    "EvidencePipeline",
    "DeterministicVerifier",
    "AssertionExecutor",
    # Project
    "Goal",
    "Task",
    "Step",
    "StepStatus",
    "TaskStatus",
    "GoalStatus",
    "StepArtifact",
    "TaskChecklist",
    "ProjectState",
    "ProjectConfig",
    "ProjectStateManager",
    "FlytoDirectory",
    # Intervention
    "InterventionType",
    "InterventionPriority",
    "InterventionPoint",
    "InterventionRequest",
    "InterventionResponse",
    "DecisionCardBuilder",
    "InterventionHandler",
    # EMS
    "ErrorSignature",
    "compute_error_signature",
    "FixPattern",
    "FixPatternStatus",
    "FixPatternScope",
    "SideEffect",
    "SideEffectType",
    "EMSStore",
    "EMSMatcher",
    "MatchResult",
    # UI
    "ProgressTracker",
    "ProgressUpdate",
    "ProgressLevel",
    "TechDecisionTranslator",
    "RiskCard",
    "RiskLevel",
    "RiskCardBuilder",
    "TaskAPI",
]
