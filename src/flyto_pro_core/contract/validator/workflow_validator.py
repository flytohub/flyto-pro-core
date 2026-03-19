"""
Workflow Validator

Validates workflow specifications against module contracts.
This is the AUTHORITATIVE validator - Cloud trusts this completely.

Validation checks:
1. All modules exist and are available
2. All edges connect valid ports
3. Edge types match (data to data, control to control)
4. Data types are compatible
5. Required parameters are present and valid
6. No cycles in non-loop paths
7. Entry nodes are valid
8. Version compatibility

Usage:
    validator = WorkflowValidator(registry)
    report = await validator.validate(workflow_spec)

    if not report.is_valid:
        for error in report.errors:
            print(f"Error: {error.message}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from ..models.workflow_spec import WorkflowSpec, NodeSpec, EdgeSpec
from ..models.module_contract import ModuleContract
from ..models.port import Port, PortDirection, EdgeType
from ..registry.contract_registry import ContractRegistry

logger = logging.getLogger(__name__)


class IssueSeverity(str, Enum):
    """Severity of validation issues."""

    ERROR = "error"  # Cannot execute
    WARNING = "warning"  # Can execute but may have issues
    INFO = "info"  # Informational


class IssueType(str, Enum):
    """Types of validation issues."""

    # Module issues
    MODULE_NOT_FOUND = "module_not_found"
    MODULE_DEPRECATED = "module_deprecated"
    MODULE_VERSION_MISMATCH = "module_version_mismatch"

    # Port issues
    PORT_NOT_FOUND = "port_not_found"
    PORT_DIRECTION_INVALID = "port_direction_invalid"
    PORT_MAX_CONNECTIONS = "port_max_connections"

    # Edge issues
    EDGE_TYPE_MISMATCH = "edge_type_mismatch"
    DATA_TYPE_MISMATCH = "data_type_mismatch"
    CONNECTION_POLICY_VIOLATION = "connection_policy_violation"

    # Parameter issues
    PARAM_REQUIRED_MISSING = "param_required_missing"
    PARAM_TYPE_INVALID = "param_type_invalid"
    PARAM_VALIDATION_FAILED = "param_validation_failed"

    # Structure issues
    CYCLE_DETECTED = "cycle_detected"
    NO_ENTRY_NODE = "no_entry_node"
    ORPHAN_NODE = "orphan_node"
    DANGLING_EDGE = "dangling_edge"

    # Other
    DUPLICATE_ID = "duplicate_id"
    CUSTOM = "custom"


@dataclass
class ValidationIssue:
    """A single validation issue."""

    severity: IssueSeverity
    type: IssueType
    message: str
    node_id: Optional[str] = None
    edge_id: Optional[str] = None
    param_name: Optional[str] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "type": self.type.value,
            "message": self.message,
            "node_id": self.node_id,
            "edge_id": self.edge_id,
            "param_name": self.param_name,
            "suggestion": self.suggestion,
        }


@dataclass
class EdgeDiagnostic:
    """Diagnostic information for an edge."""

    edge_id: str
    from_node: str
    from_port: str
    to_node: str
    to_port: str
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    from_type: Optional[str] = None
    to_type: Optional[str] = None
    edge_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "from_node": self.from_node,
            "from_port": self.from_port,
            "to_node": self.to_node,
            "to_port": self.to_port,
            "is_valid": self.is_valid,
            "issues": [i.to_dict() for i in self.issues],
            "from_type": self.from_type,
            "to_type": self.to_type,
            "edge_type": self.edge_type,
        }


@dataclass
class ValidationReport:
    """Complete validation report for a workflow."""

    is_valid: bool
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    info: List[ValidationIssue] = field(default_factory=list)
    edge_diagnostics: List[EdgeDiagnostic] = field(default_factory=list)
    entry_nodes: List[str] = field(default_factory=list)
    execution_order: List[str] = field(default_factory=list)

    @property
    def all_issues(self) -> List[ValidationIssue]:
        """Get all issues."""
        return self.errors + self.warnings + self.info

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "info": [i.to_dict() for i in self.info],
            "edge_diagnostics": [e.to_dict() for e in self.edge_diagnostics],
            "entry_nodes": self.entry_nodes,
            "execution_order": self.execution_order,
        }


class WorkflowValidator:
    """
    Validates workflow specifications against module contracts.

    This is the single source of truth for workflow validity.
    Cloud should never do its own validation - always ask Core.
    """

    def __init__(self, registry: Optional[ContractRegistry] = None):
        self.registry = registry or ContractRegistry.instance()

    async def validate(self, spec: WorkflowSpec) -> ValidationReport:
        """
        Validate a complete workflow specification.

        Args:
            spec: The workflow specification to validate

        Returns:
            ValidationReport with all issues found
        """
        errors: List[ValidationIssue] = []
        warnings: List[ValidationIssue] = []
        info: List[ValidationIssue] = []
        edge_diagnostics: List[EdgeDiagnostic] = []

        # 1. Check for duplicate IDs
        self._check_duplicate_ids(spec, errors)

        # 2. Validate all nodes
        node_contracts: Dict[str, ModuleContract] = {}
        for node in spec.nodes:
            contract = await self._validate_node(node, errors, warnings, info)
            if contract:
                node_contracts[node.id] = contract

        # 3. Validate all edges
        for edge in spec.edges:
            diagnostic = await self._validate_edge(edge, spec, node_contracts, errors, warnings)
            edge_diagnostics.append(diagnostic)

        # 4. Check for cycles
        try:
            execution_order = spec.topological_sort()
        except ValueError as e:
            errors.append(ValidationIssue(
                severity=IssueSeverity.ERROR,
                type=IssueType.CYCLE_DETECTED,
                message=str(e),
            ))
            execution_order = []

        # 5. Validate entry nodes
        entry_nodes = self._validate_entry_nodes(spec, errors, warnings)

        # 6. Check for orphan nodes
        self._check_orphan_nodes(spec, warnings)

        # 7. Check port connection limits
        self._check_connection_limits(spec, node_contracts, errors)

        # Determine overall validity
        is_valid = len(errors) == 0

        return ValidationReport(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            info=info,
            edge_diagnostics=edge_diagnostics,
            entry_nodes=entry_nodes,
            execution_order=execution_order,
        )

    def _check_duplicate_ids(
        self,
        spec: WorkflowSpec,
        errors: List[ValidationIssue],
    ) -> None:
        """Check for duplicate node/edge IDs."""
        node_ids: Set[str] = set()
        for node in spec.nodes:
            if node.id in node_ids:
                errors.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    type=IssueType.DUPLICATE_ID,
                    message=f"Duplicate node ID: {node.id}",
                    node_id=node.id,
                ))
            node_ids.add(node.id)

        edge_ids: Set[str] = set()
        for edge in spec.edges:
            if edge.id and edge.id in edge_ids:
                errors.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    type=IssueType.DUPLICATE_ID,
                    message=f"Duplicate edge ID: {edge.id}",
                    edge_id=edge.id,
                ))
            if edge.id:
                edge_ids.add(edge.id)

    async def _validate_node(
        self,
        node: NodeSpec,
        errors: List[ValidationIssue],
        warnings: List[ValidationIssue],
        info: List[ValidationIssue],
    ) -> Optional[ModuleContract]:
        """Validate a single node."""
        # Check module exists
        contract = self.registry.get(node.module_id)
        if not contract:
            errors.append(ValidationIssue(
                severity=IssueSeverity.ERROR,
                type=IssueType.MODULE_NOT_FOUND,
                message=f"Module not found: {node.module_id}",
                node_id=node.id,
            ))
            return None

        # Check deprecation
        if contract.deprecated:
            replacement = f" Use {contract.deprecated_by} instead." if contract.deprecated_by else ""
            warnings.append(ValidationIssue(
                severity=IssueSeverity.WARNING,
                type=IssueType.MODULE_DEPRECATED,
                message=f"Module {node.module_id} is deprecated.{replacement}",
                node_id=node.id,
                suggestion=contract.deprecated_by,
            ))

        # Check version compatibility
        if node.version_required:
            compatible, reason = self.registry.check_version_compatibility(
                node.module_id, node.version_required
            )
            if not compatible:
                errors.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    type=IssueType.MODULE_VERSION_MISMATCH,
                    message=reason or f"Version mismatch for {node.module_id}",
                    node_id=node.id,
                ))

        # Validate parameters
        if contract.params_schema:
            is_valid, param_errors = contract.params_schema.validate(node.params)
            if not is_valid:
                for param_name, error_msg in param_errors.items():
                    errors.append(ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        type=IssueType.PARAM_VALIDATION_FAILED,
                        message=f"Parameter '{param_name}': {error_msg}",
                        node_id=node.id,
                        param_name=param_name,
                    ))

        # Info: node is disabled
        if node.disabled:
            info.append(ValidationIssue(
                severity=IssueSeverity.INFO,
                type=IssueType.CUSTOM,
                message=f"Node {node.id} is disabled",
                node_id=node.id,
            ))

        return contract

    async def _validate_edge(
        self,
        edge: EdgeSpec,
        spec: WorkflowSpec,
        node_contracts: Dict[str, ModuleContract],
        errors: List[ValidationIssue],
        warnings: List[ValidationIssue],
    ) -> EdgeDiagnostic:
        """Validate a single edge."""
        issues: List[ValidationIssue] = []
        is_valid = True

        diagnostic = EdgeDiagnostic(
            edge_id=edge.id or f"{edge.from_node}->{edge.to_node}",
            from_node=edge.from_node,
            from_port=edge.from_port,
            to_node=edge.to_node,
            to_port=edge.to_port,
            is_valid=True,
        )

        # Check source node exists
        from_node = spec.get_node(edge.from_node)
        if not from_node:
            issue = ValidationIssue(
                severity=IssueSeverity.ERROR,
                type=IssueType.DANGLING_EDGE,
                message=f"Source node '{edge.from_node}' not found",
                edge_id=edge.id,
            )
            issues.append(issue)
            errors.append(issue)
            is_valid = False

        # Check target node exists
        to_node = spec.get_node(edge.to_node)
        if not to_node:
            issue = ValidationIssue(
                severity=IssueSeverity.ERROR,
                type=IssueType.DANGLING_EDGE,
                message=f"Target node '{edge.to_node}' not found",
                edge_id=edge.id,
            )
            issues.append(issue)
            errors.append(issue)
            is_valid = False

        # Get contracts
        from_contract = node_contracts.get(edge.from_node)
        to_contract = node_contracts.get(edge.to_node)

        if from_contract and to_contract:
            # Check ports exist
            from_port = from_contract.get_port(edge.from_port)
            to_port = to_contract.get_port(edge.to_port)

            if not from_port:
                issue = ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    type=IssueType.PORT_NOT_FOUND,
                    message=f"Port '{edge.from_port}' not found on {edge.from_node}",
                    edge_id=edge.id,
                    node_id=edge.from_node,
                )
                issues.append(issue)
                errors.append(issue)
                is_valid = False
            else:
                diagnostic.from_type = from_port.data_type
                diagnostic.edge_type = from_port.edge_type.value

                # Check port direction
                if from_port.direction != PortDirection.OUTPUT:
                    issue = ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        type=IssueType.PORT_DIRECTION_INVALID,
                        message=f"Port '{edge.from_port}' is not an output port",
                        edge_id=edge.id,
                        node_id=edge.from_node,
                    )
                    issues.append(issue)
                    errors.append(issue)
                    is_valid = False

            if not to_port:
                issue = ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    type=IssueType.PORT_NOT_FOUND,
                    message=f"Port '{edge.to_port}' not found on {edge.to_node}",
                    edge_id=edge.id,
                    node_id=edge.to_node,
                )
                issues.append(issue)
                errors.append(issue)
                is_valid = False
            else:
                diagnostic.to_type = to_port.data_type

                # Check port direction
                if to_port.direction != PortDirection.INPUT:
                    issue = ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        type=IssueType.PORT_DIRECTION_INVALID,
                        message=f"Port '{edge.to_port}' is not an input port",
                        edge_id=edge.id,
                        node_id=edge.to_node,
                    )
                    issues.append(issue)
                    errors.append(issue)
                    is_valid = False

            # Check edge type compatibility
            if from_port and to_port:
                if from_port.edge_type != to_port.edge_type:
                    issue = ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        type=IssueType.EDGE_TYPE_MISMATCH,
                        message=(
                            f"Edge type mismatch: {from_port.edge_type.value} "
                            f"cannot connect to {to_port.edge_type.value}"
                        ),
                        edge_id=edge.id,
                    )
                    issues.append(issue)
                    errors.append(issue)
                    is_valid = False

                # Check data type compatibility
                elif from_port.edge_type == EdgeType.DATA:
                    if not from_port.is_compatible_type(to_port):
                        issue = ValidationIssue(
                            severity=IssueSeverity.WARNING,
                            type=IssueType.DATA_TYPE_MISMATCH,
                            message=(
                                f"Data type mismatch: {from_port.data_type} "
                                f"may not be compatible with {to_port.data_type}"
                            ),
                            edge_id=edge.id,
                        )
                        issues.append(issue)
                        warnings.append(issue)

            # Check connection policy
            can_connect, reason = from_contract.can_connect_to(
                to_contract, edge.from_port, edge.to_port
            )
            if not can_connect:
                issue = ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    type=IssueType.CONNECTION_POLICY_VIOLATION,
                    message=reason or "Connection not allowed by policy",
                    edge_id=edge.id,
                )
                issues.append(issue)
                errors.append(issue)
                is_valid = False

        diagnostic.is_valid = is_valid
        diagnostic.issues = issues

        return diagnostic

    def _validate_entry_nodes(
        self,
        spec: WorkflowSpec,
        errors: List[ValidationIssue],
        warnings: List[ValidationIssue],
    ) -> List[str]:
        """Validate and determine entry nodes."""
        # Find nodes with no incoming edges
        auto_entry = spec.find_entry_nodes()

        # Use specified entry nodes if provided
        if spec.entry_nodes:
            # Validate specified entry nodes exist
            for entry_id in spec.entry_nodes:
                if not spec.get_node(entry_id):
                    errors.append(ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        type=IssueType.NO_ENTRY_NODE,
                        message=f"Specified entry node '{entry_id}' not found",
                    ))
            return spec.entry_nodes

        # Use auto-detected entry nodes
        if not auto_entry:
            errors.append(ValidationIssue(
                severity=IssueSeverity.ERROR,
                type=IssueType.NO_ENTRY_NODE,
                message="No entry nodes found (all nodes have incoming edges)",
            ))
            return []

        if len(auto_entry) > 1:
            warnings.append(ValidationIssue(
                severity=IssueSeverity.WARNING,
                type=IssueType.CUSTOM,
                message=f"Multiple entry nodes detected: {auto_entry}",
            ))

        return auto_entry

    def _check_orphan_nodes(
        self,
        spec: WorkflowSpec,
        warnings: List[ValidationIssue],
    ) -> None:
        """Check for nodes that are not connected to anything."""
        connected_nodes: Set[str] = set()

        for edge in spec.edges:
            connected_nodes.add(edge.from_node)
            connected_nodes.add(edge.to_node)

        for node in spec.nodes:
            if node.id not in connected_nodes and not node.disabled:
                warnings.append(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    type=IssueType.ORPHAN_NODE,
                    message=f"Node '{node.id}' has no connections",
                    node_id=node.id,
                ))

    def _check_connection_limits(
        self,
        spec: WorkflowSpec,
        node_contracts: Dict[str, ModuleContract],
        errors: List[ValidationIssue],
    ) -> None:
        """Check that ports don't exceed max_connections."""
        # Count connections per port
        port_connections: Dict[str, int] = {}  # "node_id:port_id" -> count

        for edge in spec.edges:
            # Count output connections
            from_key = f"{edge.from_node}:{edge.from_port}"
            port_connections[from_key] = port_connections.get(from_key, 0) + 1

            # Count input connections
            to_key = f"{edge.to_node}:{edge.to_port}"
            port_connections[to_key] = port_connections.get(to_key, 0) + 1

        # Check against limits
        for key, count in port_connections.items():
            node_id, port_id = key.split(":", 1)
            contract = node_contracts.get(node_id)

            if contract:
                port = contract.get_port(port_id)
                if port and port.max_connections > 0 and count > port.max_connections:
                    errors.append(ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        type=IssueType.PORT_MAX_CONNECTIONS,
                        message=(
                            f"Port '{port_id}' on node '{node_id}' has {count} connections "
                            f"but only allows {port.max_connections}"
                        ),
                        node_id=node_id,
                    ))

    async def validate_edge(
        self,
        from_module_id: str,
        from_port_id: str,
        to_module_id: str,
        to_port_id: str,
    ) -> tuple[bool, Optional[str]]:
        """
        Validate a single edge connection.

        Convenience method for checking if a connection is valid
        without a full workflow context.

        Returns:
            Tuple of (is_valid, error_message)
        """
        from_contract = self.registry.get(from_module_id)
        to_contract = self.registry.get(to_module_id)

        if not from_contract:
            return False, f"Module not found: {from_module_id}"
        if not to_contract:
            return False, f"Module not found: {to_module_id}"

        return from_contract.can_connect_to(to_contract, from_port_id, to_port_id)
