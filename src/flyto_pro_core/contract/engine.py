"""
Contract Engine - Main Entry Point

The Contract Engine is the single source of truth for:
- Module contracts (what modules can do)
- Workflow validation (is this workflow valid)
- Connection rules (can these modules connect)
- Binding resolution (what data is available)
- Workflow compilation (prepare for execution)

Cloud renders what this engine says.
Pro plans based on what this engine knows.
Core validates using this engine's rules.

Usage:
    engine = ContractEngine()
    await engine.initialize()

    # API 1: Validate workflow
    report = await engine.validate_workflow(spec)

    # API 2: Get connectability
    candidates = await engine.get_connectability("node_1", "out", "output")

    # API 3: Get available bindings
    bindings = await engine.get_available_bindings(spec, "node_3")

    # API 4: Compile workflow
    plan = await engine.compile(spec)

    # API 5: Get catalog (for LLM)
    outline = engine.get_catalog_outline()
    detail = engine.get_catalog_detail(["browser", "data"])
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .models.workflow_spec import WorkflowSpec
from .models.module_contract import ModuleContract
from .registry.contract_registry import ContractRegistry, CatalogOutline, CatalogDetail
from .validator.workflow_validator import WorkflowValidator, ValidationReport
from .binder.binding_resolver import BindingResolver, BindingTree
from .compiler.workflow_compiler import WorkflowCompiler, ExecutablePlan

logger = logging.getLogger(__name__)


class ContractEngine:
    """
    Main entry point for the Contract Engine.

    This is the AUTHORITATIVE source for all contract-related operations.
    Cloud should never make decisions about validity, connections, or
    bindings - it should always ask this engine.
    """

    _instance: Optional[ContractEngine] = None

    def __init__(self):
        self.registry = ContractRegistry()
        self.validator: Optional[WorkflowValidator] = None
        self.binder: Optional[BindingResolver] = None
        self.compiler: Optional[WorkflowCompiler] = None
        self._initialized = False

    @classmethod
    def instance(cls) -> ContractEngine:
        """
        Get singleton instance.

        Prefers DI container, falls back to class-level singleton.
        """
        # Try DI container first
        try:
            from flyto_pro_core.core.container import container
            if container.has("contract_engine"):
                return container.get("contract_engine")
        except ImportError:
            pass

        # Fall back to class-level singleton
        if cls._instance is None:
            cls._instance = ContractEngine()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing)."""
        cls._instance = None
        try:
            from flyto_pro_core.core.container import container
            container.reset("contract_engine")
        except ImportError:
            pass

    async def initialize(self, load_from_core: bool = True) -> None:
        """
        Initialize the Contract Engine.

        Args:
            load_from_core: Whether to load contracts from flyto-core
        """
        if self._initialized:
            return

        # Initialize registry
        await self.registry.initialize(load_from_core)

        # Initialize components
        self.validator = WorkflowValidator(self.registry)
        self.binder = BindingResolver(self.registry)
        self.compiler = WorkflowCompiler(self.registry)

        self._initialized = True
        logger.info("ContractEngine initialized")

    def _ensure_initialized(self) -> None:
        """Ensure engine is initialized."""
        if not self._initialized:
            raise RuntimeError("ContractEngine not initialized. Call initialize() first.")

    # =========================================================================
    # API 1: validate_workflow(spec) -> ValidationReport
    # =========================================================================

    async def validate_workflow(self, spec: WorkflowSpec) -> ValidationReport:
        """
        Validate a workflow specification.

        This is the AUTHORITATIVE validation. Cloud should display
        exactly what this returns - no local validation needed.

        Args:
            spec: The workflow specification to validate

        Returns:
            ValidationReport with errors, warnings, and diagnostics
        """
        self._ensure_initialized()
        return await self.validator.validate(spec)

    async def validate_edge(
        self,
        from_module_id: str,
        from_port_id: str,
        to_module_id: str,
        to_port_id: str,
    ) -> tuple[bool, Optional[str]]:
        """
        Validate a single edge connection.

        Convenience method for quick edge validation without full workflow.

        Returns:
            Tuple of (is_valid, error_message)
        """
        self._ensure_initialized()
        return await self.validator.validate_edge(
            from_module_id, from_port_id, to_module_id, to_port_id
        )

    # =========================================================================
    # API 2: get_connectability(node_id, port_id, direction) -> candidates
    # =========================================================================

    async def get_connectability(
        self,
        module_id: str,
        port_id: str,
        direction: str = "output",
    ) -> List[Dict[str, Any]]:
        """
        Get list of modules that can connect to/from a port.

        Cloud uses this to show connection suggestions when
        the user drags from a port.

        Args:
            module_id: The module to check
            port_id: The port to check
            direction: "output" (what can this connect to) or "input" (what can connect here)

        Returns:
            List of candidate modules with match scores, sorted by relevance
        """
        self._ensure_initialized()
        return self.registry.get_connectability(module_id, port_id, direction)

    # =========================================================================
    # API 3: get_available_bindings(spec, node_id) -> BindingTree
    # =========================================================================

    async def get_available_bindings(
        self,
        spec: WorkflowSpec,
        node_id: str,
    ) -> BindingTree:
        """
        Get all available variable bindings for a node.

        Cloud uses this to populate value selectors - showing
        what data sources are available for each parameter.

        Args:
            spec: The workflow specification
            node_id: The node to get bindings for

        Returns:
            BindingTree with all available bindings organized by source
        """
        self._ensure_initialized()
        return await self.binder.get_available_bindings(spec, node_id)

    # =========================================================================
    # API 4: compile(spec) -> ExecutablePlan
    # =========================================================================

    async def compile(
        self,
        spec: WorkflowSpec,
        skip_validation: bool = False,
    ) -> ExecutablePlan:
        """
        Compile a workflow specification into an executable plan.

        The plan contains everything needed to execute:
        - Resolved port bindings
        - Pre-computed routing rules
        - Validated type information
        - Scope injection points

        Args:
            spec: The workflow specification to compile
            skip_validation: Skip validation (for trusted/cached specs)

        Returns:
            ExecutablePlan ready for execution

        Raises:
            CompilationError: If workflow is invalid
        """
        self._ensure_initialized()
        return await self.compiler.compile(spec, skip_validation)

    # =========================================================================
    # Module/Contract Access
    # =========================================================================

    def get_contract(self, module_id: str) -> Optional[ModuleContract]:
        """Get a module contract by ID."""
        self._ensure_initialized()
        return self.registry.get(module_id)

    def has_module(self, module_id: str) -> bool:
        """Check if a module exists."""
        self._ensure_initialized()
        return self.registry.has(module_id)

    def search_modules(self, query: str, limit: int = 20) -> List[ModuleContract]:
        """Search modules by query string."""
        self._ensure_initialized()
        return self.registry.search(query, limit)

    # =========================================================================
    # Catalog (for LLM two-stage lookup)
    # =========================================================================

    def get_catalog_outline(self) -> CatalogOutline:
        """
        Get high-level catalog outline for LLM.

        This is the first stage of the two-stage catalog lookup.
        LLM sees categories and counts, not individual modules.

        Returns:
            CatalogOutline with categories and module counts
        """
        self._ensure_initialized()
        return self.registry.get_catalog_outline()

    def get_catalog_detail(self, categories: List[str]) -> CatalogDetail:
        """
        Get detailed catalog for specific categories.

        This is the second stage - LLM requests detail for
        categories it's interested in.

        Args:
            categories: List of category names to get detail for

        Returns:
            CatalogDetail with module information
        """
        self._ensure_initialized()
        return self.registry.get_catalog_detail(categories)

    # =========================================================================
    # Version Compatibility
    # =========================================================================

    def check_version_compatibility(
        self,
        module_id: str,
        required_version: str,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a module version is compatible with required version.

        Args:
            module_id: Module to check
            required_version: Required version string

        Returns:
            Tuple of (is_compatible, reason_if_not)
        """
        self._ensure_initialized()
        return self.registry.check_version_compatibility(module_id, required_version)

    def get_migrations(
        self,
        module_id: str,
        from_version: str,
        to_version: str,
    ) -> List[Dict[str, Any]]:
        """
        Get migration steps for a module version upgrade.

        Returns:
            List of migration steps (spec patches)
        """
        self._ensure_initialized()
        return self.registry.get_migrations(module_id, from_version, to_version)

    # =========================================================================
    # Registration (for dynamic modules)
    # =========================================================================

    def register_contract(self, contract: ModuleContract) -> None:
        """
        Register a module contract.

        Used for dynamically registering modules at runtime.
        """
        self._ensure_initialized()
        self.registry.register(contract)

    def unregister_contract(self, module_id: str) -> None:
        """Remove a contract from the registry."""
        self._ensure_initialized()
        self.registry.unregister(module_id)


# Convenience function for quick access
async def get_engine() -> ContractEngine:
    """Get initialized ContractEngine instance."""
    engine = ContractEngine.instance()
    if not engine._initialized:
        await engine.initialize()
    return engine
