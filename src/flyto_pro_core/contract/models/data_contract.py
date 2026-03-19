"""
Data Contract Definitions

Defines the type system for data flowing between modules.
This is a simplified type system focused on practical use cases.

Supported Types:
- string: Text data
- number: Numeric data (int or float)
- boolean: True/False
- object: Key-value dictionary
- array: List of items
- any: Accepts any type
- null: Null/None value
- file: File reference (path or buffer)
- element: Browser DOM element reference
- buffer: Binary data

Shape Notation (for complex types):
- array<string>: Array of strings
- array<object{url:string, title:string}>: Array of objects with specific fields
- object{rows:array, headers:array<string>}: Object with specific structure

Example:
    # Simple string type
    contract = DataContract(data_type=DataType.STRING)

    # Array of URLs
    contract = DataContract(
        data_type=DataType.ARRAY,
        item_type=DataType.STRING,
        shape="array<string:url>"
    )

    # CSV data structure
    contract = DataContract(
        data_type=DataType.OBJECT,
        shape="object{rows:array<object>, headers:array<string>}"
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import re


class DataType(str, Enum):
    """Supported data types."""

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    ANY = "any"
    NULL = "null"
    FILE = "file"
    ELEMENT = "element"
    BUFFER = "buffer"


@dataclass
class DataContract:
    """
    Contract defining the structure of data at a port.

    Attributes:
        data_type: Primary data type
        item_type: For arrays, the type of items
        shape: Shape descriptor for complex structures
        nullable: Whether null is allowed
        default: Default value if not provided
        constraints: Additional constraints (min, max, pattern, etc.)
        examples: Example values for documentation
    """

    data_type: DataType = DataType.ANY
    item_type: Optional[DataType] = None
    shape: Optional[str] = None
    nullable: bool = False
    default: Optional[Any] = None
    constraints: Dict[str, Any] = field(default_factory=dict)
    examples: List[Any] = field(default_factory=list)

    def validate(self, value: Any) -> tuple[bool, Optional[str]]:
        """
        Validate a value against this contract.

        Args:
            value: Value to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Handle null
        if value is None:
            if self.nullable:
                return True, None
            return False, "Value cannot be null"

        # Type checking
        if self.data_type == DataType.ANY:
            return True, None

        type_map = {
            DataType.STRING: str,
            DataType.NUMBER: (int, float),
            DataType.BOOLEAN: bool,
            DataType.OBJECT: dict,
            DataType.ARRAY: (list, tuple),
            DataType.FILE: str,  # File paths are strings
            DataType.ELEMENT: dict,  # Element refs are serialized as dicts
            DataType.BUFFER: (bytes, bytearray),
        }

        expected_type = type_map.get(self.data_type)
        if expected_type and not isinstance(value, expected_type):
            return False, f"Expected {self.data_type.value}, got {type(value).__name__}"

        # Array item type checking
        if self.data_type == DataType.ARRAY and self.item_type:
            item_contract = DataContract(data_type=self.item_type)
            for i, item in enumerate(value):
                valid, error = item_contract.validate(item)
                if not valid:
                    return False, f"Array item {i}: {error}"

        # Constraint checking
        if self.constraints:
            valid, error = self._check_constraints(value)
            if not valid:
                return False, error

        return True, None

    def _check_constraints(self, value: Any) -> tuple[bool, Optional[str]]:
        """Check value against constraints."""
        if "min" in self.constraints:
            if isinstance(value, (int, float)) and value < self.constraints["min"]:
                return False, f"Value must be >= {self.constraints['min']}"
            if isinstance(value, str) and len(value) < self.constraints["min"]:
                return False, f"Length must be >= {self.constraints['min']}"
            if isinstance(value, (list, tuple)) and len(value) < self.constraints["min"]:
                return False, f"Length must be >= {self.constraints['min']}"

        if "max" in self.constraints:
            if isinstance(value, (int, float)) and value > self.constraints["max"]:
                return False, f"Value must be <= {self.constraints['max']}"
            if isinstance(value, str) and len(value) > self.constraints["max"]:
                return False, f"Length must be <= {self.constraints['max']}"
            if isinstance(value, (list, tuple)) and len(value) > self.constraints["max"]:
                return False, f"Length must be <= {self.constraints['max']}"

        if "pattern" in self.constraints and isinstance(value, str):
            if not re.match(self.constraints["pattern"], value):
                return False, f"Value must match pattern: {self.constraints['pattern']}"

        if "enum" in self.constraints:
            if value not in self.constraints["enum"]:
                return False, f"Value must be one of: {self.constraints['enum']}"

        return True, None

    def is_compatible_with(self, other: DataContract) -> bool:
        """Check if this contract is compatible with another (for connections)."""
        # Any is always compatible
        if self.data_type == DataType.ANY or other.data_type == DataType.ANY:
            return True

        # Exact match
        if self.data_type == other.data_type:
            # For arrays, check item types
            if self.data_type == DataType.ARRAY:
                if self.item_type and other.item_type:
                    return self.item_type == other.item_type or DataType.ANY in (
                        self.item_type,
                        other.item_type,
                    )
            return True

        # Coercible types
        coercible_pairs = [
            (DataType.STRING, DataType.NUMBER),
            (DataType.NUMBER, DataType.STRING),
            (DataType.STRING, DataType.BOOLEAN),
            (DataType.BOOLEAN, DataType.STRING),
            (DataType.OBJECT, DataType.STRING),  # JSON stringify
        ]

        return (self.data_type, other.data_type) in coercible_pairs

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "data_type": self.data_type.value,
            "nullable": self.nullable,
        }
        if self.item_type:
            result["item_type"] = self.item_type.value
        if self.shape:
            result["shape"] = self.shape
        if self.default is not None:
            result["default"] = self.default
        if self.constraints:
            result["constraints"] = self.constraints
        if self.examples:
            result["examples"] = self.examples
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DataContract:
        """Create from dictionary."""
        return cls(
            data_type=DataType(data.get("data_type", "any")),
            item_type=DataType(data["item_type"]) if data.get("item_type") else None,
            shape=data.get("shape"),
            nullable=data.get("nullable", False),
            default=data.get("default"),
            constraints=data.get("constraints", {}),
            examples=data.get("examples", []),
        )

    @classmethod
    def from_type_string(cls, type_str: str) -> DataContract:
        """
        Parse a type string into a DataContract.

        Examples:
            "string" -> DataContract(data_type=DataType.STRING)
            "array<string>" -> DataContract(data_type=DataType.ARRAY, item_type=DataType.STRING)
            "string?" -> DataContract(data_type=DataType.STRING, nullable=True)
        """
        # Handle nullable
        nullable = type_str.endswith("?")
        if nullable:
            type_str = type_str[:-1]

        # Handle array notation
        array_match = re.match(r"array<(.+)>", type_str)
        if array_match:
            item_type_str = array_match.group(1)
            try:
                item_type = DataType(item_type_str.split("{")[0])
            except ValueError:
                item_type = DataType.ANY
            return cls(
                data_type=DataType.ARRAY,
                item_type=item_type,
                shape=type_str,
                nullable=nullable,
            )

        # Handle simple types
        try:
            data_type = DataType(type_str)
        except ValueError:
            data_type = DataType.ANY

        return cls(data_type=data_type, nullable=nullable)


# Pre-defined contract templates
class ContractTemplates:
    """Common contract templates."""

    STRING = DataContract(data_type=DataType.STRING)
    NUMBER = DataContract(data_type=DataType.NUMBER)
    BOOLEAN = DataContract(data_type=DataType.BOOLEAN)
    OBJECT = DataContract(data_type=DataType.OBJECT)
    ARRAY = DataContract(data_type=DataType.ARRAY)
    ANY = DataContract(data_type=DataType.ANY)

    @staticmethod
    def string_array() -> DataContract:
        return DataContract(data_type=DataType.ARRAY, item_type=DataType.STRING)

    @staticmethod
    def number_array() -> DataContract:
        return DataContract(data_type=DataType.ARRAY, item_type=DataType.NUMBER)

    @staticmethod
    def url() -> DataContract:
        return DataContract(
            data_type=DataType.STRING,
            constraints={"pattern": r"^https?://"},
            examples=["https://example.com"],
        )

    @staticmethod
    def csv_data() -> DataContract:
        return DataContract(
            data_type=DataType.OBJECT,
            shape="object{rows:array<object>, headers:array<string>}",
        )

    @staticmethod
    def file_path() -> DataContract:
        return DataContract(data_type=DataType.FILE)

    @staticmethod
    def element_ref() -> DataContract:
        return DataContract(data_type=DataType.ELEMENT)
