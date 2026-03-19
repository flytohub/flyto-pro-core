"""
Dependency Injection Container

Provides a centralized registry for service instances,
replacing scattered singleton patterns across the codebase.

Features:
- Lazy initialization via factories
- Scoped instances (singleton, transient)
- Thread-safe operations
- Easy testing via reset()

Usage:
    from flyto_pro_core.core.container import container

    # Register instance directly
    container.register("qdrant_client", client)

    # Register factory for lazy init
    container.register_factory("job_manager", lambda: JobManager())

    # Get service
    manager = container.get("job_manager")

    # Testing: reset all services
    container.reset()
"""

import logging
import threading
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar, Generic

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceScope(Enum):
    """Service lifetime scope."""
    SINGLETON = "singleton"   # One instance for entire app
    TRANSIENT = "transient"   # New instance each time


class ServiceDescriptor:
    """Describes how to create and manage a service."""

    def __init__(
        self,
        name: str,
        factory: Optional[Callable[[], Any]] = None,
        instance: Optional[Any] = None,
        scope: ServiceScope = ServiceScope.SINGLETON,
    ):
        self.name = name
        self.factory = factory
        self.instance = instance
        self.scope = scope
        self._lock = threading.Lock()

    def get_instance(self) -> Any:
        """Get or create the service instance."""
        if self.scope == ServiceScope.TRANSIENT and self.factory:
            return self.factory()

        if self.instance is not None:
            return self.instance

        if self.factory is None:
            raise ValueError(f"Service '{self.name}' has no factory or instance")

        with self._lock:
            # Double-check after acquiring lock
            if self.instance is not None:
                return self.instance

            logger.debug(f"Creating service: {self.name}")
            self.instance = self.factory()
            return self.instance

    def reset(self) -> None:
        """Reset the service instance (for testing)."""
        with self._lock:
            self.instance = None


class ServiceContainer:
    """
    Dependency Injection Container

    Thread-safe container for managing service instances.
    Replaces scattered singleton patterns.
    """

    def __init__(self):
        self._services: Dict[str, ServiceDescriptor] = {}
        self._lock = threading.RLock()

    def register(
        self,
        name: str,
        instance: Any,
        scope: ServiceScope = ServiceScope.SINGLETON,
    ) -> None:
        """
        Register a service instance directly.

        Args:
            name: Service identifier
            instance: Service instance
            scope: Service lifetime scope
        """
        with self._lock:
            if name in self._services:
                logger.warning(f"Overwriting service: {name}")

            self._services[name] = ServiceDescriptor(
                name=name,
                instance=instance,
                scope=scope,
            )
            logger.debug(f"Registered service: {name}")

    def register_factory(
        self,
        name: str,
        factory: Callable[[], Any],
        scope: ServiceScope = ServiceScope.SINGLETON,
    ) -> None:
        """
        Register a factory for lazy service initialization.

        Args:
            name: Service identifier
            factory: Callable that creates the service
            scope: Service lifetime scope
        """
        with self._lock:
            if name in self._services:
                logger.warning(f"Overwriting service factory: {name}")

            self._services[name] = ServiceDescriptor(
                name=name,
                factory=factory,
                scope=scope,
            )
            logger.debug(f"Registered service factory: {name}")

    def get(self, name: str) -> Any:
        """
        Get a service by name.

        Args:
            name: Service identifier

        Returns:
            Service instance

        Raises:
            KeyError: If service not registered
        """
        with self._lock:
            if name not in self._services:
                raise KeyError(f"Service not registered: {name}")

            return self._services[name].get_instance()

    def get_optional(self, name: str) -> Optional[Any]:
        """
        Get a service by name, returning None if not found.

        Args:
            name: Service identifier

        Returns:
            Service instance or None
        """
        try:
            return self.get(name)
        except KeyError:
            return None

    def has(self, name: str) -> bool:
        """Check if a service is registered."""
        with self._lock:
            return name in self._services

    def reset(self, name: Optional[str] = None) -> None:
        """
        Reset service instance(s) for testing.

        Args:
            name: Specific service to reset, or None for all
        """
        with self._lock:
            if name:
                if name in self._services:
                    self._services[name].reset()
                    logger.debug(f"Reset service: {name}")
            else:
                for service in self._services.values():
                    service.reset()
                logger.debug("Reset all services")

    def clear(self) -> None:
        """Remove all registered services."""
        with self._lock:
            self._services.clear()
            logger.debug("Cleared all services")

    def list_services(self) -> list:
        """List all registered service names."""
        with self._lock:
            return list(self._services.keys())


# Global container instance
container = ServiceContainer()


def register_core_services() -> None:
    """
    Register core flyto-pro services.

    Called during application startup or via flyto_pro.configure().
    Skips services that are already registered (e.g. by configure()).
    """
    def _register_if_missing(name: str, factory):
        if not container.has(name):
            container.register_factory(name, factory)

    # ── Interface providers (auto-detect from env) ────────────
    _register_if_missing("llm_service", _create_llm_service)
    _register_if_missing("embedding_service", _create_embedding_service)
    _register_if_missing("vector_store", _create_vector_store)

    # ── Legacy qdrant_client (for backward compat) ────────────
    _register_if_missing("qdrant_client", _create_qdrant_client)

    # ── Tenant manager ────────────────────────────────────────
    _register_if_missing("tenant_manager", _create_tenant_manager)

    # ── Prompt library ────────────────────────────────────────
    _register_if_missing("prompt_library", _create_prompt_library)

    # ── EMS services ──────────────────────────────────────────
    _register_if_missing("context_storage", _create_context_storage)
    _register_if_missing("job_manager", _create_job_manager)
    _register_if_missing("attempt_manager", _create_attempt_manager)

    # ── Contract services ─────────────────────────────────────
    _register_if_missing("contract_registry", _create_contract_registry)
    _register_if_missing("contract_engine", _create_contract_engine)

    logger.info("Core services registered")


# Factory functions - lazy imports to avoid circular dependencies


def _create_llm_service():
    """Create LLM service from environment (OpenAI if available)."""
    try:
        import os

        if os.getenv("OPENAI_API_KEY"):
            from flyto_pro_core.interfaces.providers.openai_llm import OpenAILLMService

            return OpenAILLMService()
        logger.debug("No OPENAI_API_KEY set, llm_service not created")
        return None
    except ImportError:
        logger.debug("openai not installed, llm_service not created")
        return None


def _create_embedding_service():
    """Create embedding service from environment (OpenAI if available)."""
    try:
        import os

        if os.getenv("OPENAI_API_KEY"):
            from flyto_pro_core.interfaces.providers.openai_llm import (
                OpenAIEmbeddingService,
            )

            return OpenAIEmbeddingService()
        logger.debug("No OPENAI_API_KEY set, embedding_service not created")
        return None
    except ImportError:
        logger.debug("openai not installed, embedding_service not created")
        return None


def _create_vector_store():
    """Create vector store from environment (Qdrant if available)."""
    try:
        import os

        if os.getenv("QDRANT_URL"):
            from flyto_pro_core.interfaces.providers.qdrant_store import QdrantVectorStore

            return QdrantVectorStore()
        logger.debug("No QDRANT_URL set, vector_store not created")
        return None
    except ImportError:
        logger.debug("qdrant-client not installed, vector_store not created")
        return None


def _create_qdrant_client():
    """Create Qdrant client. Extended by flyto-pro (licensed)."""
    return None


def _create_tenant_manager():
    """Create tenant manager. Extended by flyto-pro (licensed)."""
    return None


def _create_prompt_library():
    """Create prompt library. Extended by flyto-pro (licensed)."""
    return None


def _create_context_storage():
    """Create context storage. Extended by flyto-pro (licensed)."""
    return None


def _create_job_manager():
    """Create job manager. Extended by flyto-pro (licensed)."""
    return None


def _create_attempt_manager():
    """Create attempt manager. Extended by flyto-pro (licensed)."""
    return None


def _create_contract_registry():
    """Create contract registry."""
    try:
        from flyto_pro_core.contract.registry.contract_registry import ContractRegistry
        return ContractRegistry()
    except Exception as e:
        logger.error(f"Failed to create ContractRegistry: {e}")
        return None


def _create_contract_engine():
    """Create contract engine."""
    try:
        from flyto_pro_core.contract.engine import ContractEngine
        return ContractEngine()
    except Exception as e:
        logger.error(f"Failed to create ContractEngine: {e}")
        return None


# Convenience functions for type-safe access

def get_qdrant_client():
    """Get Qdrant client from container."""
    return container.get("qdrant_client")


def get_job_manager():
    """Get job manager from container."""
    return container.get("job_manager")


def get_contract_registry():
    """Get contract registry from container."""
    return container.get("contract_registry")


def get_llm_service():
    """Get LLM service from container."""
    return container.get("llm_service")


def get_embedding_service():
    """Get embedding service from container."""
    return container.get("embedding_service")


def get_vector_store():
    """Get vector store from container."""
    return container.get("vector_store")
