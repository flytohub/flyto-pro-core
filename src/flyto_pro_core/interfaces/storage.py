"""
Storage Service Interfaces

Abstract interfaces for file and vector storage services.

Note: This module defines abstract interfaces (Protocols).
No atomization needed - interfaces are already atomic by design.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


@dataclass
class FileContent:
    """File content with metadata."""

    content: str
    path: str
    encoding: str = "utf-8"
    size: int = 0
    exists: bool = True


@dataclass
class VectorSearchResult:
    """Vector search result with score and payload."""

    id: str
    score: float
    payload: Dict[str, Any] = field(default_factory=dict)
    vector: Optional[List[float]] = None


class IFileRepository(ABC):
    """
    Abstract interface for file operations.

    Provides a clean abstraction for file I/O operations.
    Implementations can target local filesystem, cloud storage, etc.
    """

    @abstractmethod
    def read(self, path: Union[str, Path]) -> FileContent:
        """
        Read file content.

        Args:
            path: File path to read

        Returns:
            FileContent with content and metadata

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: On read error
        """
        pass

    @abstractmethod
    def write(
        self,
        path: Union[str, Path],
        content: str,
        encoding: str = "utf-8",
    ) -> bool:
        """
        Write content to file.

        Args:
            path: File path to write
            content: Content to write
            encoding: Text encoding

        Returns:
            True if successful

        Raises:
            IOError: On write error
        """
        pass

    @abstractmethod
    def exists(self, path: Union[str, Path]) -> bool:
        """
        Check if file exists.

        Args:
            path: File path to check

        Returns:
            True if file exists
        """
        pass

    @abstractmethod
    def delete(self, path: Union[str, Path]) -> bool:
        """
        Delete file.

        Args:
            path: File path to delete

        Returns:
            True if deleted (or didn't exist)
        """
        pass

    @abstractmethod
    def list_files(
        self,
        directory: Union[str, Path],
        pattern: str = "*",
        recursive: bool = False,
    ) -> List[str]:
        """
        List files in directory.

        Args:
            directory: Directory to list
            pattern: Glob pattern for filtering
            recursive: Include subdirectories

        Returns:
            List of file paths
        """
        pass


class IVectorStoreRepository(ABC):
    """
    Abstract interface for vector database operations.

    Provides abstraction for vector storage and retrieval.
    Implementations can target Qdrant, Pinecone, Milvus, etc.
    """

    @abstractmethod
    async def upsert(
        self,
        collection: str,
        id: str,
        vector: List[float],
        payload: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Insert or update a vector.

        Args:
            collection: Collection name
            id: Vector ID
            vector: Vector data
            payload: Optional metadata

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def upsert_batch(
        self,
        collection: str,
        points: List[Dict[str, Any]],
    ) -> int:
        """
        Batch insert/update vectors.

        Args:
            collection: Collection name
            points: List of dicts with 'id', 'vector', 'payload'

        Returns:
            Number of points upserted
        """
        pass

    @abstractmethod
    async def search(
        self,
        collection: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[VectorSearchResult]:
        """
        Search for similar vectors.

        Args:
            collection: Collection name
            query_vector: Query vector
            limit: Maximum results
            score_threshold: Minimum similarity score
            filter_conditions: Metadata filters

        Returns:
            List of search results
        """
        pass

    @abstractmethod
    async def delete(
        self,
        collection: str,
        ids: List[str],
    ) -> int:
        """
        Delete vectors by ID.

        Args:
            collection: Collection name
            ids: Vector IDs to delete

        Returns:
            Number of vectors deleted
        """
        pass

    @abstractmethod
    async def get(
        self,
        collection: str,
        id: str,
    ) -> Optional[VectorSearchResult]:
        """
        Get vector by ID.

        Args:
            collection: Collection name
            id: Vector ID

        Returns:
            Vector data or None if not found
        """
        pass

    @abstractmethod
    async def create_collection(
        self,
        name: str,
        dimension: int,
        distance_metric: str = "cosine",
    ) -> bool:
        """
        Create a new collection.

        Args:
            name: Collection name
            dimension: Vector dimension
            distance_metric: Distance metric (cosine, euclidean, dot)

        Returns:
            True if created or already exists
        """
        pass

    @abstractmethod
    async def delete_collection(self, name: str) -> bool:
        """
        Delete a collection.

        Args:
            name: Collection name

        Returns:
            True if deleted
        """
        pass

    @abstractmethod
    async def collection_exists(self, name: str) -> bool:
        """
        Check if collection exists.

        Args:
            name: Collection name

        Returns:
            True if exists
        """
        pass


class LocalFileRepository(IFileRepository):
    """Local filesystem implementation of IFileRepository."""

    def __init__(self, base_path: Optional[Union[str, Path]] = None):
        self.base_path = Path(base_path) if base_path else None

    def _resolve_path(self, path: Union[str, Path]) -> Path:
        """Resolve path relative to base path if set."""
        p = Path(path)
        if self.base_path and not p.is_absolute():
            return self.base_path / p
        return p

    def read(self, path: Union[str, Path]) -> FileContent:
        resolved = self._resolve_path(path)
        if not resolved.exists():
            return FileContent(
                content="",
                path=str(resolved),
                exists=False,
            )
        content = resolved.read_text(encoding="utf-8")
        return FileContent(
            content=content,
            path=str(resolved),
            size=len(content),
            exists=True,
        )

    def write(
        self,
        path: Union[str, Path],
        content: str,
        encoding: str = "utf-8",
    ) -> bool:
        resolved = self._resolve_path(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding=encoding)
        return True

    def exists(self, path: Union[str, Path]) -> bool:
        return self._resolve_path(path).exists()

    def delete(self, path: Union[str, Path]) -> bool:
        resolved = self._resolve_path(path)
        if resolved.exists():
            resolved.unlink()
        return True

    def list_files(
        self,
        directory: Union[str, Path],
        pattern: str = "*",
        recursive: bool = False,
    ) -> List[str]:
        resolved = self._resolve_path(directory)
        if not resolved.exists():
            return []
        if recursive:
            return [str(p) for p in resolved.rglob(pattern) if p.is_file()]
        return [str(p) for p in resolved.glob(pattern) if p.is_file()]


