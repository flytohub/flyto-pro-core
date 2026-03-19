"""
Port Definitions

Ports define connection points on modules for visual workflow building.
Each module declares its input_ports and output_ports.

Example:
    # Simple module with one input, one output
    ports = [
        Port(id="in", direction=PortDirection.INPUT, edge_type=EdgeType.DATA),
        Port(id="out", direction=PortDirection.OUTPUT, edge_type=EdgeType.DATA),
    ]

    # Loop module with control flow ports
    ports = [
        Port(id="in", direction=PortDirection.INPUT, edge_type=EdgeType.DATA),
        Port(id="body", direction=PortDirection.OUTPUT, edge_type=EdgeType.CONTROL,
             scope_provides=["loop.item", "loop.index"]),
        Port(id="done", direction=PortDirection.OUTPUT, edge_type=EdgeType.CONTROL),
    ]

    # Switch module with dynamic ports
    ports = [
        Port(id="in", direction=PortDirection.INPUT, edge_type=EdgeType.DATA),
        Port(id="case:*", direction=PortDirection.OUTPUT, edge_type=EdgeType.CONTROL,
             dynamic=True),
        Port(id="default", direction=PortDirection.OUTPUT, edge_type=EdgeType.CONTROL),
    ]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PortDirection(str, Enum):
    """Direction of a port."""

    INPUT = "input"
    OUTPUT = "output"


class EdgeType(str, Enum):
    """Type of edge/connection.

    DATA: Passes data between modules
    CONTROL: Controls execution flow (if/else, loop, switch)
    """

    DATA = "data"
    CONTROL = "control"


@dataclass
class Port:
    """
    A connection point on a module.

    Attributes:
        id: Unique port identifier within the module (e.g., "in", "out", "body")
        direction: INPUT or OUTPUT
        edge_type: DATA or CONTROL
        data_type: Type of data this port handles (see DataType)
        shape: Optional shape descriptor for complex types
        label: Human-readable label for UI
        description: Detailed description
        required: Whether connection is required (for inputs)
        max_connections: Maximum connections allowed (default 1 for input, unlimited for output)
        dynamic: Whether this port can spawn dynamic instances (e.g., "case:*")
        scope_provides: Variables this port provides to its scope (e.g., loop.item)
        scope_requires: Variables this port requires from parent scope
        accepts_from: List of module categories/IDs this port accepts connections from
        rejects_from: List of module categories/IDs this port rejects connections from
    """

    id: str
    direction: PortDirection
    edge_type: EdgeType = EdgeType.DATA
    data_type: str = "any"
    shape: Optional[str] = None
    label: Optional[str] = None
    description: Optional[str] = None
    required: bool = False
    max_connections: int = -1  # -1 = unlimited
    dynamic: bool = False
    scope_provides: List[str] = field(default_factory=list)
    scope_requires: List[str] = field(default_factory=list)
    accepts_from: List[str] = field(default_factory=list)
    rejects_from: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Set defaults based on direction."""
        if self.max_connections == -1:
            # Input ports default to 1 connection, output unlimited
            self.max_connections = 1 if self.direction == PortDirection.INPUT else 999

        if not self.label:
            self.label = self.id.replace("_", " ").title()

    def can_connect_to(self, other: Port) -> bool:
        """Check if this port can connect to another port."""
        # Must be opposite directions
        if self.direction == other.direction:
            return False

        # Edge types must match
        if self.edge_type != other.edge_type:
            return False

        return True

    def is_compatible_type(self, other: Port) -> bool:
        """Check if data types are compatible."""
        # 'any' is compatible with everything
        if self.data_type == "any" or other.data_type == "any":
            return True

        # Exact match
        if self.data_type == other.data_type:
            return True

        # Allow string to be passed where number is expected (with coercion)
        compatible_pairs = [
            ("string", "number"),
            ("number", "string"),
            ("array", "object"),
        ]

        return (self.data_type, other.data_type) in compatible_pairs

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "direction": self.direction.value,
            "edge_type": self.edge_type.value,
            "data_type": self.data_type,
            "shape": self.shape,
            "label": self.label,
            "description": self.description,
            "required": self.required,
            "max_connections": self.max_connections,
            "dynamic": self.dynamic,
            "scope_provides": self.scope_provides,
            "scope_requires": self.scope_requires,
            "accepts_from": self.accepts_from,
            "rejects_from": self.rejects_from,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Port:
        """Create Port from dictionary."""
        return cls(
            id=data["id"],
            direction=PortDirection(data["direction"]),
            edge_type=EdgeType(data.get("edge_type", "data")),
            data_type=data.get("data_type", "any"),
            shape=data.get("shape"),
            label=data.get("label"),
            description=data.get("description"),
            required=data.get("required", False),
            max_connections=data.get("max_connections", -1),
            dynamic=data.get("dynamic", False),
            scope_provides=data.get("scope_provides", []),
            scope_requires=data.get("scope_requires", []),
            accepts_from=data.get("accepts_from", []),
            rejects_from=data.get("rejects_from", []),
        )


# Common port templates for convenience
class PortTemplates:
    """Pre-defined port templates for common patterns."""

    @staticmethod
    def data_input(
        id: str = "in",
        data_type: str = "any",
        required: bool = True,
        label: Optional[str] = None,
    ) -> Port:
        """Standard data input port."""
        return Port(
            id=id,
            direction=PortDirection.INPUT,
            edge_type=EdgeType.DATA,
            data_type=data_type,
            required=required,
            label=label,
        )

    @staticmethod
    def data_output(
        id: str = "out",
        data_type: str = "any",
        label: Optional[str] = None,
    ) -> Port:
        """Standard data output port."""
        return Port(
            id=id,
            direction=PortDirection.OUTPUT,
            edge_type=EdgeType.DATA,
            data_type=data_type,
            label=label,
        )

    @staticmethod
    def control_input(
        id: str = "trigger",
        label: Optional[str] = None,
    ) -> Port:
        """Control flow input port."""
        return Port(
            id=id,
            direction=PortDirection.INPUT,
            edge_type=EdgeType.CONTROL,
            label=label,
        )

    @staticmethod
    def control_output(
        id: str = "next",
        label: Optional[str] = None,
    ) -> Port:
        """Control flow output port."""
        return Port(
            id=id,
            direction=PortDirection.OUTPUT,
            edge_type=EdgeType.CONTROL,
            label=label,
        )

    @staticmethod
    def loop_body(
        item_type: str = "any",
        provides: Optional[List[str]] = None,
    ) -> Port:
        """Loop body port that provides item scope."""
        return Port(
            id="body",
            direction=PortDirection.OUTPUT,
            edge_type=EdgeType.CONTROL,
            label="Loop Body",
            scope_provides=provides or ["loop.item", "loop.index"],
        )

    @staticmethod
    def loop_done() -> Port:
        """Loop completion port."""
        return Port(
            id="done",
            direction=PortDirection.OUTPUT,
            edge_type=EdgeType.CONTROL,
            label="Done",
        )

    @staticmethod
    def switch_case(case_id: str = "*") -> Port:
        """Switch case output port."""
        return Port(
            id=f"case:{case_id}",
            direction=PortDirection.OUTPUT,
            edge_type=EdgeType.CONTROL,
            dynamic=True if case_id == "*" else False,
            label=f"Case {case_id}",
        )

    @staticmethod
    def switch_default() -> Port:
        """Switch default output port."""
        return Port(
            id="default",
            direction=PortDirection.OUTPUT,
            edge_type=EdgeType.CONTROL,
            label="Default",
        )
