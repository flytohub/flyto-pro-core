"""
Workflow Specification Models

Defines the structure of a workflow as a graph of nodes and edges.
This is the format that Cloud sends to Core for validation and execution.

Example:
    spec = WorkflowSpec(
        id="my-workflow",
        name="Scrape Products",
        version="1.0.0",
        nodes=[
            NodeSpec(id="n1", module_id="browser.goto", params={"url": "..."}),
            NodeSpec(id="n2", module_id="browser.click", params={"selector": "..."}),
        ],
        edges=[
            EdgeSpec(from_node="n1", from_port="out", to_node="n2", to_port="in"),
        ],
        entry_nodes=["n1"],
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class NodeSpec:
    """
    Specification for a single node in the workflow.

    Attributes:
        id: Unique node identifier within the workflow
        module_id: The module to execute (e.g., "browser.goto")
        params: Parameter values for the module
        label: Optional display label (defaults to module label)
        position: UI position {x, y}
        disabled: Whether node is disabled
        comment: Developer comment/note
        version_required: Minimum module version required
    """

    id: str
    module_id: str
    params: Dict[str, Any] = field(default_factory=dict)
    label: Optional[str] = None
    position: Dict[str, float] = field(default_factory=dict)
    disabled: bool = False
    comment: Optional[str] = None
    version_required: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "module_id": self.module_id,
            "params": self.params,
            "label": self.label,
            "position": self.position,
            "disabled": self.disabled,
            "comment": self.comment,
            "version_required": self.version_required,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> NodeSpec:
        return cls(
            id=data["id"],
            module_id=data["module_id"],
            params=data.get("params", {}),
            label=data.get("label"),
            position=data.get("position", {}),
            disabled=data.get("disabled", False),
            comment=data.get("comment"),
            version_required=data.get("version_required"),
        )


@dataclass
class EdgeSpec:
    """
    Specification for an edge (connection) between nodes.

    Attributes:
        id: Optional edge identifier
        from_node: Source node ID
        from_port: Source port ID (default: "out")
        to_node: Target node ID
        to_port: Target port ID (default: "in")
        label: Optional edge label
        condition: Optional condition for conditional edges
    """

    from_node: str
    to_node: str
    from_port: str = "out"
    to_port: str = "in"
    id: Optional[str] = None
    label: Optional[str] = None
    condition: Optional[str] = None

    def __post_init__(self):
        if not self.id:
            self.id = f"{self.from_node}:{self.from_port}->{self.to_node}:{self.to_port}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from_node": self.from_node,
            "from_port": self.from_port,
            "to_node": self.to_node,
            "to_port": self.to_port,
            "label": self.label,
            "condition": self.condition,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EdgeSpec:
        return cls(
            from_node=data["from_node"],
            to_node=data["to_node"],
            from_port=data.get("from_port", "out"),
            to_port=data.get("to_port", "in"),
            id=data.get("id"),
            label=data.get("label"),
            condition=data.get("condition"),
        )


@dataclass
class WorkflowSpec:
    """
    Complete workflow specification.

    Attributes:
        id: Unique workflow identifier
        name: Human-readable name
        description: Workflow description
        version: Workflow version
        nodes: List of node specifications
        edges: List of edge specifications
        entry_nodes: Node IDs that can be entry points
        variables: Workflow-level variables
        metadata: Additional metadata
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: str
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    nodes: List[NodeSpec] = field(default_factory=list)
    edges: List[EdgeSpec] = field(default_factory=list)
    entry_nodes: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def get_node(self, node_id: str) -> Optional[NodeSpec]:
        """Get a node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_node_inputs(self, node_id: str) -> List[EdgeSpec]:
        """Get all edges going into a node."""
        return [e for e in self.edges if e.to_node == node_id]

    def get_node_outputs(self, node_id: str) -> List[EdgeSpec]:
        """Get all edges going out of a node."""
        return [e for e in self.edges if e.from_node == node_id]

    def get_upstream_nodes(self, node_id: str) -> List[str]:
        """Get IDs of all nodes that connect to this node."""
        return [e.from_node for e in self.get_node_inputs(node_id)]

    def get_downstream_nodes(self, node_id: str) -> List[str]:
        """Get IDs of all nodes this node connects to."""
        return [e.to_node for e in self.get_node_outputs(node_id)]

    def get_enabled_nodes(self) -> List[NodeSpec]:
        """Get all non-disabled nodes."""
        return [n for n in self.nodes if not n.disabled]

    def topological_sort(self) -> List[str]:
        """
        Return node IDs in topological order (execution order).

        Returns:
            List of node IDs sorted by dependency order

        Raises:
            ValueError: If workflow contains cycles
        """
        # Build adjacency list
        graph: Dict[str, List[str]] = {n.id: [] for n in self.nodes}
        in_degree: Dict[str, int] = {n.id: 0 for n in self.nodes}

        for edge in self.edges:
            if edge.from_node in graph and edge.to_node in graph:
                graph[edge.from_node].append(edge.to_node)
                in_degree[edge.to_node] += 1

        # Kahn's algorithm
        queue = [n for n, d in in_degree.items() if d == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self.nodes):
            raise ValueError("Workflow contains cycles")

        return result

    def find_entry_nodes(self) -> List[str]:
        """Find nodes with no incoming edges (potential entry points)."""
        nodes_with_inputs = {e.to_node for e in self.edges}
        return [n.id for n in self.nodes if n.id not in nodes_with_inputs]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "entry_nodes": self.entry_nodes,
            "variables": self.variables,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkflowSpec:
        nodes = [NodeSpec.from_dict(n) for n in data.get("nodes", [])]
        edges = [EdgeSpec.from_dict(e) for e in data.get("edges", [])]

        return cls(
            id=data["id"],
            name=data.get("name", ""),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            nodes=nodes,
            edges=edges,
            entry_nodes=data.get("entry_nodes", []),
            variables=data.get("variables", {}),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    @classmethod
    def from_yaml(cls, yaml_str: str) -> WorkflowSpec:
        """Parse from YAML string (flyto format)."""
        import yaml

        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)
