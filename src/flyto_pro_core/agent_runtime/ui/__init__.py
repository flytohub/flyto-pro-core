"""
UI Module - Communication layer for frontend.

Provides:
- Progress visualization data
- Task management API
- Risk confirmation cards
- Tech-to-user translation
"""

from .progress_tracker import (
    ProgressTracker,
    ProgressUpdate,
    ProgressLevel,
)
from .tech_translator import (
    TechDecisionTranslator,
    TranslationContext,
)
from .risk_card import (
    RiskCard,
    RiskLevel,
    RiskCardBuilder,
)
from .task_api import (
    TaskAPI,
    TaskReorderRequest,
    TaskUpdateRequest,
)

__all__ = [
    # Progress
    "ProgressTracker",
    "ProgressUpdate",
    "ProgressLevel",
    # Translation
    "TechDecisionTranslator",
    "TranslationContext",
    # Risk
    "RiskCard",
    "RiskLevel",
    "RiskCardBuilder",
    # Task API
    "TaskAPI",
    "TaskReorderRequest",
    "TaskUpdateRequest",
]
