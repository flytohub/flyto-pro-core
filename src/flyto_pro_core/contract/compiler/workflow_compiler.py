"""
Workflow Compiler

Compiles workflow specifications into executable plans.
The ExecutablePlan contains everything needed to run the workflow:
- Resolved port bindings
- Pre-computed routing rules
- Validated type information
- Scope injection points

Usage:
    compiler = WorkflowCompiler(registry)
    plan = await compiler.compile(workflow_spec)

    # Plan can be cached (hash the spec)
    cache_key = plan.spec_hash

    # Execute the plan
    for step in plan.execution_order:
        node = plan.nodes[step]
        # ... execute node ...
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from datetime import datetime

from ..models.workflow_spec import WorkflowSpec, NodeSpec, EdgeSpec
from ..models.module_contract import ModuleContract
from ..models.port import Port, PortDirection, EdgeType
from ..models.execution_result import ExecutionEvent
from ..registry.contract_registry import ContractRegistry
from ..validator.workflow_validator import WorkflowValidator, ValidationReport
from ..binder.binding_resolver import BindingResolver, BindingTree

logger = logging.getLogger(__name__)


@dataclass
class PortBinding:
    """Resolved binding for a port."""

    port_id: str
    direction: str  # "input" or "output"
    edge_type: str  # "data" or "control"
    data_type: str
    connected_to: List[str] = field(default_factory=list)  # "node_id:port_id"
    scope_provides: List[str] = field(default_factory=list)
    scope_requires: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "port_id": self.port_id,
            "direction": self.direction,
            "edge_type": self.edge_type,
            "data_type": self.data_type,
            "connected_to": self.connected_to,
            "scope_provides": self.scope_provides,
            "scope_requires": self.scope_requires,
        }


@dataclass
class RoutingRule:
    """Rule for routing to next node based on event."""

    event: str  # Event that triggers this route
    target_node: str  # Node to route to
    target_port: str  # Port on target node
    scope_inject: List[str] = field(default_factory=list)  # Scope vars to inject

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event": self.event,
            "target_node": self.target_node,
            "target_port": self.target_port,
            "scope_inject": self.scope_inject,
        }


@dataclass
class CompiledNode:
    """A compiled node ready for execution."""

    id: str
    module_id: str
    module_version: str
    label: str
    params: Dict[str, Any]
    ports: List[PortBinding] = field(default_factory=list)
    routing_rules: List[RoutingRule] = field(default_factory=list)
    bindings: Optional[Dict[str, Any]] = None  # Available bindings tree
    depends_on: List[str] = field(default_factory=list)  # Node IDs this depends on
    is_entry: bool = False
    is_control_flow: bool = False
    disabled: bool = False

    def get_default_route(self) -> Optional[RoutingRule]:
        """Get the default routing rule (for non-event cases)."""
        for rule in self.routing_rules:
            if rule.event in ("next", "out", "done"):
                return rule
        return self.routing_rules[0] if self.routing_rules else None

    def get_route_for_event(self, event: str) -> Optional[RoutingRule]:
        """Get routing rule for a specific event."""
        for rule in self.routing_rules:
            if rule.event == event:
                return rule
            # Handle case:* pattern
            if rule.event.startswith("case:") and event.startswith("case:"):
                if rule.event == "case:*" or rule.event == event:
                    return rule
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "module_id": self.module_id,
            "module_version": self.module_version,
            "label": self.label,
            "params": self.params,
            "ports": [p.to_dict() for p in self.ports],
            "routing_rules": [r.to_dict() for r in self.routing_rules],
            "bindings": self.bindings,
            "depends_on": self.depends_on,
            "is_entry": self.is_entry,
            "is_control_flow": self.is_control_flow,
            "disabled": self.disabled,
        }


@dataclass
class ExecutablePlan:
    """
    Compiled executable plan for a workflow.

    This is the output of compilation - everything needed to execute.
    Can be cached and reused for the same workflow spec.
    """

    workflow_id: str
    workflow_name: str
    workflow_version: str
    spec_hash: str  # Hash of the spec for caching
    nodes: Dict[str, CompiledNode] = field(default_factory=dict)
    execution_order: List[str] = field(default_factory=list)
    entry_nodes: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    compiled_at: Optional[str] = None
    validation_report: Optional[Dict[str, Any]] = None

    def get_node(self, node_id: str) -> Optional[CompiledNode]:
        """Get a compiled node by ID."""
        return self.nodes.get(node_id)

    def get_entry_nodes(self) -> List[CompiledNode]:
        """Get all entry nodes."""
        return [self.nodes[n] for n in self.entry_nodes if n in self.nodes]

    def get_next_nodes(self, node_id: str, event: Optional[str] = None) -> List[str]:
        """Get IDs of nodes to execute next based on event."""
        node = self.get_node(node_id)
        if not node:
            return []

        if event:
            rule = node.get_route_for_event(event)
            if rule:
                return [rule.target_node]
        else:
            # Return all non-control-flow routes
            return [
                r.target_node for r in node.routing_rules
                if r.event in ("next", "out", "done")
            ]

        return []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "workflow_version": self.workflow_version,
            "spec_hash": self.spec_hash,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "execution_order": self.execution_order,
            "entry_nodes": self.entry_nodes,
            "variables": self.variables,
            "compiled_at": self.compiled_at,
            "validation_report": self.validation_report,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExecutablePlan:
        """Restore from dictionary (e.g., from cache)."""
        nodes = {}
        for node_id, node_data in data.get("nodes", {}).items():
            nodes[node_id] = CompiledNode(
                id=node_data["id"],
                module_id=node_data["module_id"],
                module_version=node_data["module_version"],
                label=node_data["label"],
                params=node_data["params"],
                ports=[PortBinding(**p) for p in node_data.get("ports", [])],
                routing_rules=[RoutingRule(**r) for r in node_data.get("routing_rules", [])],
                bindings=node_data.get("bindings"),
                depends_on=node_data.get("depends_on", []),
                is_entry=node_data.get("is_entry", False),
                is_control_flow=node_data.get("is_control_flow", False),
                disabled=node_data.get("disabled", False),
            )

        return cls(
            workflow_id=data["workflow_id"],
            workflow_name=data["workflow_name"],
            workflow_version=data["workflow_version"],
            spec_hash=data["spec_hash"],
            nodes=nodes,
            execution_order=data.get("execution_order", []),
            entry_nodes=data.get("entry_nodes", []),
            variables=data.get("variables", {}),
            compiled_at=data.get("compiled_at"),
            validation_report=data.get("validation_report"),
        )


class CompilationError(Exception):
    """Error during workflow compilation."""

    def __init__(self, message: str, validation_report: Optional[ValidationReport] = None):
        super().__init__(message)
        self.validation_report = validation_report


class WorkflowCompiler:
    """
    Compiles workflow specifications into executable plans.

    The compiler:
    1. Validates the workflow
    2. Resolves all port bindings
    3. Computes routing rules
    4. Resolves variable bindings
    5. Produces a cacheable ExecutablePlan
    """

    def __init__(self, registry: Optional[ContractRegistry] = None):
        self.registry = registry or ContractRegistry.instance()
        self.validator = WorkflowValidator(self.registry)
        self.binder = BindingResolver(self.registry)

    async def compile(
        self,
        spec: WorkflowSpec,
        skip_validation: bool = False,
    ) -> ExecutablePlan:
        """
        Compile a workflow specification into an executable plan.

        Args:
            spec: The workflow specification to compile
            skip_validation: Skip validation (only for trusted/cached specs)

        Returns:
            ExecutablePlan ready for execution

        Raises:
            CompilationError: If workflow is invalid
        """
        # 1. Validate the workflow
        validation_report = None
        if not skip_validation:
            validation_report = await self.validator.validate(spec)
            if not validation_report.is_valid:
                raise CompilationError(
                    f"Workflow validation failed with {len(validation_report.errors)} errors",
                    validation_report,
                )

        # 2. Compute spec hash for caching
        spec_hash = self._compute_spec_hash(spec)

        # 3. Compile each node
        compiled_nodes: Dict[str, CompiledNode] = {}

        for node in spec.nodes:
            compiled = await self._compile_node(node, spec)
            compiled_nodes[node.id] = compiled

        # 4. Compute execution order
        try:
            execution_order = spec.topological_sort()
        except ValueError:
            execution_order = [n.id for n in spec.nodes]

        # 5. Determine entry nodes
        entry_nodes = validation_report.entry_nodes if validation_report else spec.find_entry_nodes()
        for entry_id in entry_nodes:
            if entry_id in compiled_nodes:
                compiled_nodes[entry_id].is_entry = True

        # 6. Build the plan
        plan = ExecutablePlan(
            workflow_id=spec.id,
            workflow_name=spec.name,
            workflow_version=spec.version,
            spec_hash=spec_hash,
            nodes=compiled_nodes,
            execution_order=execution_order,
            entry_nodes=entry_nodes,
            variables=spec.variables,
            compiled_at=datetime.utcnow().isoformat(),
            validation_report=validation_report.to_dict() if validation_report else None,
        )

        logger.info(f"Compiled workflow {spec.id} with {len(compiled_nodes)} nodes")

        return plan

    async def _compile_node(
        self,
        node: NodeSpec,
        spec: WorkflowSpec,
    ) -> CompiledNode:
        """Compile a single node."""
        contract = self.registry.get(node.module_id)

        # Get module info
        module_version = contract.version if contract else "1.0.0"
        label = node.label or (contract.label if contract else node.module_id)
        is_control_flow = contract.category == "flow" if contract else False

        # Compile ports
        ports: List[PortBinding] = []
        if contract:
            for port in contract.ports:
                binding = PortBinding(
                    port_id=port.id,
                    direction=port.direction.value,
                    edge_type=port.edge_type.value,
                    data_type=port.data_type,
                    connected_to=self._get_connected_nodes(spec, node.id, port.id, port.direction),
                    scope_provides=port.scope_provides,
                    scope_requires=port.scope_requires,
                )
                ports.append(binding)

        # Compute routing rules
        routing_rules = self._compute_routing_rules(node, spec, contract)

        # Resolve bindings
        bindings = await self.binder.get_available_bindings(spec, node.id)

        # Get dependencies
        depends_on = spec.get_upstream_nodes(node.id)

        return CompiledNode(
            id=node.id,
            module_id=node.module_id,
            module_version=module_version,
            label=label,
            params=node.params,
            ports=ports,
            routing_rules=routing_rules,
            bindings=bindings.to_dict(),
            depends_on=depends_on,
            is_entry=False,  # Set later
            is_control_flow=is_control_flow,
            disabled=node.disabled,
        )

    def _get_connected_nodes(
        self,
        spec: WorkflowSpec,
        node_id: str,
        port_id: str,
        direction: PortDirection,
    ) -> List[str]:
        """Get list of node:port that connect to/from this port."""
        connections = []

        for edge in spec.edges:
            if direction == PortDirection.OUTPUT:
                if edge.from_node == node_id and edge.from_port == port_id:
                    connections.append(f"{edge.to_node}:{edge.to_port}")
            else:
                if edge.to_node == node_id and edge.to_port == port_id:
                    connections.append(f"{edge.from_node}:{edge.from_port}")

        return connections

    def _compute_routing_rules(
        self,
        node: NodeSpec,
        spec: WorkflowSpec,
        contract: Optional[ModuleContract],
    ) -> List[RoutingRule]:
        """Compute routing rules for a node based on its output edges."""
        rules: List[RoutingRule] = []

        # Get all output edges from this node
        output_edges = spec.get_node_outputs(node.id)

        for edge in output_edges:
            # Determine the event for this route
            event = self._port_to_event(edge.from_port, contract)

            # Get scope injection if any
            scope_inject = []
            if contract:
                port = contract.get_port(edge.from_port)
                if port:
                    scope_inject = port.scope_provides

            rules.append(RoutingRule(
                event=event,
                target_node=edge.to_node,
                target_port=edge.to_port,
                scope_inject=scope_inject,
            ))

        return rules

    def _port_to_event(self, port_id: str, contract: Optional[ModuleContract]) -> str:
        """Map port ID to routing event."""
        # Standard mappings
        port_event_map = {
            "out": "next",
            "next": "next",
            "body": ExecutionEvent.ITERATE.value,
            "done": ExecutionEvent.DONE.value,
            "true": ExecutionEvent.TRUE.value,
            "false": ExecutionEvent.FALSE.value,
            "default": ExecutionEvent.DEFAULT.value,
            "catch": ExecutionEvent.ERROR.value,
            "finally": "finally",
        }

        if port_id in port_event_map:
            return port_event_map[port_id]

        # Handle case:* ports
        if port_id.startswith("case:"):
            return port_id

        # Default to port ID as event
        return port_id

    def _compute_spec_hash(self, spec: WorkflowSpec) -> str:
        """Compute a hash of the workflow spec for caching."""
        # Create a deterministic representation
        spec_dict = spec.to_dict()

        # Remove non-deterministic fields
        spec_dict.pop("created_at", None)
        spec_dict.pop("updated_at", None)

        # Sort for determinism
        spec_json = json.dumps(spec_dict, sort_keys=True)

        return hashlib.sha256(spec_json.encode()).hexdigest()[:16]

    async def recompile_if_changed(
        self,
        spec: WorkflowSpec,
        cached_plan: ExecutablePlan,
    ) -> tuple[ExecutablePlan, bool]:
        """
        Recompile only if spec has changed.

        Args:
            spec: Current workflow specification
            cached_plan: Previously compiled plan

        Returns:
            Tuple of (plan, was_recompiled)
        """
        current_hash = self._compute_spec_hash(spec)

        if current_hash == cached_plan.spec_hash:
            return cached_plan, False

        new_plan = await self.compile(spec)
        return new_plan, True
