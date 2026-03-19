"""
Quality Service Interfaces

Abstract interfaces for code quality checking and analysis.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class QualityIssue:
    """A single quality issue found during analysis."""

    severity: str  # "error", "warning", "info", "hint"
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    rule: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityReport:
    """Result of a quality check."""

    score: float
    max_score: float = 10.0
    passed: bool = True
    summary: str = ""
    issues: List[QualityIssue] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class IQualityChecker(ABC):
    """
    Abstract interface for quality checking services.

    Implementations validate code against quality standards.
    """

    @abstractmethod
    async def check(
        self,
        content: str,
        file_path: Optional[str] = None,
        **kwargs: Any,
    ) -> QualityReport:
        """
        Run quality checks on content.

        Args:
            content: Code or text to check
            file_path: Optional file path for context
            **kwargs: Checker-specific options

        Returns:
            QualityReport with score and issues
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the checker is available."""
        pass


class ICodeAnalyzer(ABC):
    """
    Abstract interface for code analysis services.

    Implementations provide deeper structural analysis beyond linting.
    """

    @abstractmethod
    async def analyze(
        self,
        content: str,
        language: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Analyze code structure and quality.

        Args:
            content: Source code to analyze
            language: Programming language
            **kwargs: Analyzer-specific options

        Returns:
            Analysis results dict
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the analyzer is available."""
        pass
