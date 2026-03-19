"""
Binding Resolver

Resolves what variables are available to a node in a workflow.
This is how the UX knows what data sources to show in value selectors.

Binding Sources:
1. Upstream outputs - Data from previous steps
2. Loop scope - loop.item, loop.index (when inside a loop)
3. Branch scope - Variables from if/switch branches
4. UI inputs - Form field values
5. System vars - execution_id, workflow_id, env vars
6. Workflow variables - Global workflow-level vars

Example:
    resolver = BindingResolver(registry)
    tree = await resolver.get_available_bindings(workflow_spec, "node_3")

    # Returns something like:
    {
        "steps": {
            "node_1": {"url": "string", "title": "string"},
            "node_2": {"rows": "array<object>", "headers": "array<string>"},
        },
        "loop": {
            "item": {"url": "string", "name": "string"},
            "index": "number",
        },
        "ui": {
            "searchQuery": "string",
        },
        "system": {
            "execution_id": "string",
            "workflow_id": "string",
        },
    }
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from ..models.workflow_spec import WorkflowSpec, NodeSpec, EdgeSpec
from ..models.module_contract import ModuleContract
from ..models.port import Port, EdgeType
from ..models.data_contract import DataContract, DataType
from ..registry.contract_registry import ContractRegistry

logger = logging.getLogger(__name__)


class BindingSource(str, Enum):
    """Source of a binding."""

    STEP = "step"  # Output from a previous step
    LOOP = "loop"  # Loop scope variable
    BRANCH = "branch"  # Branch/switch scope variable
    ERROR = "error"  # Error scope from try-catch
    UI = "ui"  # UI form input
    SYSTEM = "system"  # System variables
    WORKFLOW = "workflow"  # Workflow-level variables
    PARAM = "param"  # Module parameter default


@dataclass
class BindingEntry:
    """A single binding available to a node."""

    path: str  # e.g., "steps.node_1.url" or "loop.item.name"
    data_type: str  # e.g., "string", "number", "array<object>"
    source: BindingSource
    source_id: Optional[str] = None  # e.g., node ID or scope name
    label: Optional[str] = None  # Human-readable label
    description: Optional[str] = None
    shape: Optional[str] = None  # For complex types

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "data_type": self.data_type,
            "source": self.source.value,
            "source_id": self.source_id,
            "label": self.label,
            "description": self.description,
            "shape": self.shape,
        }


@dataclass
class BindingTree:
    """
    Complete binding tree for a node.

    Organized by source for easy UI rendering.
    """

    steps: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    loop: Dict[str, Any] = field(default_factory=dict)
    branch: Dict[str, Any] = field(default_factory=dict)
    error: Dict[str, Any] = field(default_factory=dict)
    ui: Dict[str, Any] = field(default_factory=dict)
    system: Dict[str, Any] = field(default_factory=dict)
    workflow: Dict[str, Any] = field(default_factory=dict)

    # Flat list of all bindings for searching
    all_bindings: List[BindingEntry] = field(default_factory=list)

    def add_step_binding(
        self,
        node_id: str,
        field_name: str,
        data_type: str,
        label: Optional[str] = None,
        shape: Optional[str] = None,
    ) -> None:
        """Add a binding from a step's output."""
        if node_id not in self.steps:
            self.steps[node_id] = {}

        self.steps[node_id][field_name] = {
            "type": data_type,
            "shape": shape,
        }

        self.all_bindings.append(BindingEntry(
            path=f"steps.{node_id}.{field_name}",
            data_type=data_type,
            source=BindingSource.STEP,
            source_id=node_id,
            label=label or field_name,
            shape=shape,
        ))

    def add_loop_binding(
        self,
        var_name: str,
        data_type: str,
        shape: Optional[str] = None,
    ) -> None:
        """Add a loop scope binding."""
        self.loop[var_name] = {
            "type": data_type,
            "shape": shape,
        }

        self.all_bindings.append(BindingEntry(
            path=f"loop.{var_name}",
            data_type=data_type,
            source=BindingSource.LOOP,
            label=var_name,
            shape=shape,
        ))

    def add_system_binding(
        self,
        var_name: str,
        data_type: str,
        description: Optional[str] = None,
    ) -> None:
        """Add a system variable binding."""
        self.system[var_name] = {
            "type": data_type,
            "description": description,
        }

        self.all_bindings.append(BindingEntry(
            path=f"system.{var_name}",
            data_type=data_type,
            source=BindingSource.SYSTEM,
            label=var_name,
            description=description,
        ))

    def search(self, query: str) -> List[BindingEntry]:
        """Search bindings by path or label."""
        query_lower = query.lower()
        results = []

        for binding in self.all_bindings:
            if (
                query_lower in binding.path.lower()
                or (binding.label and query_lower in binding.label.lower())
            ):
                results.append(binding)

        return results

    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps": self.steps,
            "loop": self.loop,
            "branch": self.branch,
            "error": self.error,
            "ui": self.ui,
            "system": self.system,
            "workflow": self.workflow,
        }


class BindingResolver:
    """
    Resolves available bindings for workflow nodes.

    This is the AUTHORITATIVE source for what data is available
    to a node. Cloud's value selector should display exactly
    what this resolver returns.
    """

    # System variables always available
    SYSTEM_VARS = {
        "execution_id": ("string", "Unique execution identifier"),
        "workflow_id": ("string", "Workflow identifier"),
        "workflow_name": ("string", "Workflow name"),
        "timestamp": ("string", "Current ISO timestamp"),
        "iteration": ("number", "Current iteration (for retries)"),
    }

    def __init__(self, registry: Optional[ContractRegistry] = None):
        self.registry = registry or ContractRegistry.instance()

    async def get_available_bindings(
        self,
        spec: WorkflowSpec,
        node_id: str,
    ) -> BindingTree:
        """
        Get all available bindings for a node.

        Args:
            spec: The workflow specification
            node_id: The node to get bindings for

        Returns:
            BindingTree with all available bindings
        """
        tree = BindingTree()

        # Get the target node
        target_node = spec.get_node(node_id)
        if not target_node:
            return tree

        # 1. Add upstream step outputs
        await self._add_upstream_bindings(spec, node_id, tree)

        # 2. Add scope bindings (loop, branch, error)
        await self._add_scope_bindings(spec, node_id, tree)

        # 3. Add UI bindings
        self._add_ui_bindings(spec, tree)

        # 4. Add system bindings
        self._add_system_bindings(tree)

        # 5. Add workflow variables
        self._add_workflow_bindings(spec, tree)

        return tree

    async def _add_upstream_bindings(
        self,
        spec: WorkflowSpec,
        node_id: str,
        tree: BindingTree,
    ) -> None:
        """Add bindings from upstream nodes."""
        # Get all upstream nodes (transitively)
        upstream = self._get_all_upstream(spec, node_id)

        for upstream_id in upstream:
            upstream_node = spec.get_node(upstream_id)
            if not upstream_node:
                continue

            contract = self.registry.get(upstream_node.module_id)
            if not contract:
                continue

            # Get output schema
            if contract.output_schema:
                self._add_output_schema_bindings(
                    upstream_id, contract.output_schema, tree
                )
            else:
                # Try to infer from output ports
                for port in contract.get_output_ports():
                    if port.edge_type == EdgeType.DATA:
                        tree.add_step_binding(
                            upstream_id,
                            "result",
                            port.data_type,
                            label=contract.label,
                            shape=port.shape,
                        )

    def _add_output_schema_bindings(
        self,
        node_id: str,
        schema: DataContract,
        tree: BindingTree,
    ) -> None:
        """Add bindings from an output schema."""
        if schema.data_type == DataType.OBJECT and schema.shape:
            # Parse shape to extract fields
            # Shape format: "object{field1:type1, field2:type2}"
            fields = self._parse_object_shape(schema.shape)
            for field_name, field_type in fields.items():
                tree.add_step_binding(node_id, field_name, field_type)
        else:
            # Single value output
            tree.add_step_binding(
                node_id,
                "result",
                schema.data_type.value,
                shape=schema.shape,
            )

    def _parse_object_shape(self, shape: str) -> Dict[str, str]:
        """Parse object shape string to extract fields."""
        # Format: "object{field1:type1, field2:type2}"
        fields = {}

        if not shape.startswith("object{") or not shape.endswith("}"):
            return fields

        content = shape[7:-1]  # Remove "object{" and "}"

        # Simple parsing - doesn't handle nested objects well
        parts = content.split(",")
        for part in parts:
            if ":" in part:
                field_name, field_type = part.strip().split(":", 1)
                fields[field_name.strip()] = field_type.strip()

        return fields

    async def _add_scope_bindings(
        self,
        spec: WorkflowSpec,
        node_id: str,
        tree: BindingTree,
    ) -> None:
        """Add scope bindings from control flow nodes."""
        # Find control flow nodes that scope this node
        scope_nodes = self._find_scope_providers(spec, node_id)

        for scope_node_id, scope_type in scope_nodes:
            scope_node = spec.get_node(scope_node_id)
            if not scope_node:
                continue

            contract = self.registry.get(scope_node.module_id)
            if not contract:
                continue

            # Find the port that provides scope
            for port in contract.ports:
                if port.scope_provides:
                    for var_name in port.scope_provides:
                        # Determine type from port or default to any
                        var_type = "any"
                        if var_name.endswith(".index"):
                            var_type = "number"
                        elif var_name.endswith(".item"):
                            # Try to get item type from input
                            input_port = contract.get_port("in")
                            if input_port and input_port.data_type == "array":
                                var_type = "any"  # Item type from array

                        if scope_type == "loop":
                            tree.add_loop_binding(var_name.split(".")[-1], var_type)
                        elif scope_type == "error":
                            tree.error[var_name.split(".")[-1]] = {"type": var_type}
                        elif scope_type == "branch":
                            tree.branch[var_name.split(".")[-1]] = {"type": var_type}

    def _find_scope_providers(
        self,
        spec: WorkflowSpec,
        node_id: str,
    ) -> List[tuple[str, str]]:
        """
        Find nodes that provide scope to this node.

        Returns list of (node_id, scope_type) tuples.
        """
        providers = []

        # Walk backwards through control flow edges
        visited: Set[str] = set()
        queue = [node_id]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            # Find incoming edges
            for edge in spec.edges:
                if edge.to_node == current:
                    from_node = spec.get_node(edge.from_node)
                    if not from_node:
                        continue

                    contract = self.registry.get(from_node.module_id)
                    if not contract:
                        queue.append(edge.from_node)
                        continue

                    # Check if this port provides scope
                    port = contract.get_port(edge.from_port)
                    if port and port.scope_provides:
                        # Determine scope type from port or module
                        if "loop" in from_node.module_id:
                            scope_type = "loop"
                        elif "try" in from_node.module_id or "catch" in edge.from_port:
                            scope_type = "error"
                        else:
                            scope_type = "branch"

                        providers.append((edge.from_node, scope_type))

                    queue.append(edge.from_node)

        return providers

    def _get_all_upstream(
        self,
        spec: WorkflowSpec,
        node_id: str,
    ) -> List[str]:
        """Get all upstream nodes (transitively)."""
        upstream: List[str] = []
        visited: Set[str] = set()
        queue = list(spec.get_upstream_nodes(node_id))

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            upstream.append(current)

            # Add this node's upstream
            queue.extend(spec.get_upstream_nodes(current))

        return upstream

    def _add_ui_bindings(self, spec: WorkflowSpec, tree: BindingTree) -> None:
        """Add UI form input bindings."""
        # UI inputs are defined in workflow metadata
        ui_inputs = spec.metadata.get("ui_inputs", {})

        for input_name, input_def in ui_inputs.items():
            if isinstance(input_def, dict):
                data_type = input_def.get("type", "string")
                description = input_def.get("description")
            else:
                data_type = "string"
                description = None

            tree.ui[input_name] = {"type": data_type}

            tree.all_bindings.append(BindingEntry(
                path=f"ui.{input_name}",
                data_type=data_type,
                source=BindingSource.UI,
                label=input_name,
                description=description,
            ))

    def _add_system_bindings(self, tree: BindingTree) -> None:
        """Add system variable bindings."""
        for var_name, (data_type, description) in self.SYSTEM_VARS.items():
            tree.add_system_binding(var_name, data_type, description)

    def _add_workflow_bindings(
        self,
        spec: WorkflowSpec,
        tree: BindingTree,
    ) -> None:
        """Add workflow-level variable bindings."""
        for var_name, var_value in spec.variables.items():
            # Infer type from value
            if isinstance(var_value, bool):
                data_type = "boolean"
            elif isinstance(var_value, int) or isinstance(var_value, float):
                data_type = "number"
            elif isinstance(var_value, list):
                data_type = "array"
            elif isinstance(var_value, dict):
                data_type = "object"
            else:
                data_type = "string"

            tree.workflow[var_name] = {"type": data_type, "value": var_value}

            tree.all_bindings.append(BindingEntry(
                path=f"workflow.{var_name}",
                data_type=data_type,
                source=BindingSource.WORKFLOW,
                label=var_name,
            ))

    async def resolve_expression(
        self,
        expression: str,
        bindings: BindingTree,
        runtime_values: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Resolve an expression to its value.

        Expression format: ${path.to.value}

        This is used at runtime to get actual values.
        """
        if not expression.startswith("${") or not expression.endswith("}"):
            return expression

        path = expression[2:-1]  # Remove ${ and }
        parts = path.split(".")

        if not parts:
            return None

        # Get the value from runtime_values if available
        if runtime_values:
            try:
                value = runtime_values
                for part in parts:
                    if isinstance(value, dict):
                        value = value.get(part)
                    elif hasattr(value, part):
                        value = getattr(value, part)
                    else:
                        return None
                return value
            except (KeyError, AttributeError):
                pass

        return None

    def generate_expression(self, binding: BindingEntry) -> str:
        """
        Generate an expression string for a binding.

        This is what gets stored in node params.
        """
        return f"${{{binding.path}}}"
