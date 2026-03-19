"""
Contract Registry

Central registry for module contracts. Bridges flyto-core ModuleRegistry
with the Contract Engine by loading and caching contracts.

Usage:
    registry = ContractRegistry()
    await registry.initialize()

    # Get a contract
    contract = registry.get("browser.goto")

    # Get all contracts in a category
    browser_contracts = registry.get_by_category("browser")

    # Get catalog for LLM (outline only)
    catalog = registry.get_catalog_outline()

    # Get detail for specific categories
    detail = registry.get_catalog_detail(["browser", "data"])
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from pathlib import Path
import json

from ..models.module_contract import ModuleContract, ConnectionPolicy
from ..models.port import Port, PortDirection, EdgeType
from ..models.params_schema import ParamsSchema
from ..models.data_contract import DataContract

logger = logging.getLogger(__name__)


@dataclass
class CategoryInfo:
    """Information about a module category."""

    name: str
    label: str
    description: str
    icon: Optional[str] = None
    count: int = 0
    subcategories: List[str] = field(default_factory=list)
    typical_tasks: List[str] = field(default_factory=list)


@dataclass
class CatalogOutline:
    """
    High-level catalog for LLM consumption.

    This is the "outline" that LLM sees first to understand
    what's available without loading all module details.
    """

    version: str
    total_modules: int
    categories: List[CategoryInfo] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "total_modules": self.total_modules,
            "categories": [
                {
                    "name": c.name,
                    "label": c.label,
                    "description": c.description,
                    "icon": c.icon,
                    "count": c.count,
                    "subcategories": c.subcategories,
                    "typical_tasks": c.typical_tasks,
                }
                for c in self.categories
            ],
        }


@dataclass
class CatalogDetail:
    """
    Detailed catalog for specific categories.

    This is what LLM sees after selecting categories to explore.
    """

    categories: List[str]
    modules: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "categories": self.categories,
            "modules": self.modules,
        }


class ContractRegistry:
    """
    Central registry for module contracts.

    Loads contracts from:
    1. flyto-core ModuleRegistry (primary source)
    2. Contract override files (for enhanced contracts)
    3. Dynamic registration at runtime
    """

    _instance: Optional[ContractRegistry] = None

    def __init__(self):
        self._contracts: Dict[str, ModuleContract] = {}
        self._categories: Dict[str, CategoryInfo] = {}
        self._initialized = False
        self._version = "1.0.0"

    @classmethod
    def instance(cls) -> ContractRegistry:
        """
        Get singleton instance.

        Prefers DI container, falls back to class-level singleton.
        """
        # Try DI container first
        try:
            from flyto_pro_core.core.container import container
            if container.has("contract_registry"):
                return container.get("contract_registry")
        except ImportError:
            pass

        # Fall back to class-level singleton
        if cls._instance is None:
            cls._instance = ContractRegistry()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing)."""
        cls._instance = None
        try:
            from flyto_pro_core.core.container import container
            container.reset("contract_registry")
        except ImportError:
            pass

    async def initialize(self, load_from_core: bool = True) -> None:
        """
        Initialize the registry.

        Args:
            load_from_core: Whether to load from flyto-core ModuleRegistry
        """
        if self._initialized:
            return

        if load_from_core:
            await self._load_from_core()

        # Load any contract overrides
        await self._load_overrides()

        # Build category index
        self._build_category_index()

        self._initialized = True
        logger.info(f"ContractRegistry initialized with {len(self._contracts)} contracts")

    async def _load_from_core(self) -> None:
        """Load contracts from flyto-core ModuleRegistry."""
        try:
            from core.modules.registry import ModuleRegistry

            all_metadata = ModuleRegistry.get_all_metadata()

            for module_id, metadata in all_metadata.items():
                try:
                    contract = ModuleContract.from_flyto_core_metadata(module_id, metadata)
                    self._contracts[module_id] = contract
                except Exception as e:
                    logger.warning(f"Failed to load contract for {module_id}: {e}")

            logger.info(f"Loaded {len(self._contracts)} contracts from flyto-core")

        except ImportError:
            logger.warning("flyto-core not available, skipping core module loading")
        except Exception as e:
            logger.error(f"Error loading from core: {e}")

    async def _load_overrides(self) -> None:
        """Load contract overrides from files."""
        override_dir = Path(__file__).parent.parent / "overrides"

        if not override_dir.exists():
            return

        for file_path in override_dir.glob("*.json"):
            try:
                with open(file_path) as f:
                    data = json.load(f)

                if isinstance(data, list):
                    for item in data:
                        contract = ModuleContract.from_dict(item)
                        self._contracts[contract.module_id] = contract
                else:
                    contract = ModuleContract.from_dict(data)
                    self._contracts[contract.module_id] = contract

                logger.debug(f"Loaded contract override from {file_path}")

            except Exception as e:
                logger.warning(f"Failed to load override {file_path}: {e}")

    def _build_category_index(self) -> None:
        """Build category index from loaded contracts."""
        self._categories.clear()

        for contract in self._contracts.values():
            category = contract.category or "other"

            if category not in self._categories:
                self._categories[category] = CategoryInfo(
                    name=category,
                    label=category.replace("_", " ").title(),
                    description=f"Modules for {category} operations",
                    count=0,
                    subcategories=[],
                    typical_tasks=[],
                )

            self._categories[category].count += 1

            # Track subcategories from module_id
            if "." in contract.module_id:
                parts = contract.module_id.split(".")
                if len(parts) > 1:
                    subcategory = parts[1]
                    if subcategory not in self._categories[category].subcategories:
                        self._categories[category].subcategories.append(subcategory)

    def register(self, contract: ModuleContract) -> None:
        """
        Register a module contract.

        Args:
            contract: The contract to register
        """
        self._contracts[contract.module_id] = contract

        # Update category index
        category = contract.category or "other"
        if category in self._categories:
            self._categories[category].count += 1
        else:
            self._categories[category] = CategoryInfo(
                name=category,
                label=category.replace("_", " ").title(),
                description=f"Modules for {category} operations",
                count=1,
            )

    def unregister(self, module_id: str) -> None:
        """Remove a contract from the registry."""
        if module_id in self._contracts:
            contract = self._contracts[module_id]
            category = contract.category or "other"

            del self._contracts[module_id]

            if category in self._categories:
                self._categories[category].count -= 1

    def get(self, module_id: str) -> Optional[ModuleContract]:
        """Get a contract by module ID."""
        return self._contracts.get(module_id)

    def has(self, module_id: str) -> bool:
        """Check if a contract exists."""
        return module_id in self._contracts

    def get_all(self) -> Dict[str, ModuleContract]:
        """Get all contracts."""
        return self._contracts.copy()

    def get_by_category(self, category: str) -> List[ModuleContract]:
        """Get all contracts in a category."""
        return [c for c in self._contracts.values() if c.category == category]

    def get_by_tags(self, tags: List[str]) -> List[ModuleContract]:
        """Get all contracts with any of the given tags."""
        return [
            c for c in self._contracts.values()
            if any(t in c.tags for t in tags)
        ]

    def search(self, query: str, limit: int = 20) -> List[ModuleContract]:
        """
        Search contracts by query string.

        Searches module_id, label, description, and tags.
        """
        query_lower = query.lower()
        results = []

        for contract in self._contracts.values():
            score = 0

            # Exact module_id match
            if contract.module_id == query:
                score = 100
            # Module ID contains query
            elif query_lower in contract.module_id.lower():
                score = 50
            # Label contains query
            elif query_lower in contract.label.lower():
                score = 40
            # Description contains query
            elif query_lower in contract.description.lower():
                score = 20
            # Tag matches
            elif any(query_lower in tag.lower() for tag in contract.tags):
                score = 30

            if score > 0:
                results.append((score, contract))

        # Sort by score descending
        results.sort(key=lambda x: x[0], reverse=True)

        return [contract for _, contract in results[:limit]]

    def get_catalog_outline(self) -> CatalogOutline:
        """
        Get high-level catalog outline for LLM.

        This is the first stage of the two-stage catalog lookup.
        """
        return CatalogOutline(
            version=self._version,
            total_modules=len(self._contracts),
            categories=list(self._categories.values()),
        )

    def get_catalog_detail(self, categories: List[str]) -> CatalogDetail:
        """
        Get detailed catalog for specific categories.

        This is the second stage of the two-stage catalog lookup.
        """
        modules = []

        for category in categories:
            for contract in self.get_by_category(category):
                modules.append({
                    "module_id": contract.module_id,
                    "label": contract.label,
                    "description": contract.description,
                    "category": contract.category,
                    "version": contract.version,
                    "ports": [p.to_dict() for p in contract.ports],
                    "params_schema": contract.params_schema.to_dict() if contract.params_schema else None,
                    "tags": contract.tags,
                    "tier": contract.tier,
                })

        return CatalogDetail(categories=categories, modules=modules)

    def get_connectability(
        self,
        module_id: str,
        port_id: str,
        direction: str = "output",
    ) -> List[Dict[str, Any]]:
        """
        Get list of modules that can connect to/from a port.

        Args:
            module_id: The module to check
            port_id: The port to check
            direction: "output" (what can this connect to) or "input" (what can connect here)

        Returns:
            List of candidate modules with match scores
        """
        contract = self.get(module_id)
        if not contract:
            return []

        port = contract.get_port(port_id)
        if not port:
            return []

        candidates = []

        for other_contract in self._contracts.values():
            if other_contract.module_id == module_id:
                continue  # Skip self

            # Find compatible ports on the other module
            if direction == "output":
                # We're connecting FROM this port TO another module's input
                target_ports = other_contract.get_input_ports()
                for target_port in target_ports:
                    can_connect, reason = contract.can_connect_to(
                        other_contract, port_id, target_port.id
                    )
                    if can_connect:
                        score = self._calculate_match_score(port, target_port, other_contract)
                        candidates.append({
                            "module_id": other_contract.module_id,
                            "port_id": target_port.id,
                            "label": other_contract.label,
                            "category": other_contract.category,
                            "score": score,
                        })
            else:
                # We're looking for what can connect TO this port
                source_ports = other_contract.get_output_ports()
                for source_port in source_ports:
                    can_connect, reason = other_contract.can_connect_to(
                        contract, source_port.id, port_id
                    )
                    if can_connect:
                        score = self._calculate_match_score(source_port, port, other_contract)
                        candidates.append({
                            "module_id": other_contract.module_id,
                            "port_id": source_port.id,
                            "label": other_contract.label,
                            "category": other_contract.category,
                            "score": score,
                        })

        # Sort by score descending
        candidates.sort(key=lambda x: x["score"], reverse=True)

        return candidates

    def _calculate_match_score(
        self,
        from_port: Port,
        to_port: Port,
        target_contract: ModuleContract,
    ) -> int:
        """Calculate compatibility score between ports."""
        score = 0

        # Edge type match (required but not scored)
        if from_port.edge_type != to_port.edge_type:
            return 0

        # Data type exact match
        if from_port.data_type == to_port.data_type:
            score += 50
        elif from_port.data_type == "any" or to_port.data_type == "any":
            score += 30
        elif from_port.is_compatible_type(to_port):
            score += 20

        # Same category bonus
        # (Not applicable here as we don't have source contract in this method)

        return score

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
        contract = self.get(module_id)
        if not contract:
            return False, f"Module {module_id} not found"

        if contract.is_compatible_with(required_version):
            return True, None

        return False, (
            f"Module {module_id} version {contract.version} "
            f"is not compatible with required version {required_version}"
        )

    def get_migrations(
        self,
        module_id: str,
        from_version: str,
        to_version: str,
    ) -> List[Dict[str, Any]]:
        """
        Get migration steps for a module version upgrade.

        Returns migration steps needed to upgrade from one version to another.
        """
        migrations = []

        contract = self.get(module_id)
        if not contract:
            return migrations

        # Check if contract has migration info
        if hasattr(contract, 'migrations'):
            all_migrations = contract.migrations or []

            # Parse versions
            from packaging import version
            try:
                from_v = version.parse(from_version)
                to_v = version.parse(to_version)
            except Exception:
                return migrations

            # Filter migrations in range
            for migration in all_migrations:
                try:
                    mig_from = version.parse(migration.get("from_version", "0.0.0"))
                    mig_to = version.parse(migration.get("to_version", "0.0.0"))

                    if from_v <= mig_from and mig_to <= to_v:
                        migrations.append(migration)
                except Exception:
                    continue

            # Sort by version
            migrations.sort(key=lambda m: version.parse(m.get("from_version", "0.0.0")))

        return migrations
