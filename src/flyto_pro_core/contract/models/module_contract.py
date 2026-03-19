"""
Module Contract - Complete Contract for a Module

This is the single source of truth for what a module can do:
- What ports it has (connections)
- What parameters it accepts
- What data types it handles
- What it can connect to
- What version it is

The Contract Engine uses these contracts to:
1. Validate workflows
2. Determine valid connections
3. Resolve data bindings
4. Check version compatibility

Example:
    contract = ModuleContract(
        module_id="browser.goto",
        version="1.5.0",
        category="browser",
        label="Navigate to URL",
        description="Navigate the browser to a specified URL",
        ports=[
            Port(id="in", direction=PortDirection.INPUT, edge_type=EdgeType.DATA),
            Port(id="out", direction=PortDirection.OUTPUT, edge_type=EdgeType.DATA,
                 data_type="object", shape="object{url:string, title:string}"),
        ],
        params_schema=ParamsSchema(params={
            "url": ParamDef(type=ParamType.STRING, required=True, label="URL"),
            "wait_for": ParamDef(type=ParamType.SELECT, options=[...]),
        }),
        output_schema=DataContract(
            data_type=DataType.OBJECT,
            shape="object{url:string, title:string, status:number}"
        ),
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import re

from .port import Port, PortDirection, EdgeType
from .params_schema import ParamsSchema, ParamDef
from .data_contract import DataContract, DataType


@dataclass
class ConnectionPolicy:
    """
    Rules for what this module can connect to/from.

    Attributes:
        can_connect_from: Categories/module IDs that can connect to inputs
        cannot_connect_from: Categories/module IDs blocked from inputs
        can_connect_to: Categories/module IDs outputs can connect to
        cannot_connect_to: Categories/module IDs blocked from outputs
        requires_before: Module IDs that must appear before this one
        requires_after: Module IDs that must appear after this one
    """

    can_connect_from: List[str] = field(default_factory=list)
    cannot_connect_from: List[str] = field(default_factory=list)
    can_connect_to: List[str] = field(default_factory=list)
    cannot_connect_to: List[str] = field(default_factory=list)
    requires_before: List[str] = field(default_factory=list)
    requires_after: List[str] = field(default_factory=list)

    def allows_from(self, module_id: str, category: str) -> bool:
        """Check if connection from given module is allowed."""
        # Check blocklist first
        if module_id in self.cannot_connect_from or category in self.cannot_connect_from:
            return False

        # If allowlist is empty, allow all (except blocked)
        if not self.can_connect_from:
            return True

        # Check allowlist
        return module_id in self.can_connect_from or category in self.can_connect_from

    def allows_to(self, module_id: str, category: str) -> bool:
        """Check if connection to given module is allowed."""
        if module_id in self.cannot_connect_to or category in self.cannot_connect_to:
            return False

        if not self.can_connect_to:
            return True

        return module_id in self.can_connect_to or category in self.can_connect_to

    def to_dict(self) -> Dict[str, Any]:
        return {
            "can_connect_from": self.can_connect_from,
            "cannot_connect_from": self.cannot_connect_from,
            "can_connect_to": self.can_connect_to,
            "cannot_connect_to": self.cannot_connect_to,
            "requires_before": self.requires_before,
            "requires_after": self.requires_after,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ConnectionPolicy:
        return cls(
            can_connect_from=data.get("can_connect_from", []),
            cannot_connect_from=data.get("cannot_connect_from", []),
            can_connect_to=data.get("can_connect_to", []),
            cannot_connect_to=data.get("cannot_connect_to", []),
            requires_before=data.get("requires_before", []),
            requires_after=data.get("requires_after", []),
        )


@dataclass
class ModuleContract:
    """
    Complete contract for a module.

    This defines everything about what a module can do and how it connects.
    The Contract Engine uses this to validate workflows and connections.

    Attributes:
        module_id: Unique identifier (e.g., "browser.goto")
        version: Semantic version (e.g., "1.5.0")
        category: Module category (e.g., "browser", "data", "flow")
        label: Human-readable name
        description: Detailed description
        ports: Input and output ports
        params_schema: Parameter definitions
        output_schema: Schema for module output data
        connection_policy: Rules for valid connections
        tags: Searchable tags
        tier: License tier required (FREE, PRO, ENTERPRISE)
        deprecated: Whether module is deprecated
        deprecated_by: Replacement module ID if deprecated
        examples: Usage examples
    """

    module_id: str
    version: str = "1.0.0"
    category: str = ""
    label: str = ""
    description: str = ""
    ports: List[Port] = field(default_factory=list)
    params_schema: Optional[ParamsSchema] = None
    output_schema: Optional[DataContract] = None
    connection_policy: ConnectionPolicy = field(default_factory=ConnectionPolicy)
    tags: List[str] = field(default_factory=list)
    tier: str = "FREE"
    deprecated: bool = False
    deprecated_by: Optional[str] = None
    examples: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        """Set defaults from module_id."""
        if not self.category and "." in self.module_id:
            self.category = self.module_id.split(".")[0]
        if not self.label:
            self.label = self.module_id.replace(".", " ").replace("_", " ").title()

    def get_port(self, port_id: str) -> Optional[Port]:
        """Get a port by ID."""
        for port in self.ports:
            if port.id == port_id:
                return port
            # Handle dynamic ports (case:*)
            if port.dynamic and port.id.endswith(":*"):
                prefix = port.id[:-1]  # Remove *
                if port_id.startswith(prefix):
                    return port
        return None

    def get_input_ports(self) -> List[Port]:
        """Get all input ports."""
        return [p for p in self.ports if p.direction == PortDirection.INPUT]

    def get_output_ports(self) -> List[Port]:
        """Get all output ports."""
        return [p for p in self.ports if p.direction == PortDirection.OUTPUT]

    def get_data_ports(self) -> List[Port]:
        """Get all data ports (vs control flow)."""
        return [p for p in self.ports if p.edge_type == EdgeType.DATA]

    def get_control_ports(self) -> List[Port]:
        """Get all control flow ports."""
        return [p for p in self.ports if p.edge_type == EdgeType.CONTROL]

    def can_connect_to(self, other: ModuleContract, from_port_id: str, to_port_id: str) -> tuple[bool, Optional[str]]:
        """
        Check if this module can connect to another.

        Args:
            other: Target module contract
            from_port_id: Output port on this module
            to_port_id: Input port on target module

        Returns:
            Tuple of (can_connect, reason_if_not)
        """
        # Get ports
        from_port = self.get_port(from_port_id)
        to_port = other.get_port(to_port_id)

        if not from_port:
            return False, f"Port '{from_port_id}' not found on {self.module_id}"
        if not to_port:
            return False, f"Port '{to_port_id}' not found on {other.module_id}"

        # Check direction
        if from_port.direction != PortDirection.OUTPUT:
            return False, f"Port '{from_port_id}' is not an output port"
        if to_port.direction != PortDirection.INPUT:
            return False, f"Port '{to_port_id}' is not an input port"

        # Check edge type compatibility
        if from_port.edge_type != to_port.edge_type:
            return False, f"Edge type mismatch: {from_port.edge_type.value} -> {to_port.edge_type.value}"

        # Check data type compatibility
        if not from_port.is_compatible_type(to_port):
            return False, f"Data type mismatch: {from_port.data_type} -> {to_port.data_type}"

        # Check connection policy
        if not self.connection_policy.allows_to(other.module_id, other.category):
            return False, f"Connection policy blocks {self.module_id} -> {other.module_id}"
        if not other.connection_policy.allows_from(self.module_id, self.category):
            return False, f"Connection policy blocks {self.module_id} -> {other.module_id}"

        # Check port-level restrictions
        if from_port.rejects_from and (other.module_id in from_port.rejects_from or other.category in from_port.rejects_from):
            return False, f"Port '{from_port_id}' rejects connection from {other.module_id}"
        if to_port.rejects_from and (self.module_id in to_port.rejects_from or self.category in to_port.rejects_from):
            return False, f"Port '{to_port_id}' rejects connection from {self.module_id}"

        return True, None

    def get_version_parts(self) -> tuple[int, int, int]:
        """Parse version into (major, minor, patch)."""
        match = re.match(r"(\d+)\.(\d+)\.(\d+)", self.version)
        if match:
            return int(match.group(1)), int(match.group(2)), int(match.group(3))
        return 0, 0, 0

    def is_compatible_with(self, required_version: str) -> bool:
        """
        Check if this module version is compatible with required version.

        Uses semver major version compatibility:
        - Same major version = compatible
        - Different major version = incompatible
        """
        current = self.get_version_parts()
        match = re.match(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", required_version)
        if not match:
            return True  # No version requirement

        required_major = int(match.group(1))
        required_minor = int(match.group(2) or 0)

        # Major version must match
        if current[0] != required_major:
            return False

        # Current minor must be >= required minor
        if current[1] < required_minor:
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "module_id": self.module_id,
            "version": self.version,
            "category": self.category,
            "label": self.label,
            "description": self.description,
            "ports": [p.to_dict() for p in self.ports],
            "params_schema": self.params_schema.to_dict() if self.params_schema else None,
            "output_schema": self.output_schema.to_dict() if self.output_schema else None,
            "connection_policy": self.connection_policy.to_dict(),
            "tags": self.tags,
            "tier": self.tier,
            "deprecated": self.deprecated,
            "deprecated_by": self.deprecated_by,
            "examples": self.examples,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ModuleContract:
        """Create from dictionary."""
        ports = [Port.from_dict(p) for p in data.get("ports", [])]

        params_schema = None
        if data.get("params_schema"):
            params_schema = ParamsSchema.from_dict(data["params_schema"])

        output_schema = None
        if data.get("output_schema"):
            output_schema = DataContract.from_dict(data["output_schema"])

        connection_policy = ConnectionPolicy()
        if data.get("connection_policy"):
            connection_policy = ConnectionPolicy.from_dict(data["connection_policy"])

        return cls(
            module_id=data["module_id"],
            version=data.get("version", "1.0.0"),
            category=data.get("category", ""),
            label=data.get("label", ""),
            description=data.get("description", ""),
            ports=ports,
            params_schema=params_schema,
            output_schema=output_schema,
            connection_policy=connection_policy,
            tags=data.get("tags", []),
            tier=data.get("tier", "FREE"),
            deprecated=data.get("deprecated", False),
            deprecated_by=data.get("deprecated_by"),
            examples=data.get("examples", []),
        )

    @classmethod
    def from_flyto_core_metadata(cls, module_id: str, metadata: Dict[str, Any]) -> ModuleContract:
        """
        Create a ModuleContract from flyto-core registry metadata.

        This bridges the existing flyto-core module system with the Contract Engine.
        """
        # Default ports if not specified
        ports = []
        if "ports" in metadata:
            ports = [Port.from_dict(p) for p in metadata["ports"]]
        else:
            # Create default data flow ports
            ports = [
                Port(id="in", direction=PortDirection.INPUT, edge_type=EdgeType.DATA),
                Port(id="out", direction=PortDirection.OUTPUT, edge_type=EdgeType.DATA),
            ]

        # Parse params_schema
        params_schema = None
        if "params_schema" in metadata:
            params_schema = ParamsSchema.from_flyto_core_schema(metadata["params_schema"])

        # Parse output_schema
        output_schema = None
        if "output_schema" in metadata:
            output_schema = DataContract.from_dict(metadata["output_schema"])

        # Handle i18n labels
        label = metadata.get("label", "")
        if isinstance(label, dict):
            label = label.get("en") or next(iter(label.values()), "")

        description = metadata.get("description", "")
        if isinstance(description, dict):
            description = description.get("en") or next(iter(description.values()), "")

        return cls(
            module_id=module_id,
            version=metadata.get("version", "1.0.0"),
            category=metadata.get("category", module_id.split(".")[0] if "." in module_id else ""),
            label=label,
            description=description,
            ports=ports,
            params_schema=params_schema,
            output_schema=output_schema,
            tags=metadata.get("tags", []),
            tier=metadata.get("tier", "FREE"),
            deprecated=metadata.get("deprecated", False),
            deprecated_by=metadata.get("deprecated_by"),
        )


# Common control flow contracts
class ControlFlowContracts:
    """Pre-defined contracts for control flow modules."""

    @staticmethod
    def if_else() -> ModuleContract:
        """If-Else branching contract."""
        return ModuleContract(
            module_id="flow.if_else",
            version="1.0.0",
            category="flow",
            label="If-Else",
            description="Conditional branching based on a condition",
            ports=[
                Port(id="in", direction=PortDirection.INPUT, edge_type=EdgeType.DATA),
                Port(id="true", direction=PortDirection.OUTPUT, edge_type=EdgeType.CONTROL, label="True"),
                Port(id="false", direction=PortDirection.OUTPUT, edge_type=EdgeType.CONTROL, label="False"),
            ],
            params_schema=ParamsSchema(params={
                "condition": ParamDef(type="expression", required=True, label="Condition"),
            }),
        )

    @staticmethod
    def loop() -> ModuleContract:
        """Loop/foreach contract."""
        return ModuleContract(
            module_id="flow.loop",
            version="1.0.0",
            category="flow",
            label="Loop",
            description="Iterate over items",
            ports=[
                Port(id="in", direction=PortDirection.INPUT, edge_type=EdgeType.DATA,
                     data_type="array"),
                Port(id="body", direction=PortDirection.OUTPUT, edge_type=EdgeType.CONTROL,
                     label="Loop Body", scope_provides=["loop.item", "loop.index"]),
                Port(id="done", direction=PortDirection.OUTPUT, edge_type=EdgeType.CONTROL,
                     label="Done"),
            ],
            params_schema=ParamsSchema(params={
                "items": ParamDef(type="expression", required=True, label="Items to loop"),
                "item_var": ParamDef(type="string", default="item", label="Item variable name"),
            }),
        )

    @staticmethod
    def switch() -> ModuleContract:
        """Switch/case contract."""
        return ModuleContract(
            module_id="flow.switch",
            version="1.0.0",
            category="flow",
            label="Switch",
            description="Multi-way branching based on value",
            ports=[
                Port(id="in", direction=PortDirection.INPUT, edge_type=EdgeType.DATA),
                Port(id="case:*", direction=PortDirection.OUTPUT, edge_type=EdgeType.CONTROL,
                     dynamic=True, label="Case"),
                Port(id="default", direction=PortDirection.OUTPUT, edge_type=EdgeType.CONTROL,
                     label="Default"),
            ],
            params_schema=ParamsSchema(params={
                "value": ParamDef(type="expression", required=True, label="Value to switch on"),
                "cases": ParamDef(type="array", required=True, label="Case values"),
            }),
        )

    @staticmethod
    def try_catch() -> ModuleContract:
        """Try-catch error handling contract."""
        return ModuleContract(
            module_id="flow.try_catch",
            version="1.0.0",
            category="flow",
            label="Try-Catch",
            description="Error handling wrapper",
            ports=[
                Port(id="in", direction=PortDirection.INPUT, edge_type=EdgeType.DATA),
                Port(id="try", direction=PortDirection.OUTPUT, edge_type=EdgeType.CONTROL,
                     label="Try"),
                Port(id="catch", direction=PortDirection.OUTPUT, edge_type=EdgeType.CONTROL,
                     label="Catch", scope_provides=["error.message", "error.type"]),
                Port(id="finally", direction=PortDirection.OUTPUT, edge_type=EdgeType.CONTROL,
                     label="Finally"),
            ],
        )
