"""
Core Interfaces for Dependency Injection

This module defines abstract interfaces for all major services.
Use these interfaces for dependency injection to achieve:
- Zero coupling between modules
- Easy testing with mock implementations
- Swappable implementations
"""

from .llm import ILLMService, IEmbeddingService
from .storage import IFileRepository, IVectorStoreRepository
from .quality import IQualityChecker, ICodeAnalyzer

__all__ = [
    "ILLMService",
    "IEmbeddingService",
    "IFileRepository",
    "IVectorStoreRepository",
    "IQualityChecker",
    "ICodeAnalyzer",
]
