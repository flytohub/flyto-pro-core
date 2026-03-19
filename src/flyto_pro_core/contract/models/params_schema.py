"""
Params Schema Definitions

Defines the schema for module parameters, used for:
1. UI rendering (what fields to show)
2. Runtime validation (are params valid)
3. Default values
4. Dynamic options (depends on other params or context)

This is designed to work with the existing flyto-core params_schema format
while adding enhanced features for the Contract Engine.

Example:
    schema = ParamsSchema(
        params={
            "url": ParamDef(
                type="string",
                required=True,
                label="URL",
                description="The URL to navigate to",
                placeholder="https://example.com",
                validation={"pattern": r"^https?://"},
            ),
            "wait_for": ParamDef(
                type="select",
                required=False,
                default="load",
                label="Wait For",
                options=[
                    {"value": "load", "label": "Page Load"},
                    {"value": "network", "label": "Network Idle"},
                ],
            ),
            "timeout": ParamDef(
                type="number",
                required=False,
                default=30000,
                label="Timeout (ms)",
                validation={"min": 1000, "max": 120000},
            ),
        }
    )
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class ParamType(str, Enum):
    """Supported parameter types."""

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    OBJECT = "object"
    ARRAY = "array"
    CODE = "code"
    FILE = "file"
    SECRET = "secret"
    EXPRESSION = "expression"  # Dynamic value from context
    SELECTOR = "selector"  # CSS/XPath selector with picker UI


@dataclass
class ParamOption:
    """Option for select/multi_select parameters."""

    value: Any
    label: str
    description: Optional[str] = None
    icon: Optional[str] = None
    disabled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        result = {"value": self.value, "label": self.label}
        if self.description:
            result["description"] = self.description
        if self.icon:
            result["icon"] = self.icon
        if self.disabled:
            result["disabled"] = self.disabled
        return result

    @classmethod
    def from_dict(cls, data: Union[Dict[str, Any], str]) -> ParamOption:
        if isinstance(data, str):
            return cls(value=data, label=data)
        return cls(
            value=data["value"],
            label=data.get("label", str(data["value"])),
            description=data.get("description"),
            icon=data.get("icon"),
            disabled=data.get("disabled", False),
        )


@dataclass
class ParamDef:
    """
    Definition for a single parameter.

    Attributes:
        type: Parameter type (string, number, select, etc.)
        required: Whether the parameter is required
        default: Default value if not provided
        label: Human-readable label for UI
        description: Detailed description/help text
        placeholder: Placeholder text for input fields
        options: For select types, the available options
        validation: Validation rules (min, max, pattern, etc.)
        depends_on: Other params this one depends on
        visible_when: Condition for when to show this param
        dynamic_options: Identifier for fetching options dynamically
        secret: Whether this is a sensitive value (masks input)
        multiline: For strings, whether to use textarea
        code_language: For code type, the language
        group: UI grouping identifier
        order: Display order within group
    """

    type: ParamType = ParamType.STRING
    required: bool = False
    default: Any = None
    label: Optional[str] = None
    description: Optional[str] = None
    placeholder: Optional[str] = None
    options: List[ParamOption] = field(default_factory=list)
    validation: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    visible_when: Optional[str] = None
    dynamic_options: Optional[str] = None
    secret: bool = False
    multiline: bool = False
    code_language: Optional[str] = None
    group: Optional[str] = None
    order: int = 0

    def validate(self, value: Any, all_params: Optional[Dict[str, Any]] = None) -> tuple[bool, Optional[str]]:
        """
        Validate a parameter value.

        Args:
            value: The value to validate
            all_params: All parameter values (for depends_on checks)

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Required check
        if value is None or value == "":
            if self.required:
                return False, f"Parameter is required"
            return True, None

        # Type checking
        type_validators = {
            ParamType.STRING: lambda v: isinstance(v, str),
            ParamType.NUMBER: lambda v: isinstance(v, (int, float)),
            ParamType.BOOLEAN: lambda v: isinstance(v, bool),
            ParamType.SELECT: lambda v: True,  # Validated against options
            ParamType.MULTI_SELECT: lambda v: isinstance(v, list),
            ParamType.OBJECT: lambda v: isinstance(v, dict),
            ParamType.ARRAY: lambda v: isinstance(v, list),
            ParamType.CODE: lambda v: isinstance(v, str),
            ParamType.FILE: lambda v: isinstance(v, str),
            ParamType.SECRET: lambda v: isinstance(v, str),
            ParamType.EXPRESSION: lambda v: isinstance(v, str),
            ParamType.SELECTOR: lambda v: isinstance(v, str),
        }

        validator = type_validators.get(self.type)
        if validator and not validator(value):
            return False, f"Invalid type, expected {self.type.value}"

        # Options validation for select types
        if self.type in (ParamType.SELECT, ParamType.MULTI_SELECT) and self.options:
            valid_values = [opt.value for opt in self.options]
            if self.type == ParamType.SELECT:
                if value not in valid_values:
                    return False, f"Value must be one of: {valid_values}"
            else:  # MULTI_SELECT
                for v in value:
                    if v not in valid_values:
                        return False, f"Value {v} must be one of: {valid_values}"

        # Validation rules
        if self.validation:
            valid, error = self._check_validation(value)
            if not valid:
                return False, error

        return True, None

    def _check_validation(self, value: Any) -> tuple[bool, Optional[str]]:
        """Apply validation rules."""
        v = self.validation

        # Min/Max for numbers
        if self.type == ParamType.NUMBER:
            if "min" in v and value < v["min"]:
                return False, f"Value must be >= {v['min']}"
            if "max" in v and value > v["max"]:
                return False, f"Value must be <= {v['max']}"

        # Min/Max length for strings
        if self.type in (ParamType.STRING, ParamType.CODE, ParamType.SECRET):
            if "min" in v and len(value) < v["min"]:
                return False, f"Length must be >= {v['min']}"
            if "max" in v and len(value) > v["max"]:
                return False, f"Length must be <= {v['max']}"

        # Pattern matching
        if "pattern" in v and isinstance(value, str):
            if not re.match(v["pattern"], value):
                return False, f"Value must match pattern: {v['pattern']}"

        # Custom validation message
        if "custom" in v:
            # Custom validations are evaluated at runtime
            pass

        return True, None

    def get_default(self) -> Any:
        """Get the default value, evaluating if needed."""
        return self.default

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "type": self.type.value,
            "required": self.required,
        }

        if self.default is not None:
            result["default"] = self.default
        if self.label:
            result["label"] = self.label
        if self.description:
            result["description"] = self.description
        if self.placeholder:
            result["placeholder"] = self.placeholder
        if self.options:
            result["options"] = [opt.to_dict() for opt in self.options]
        if self.validation:
            result["validation"] = self.validation
        if self.depends_on:
            result["depends_on"] = self.depends_on
        if self.visible_when:
            result["visible_when"] = self.visible_when
        if self.dynamic_options:
            result["dynamic_options"] = self.dynamic_options
        if self.secret:
            result["secret"] = self.secret
        if self.multiline:
            result["multiline"] = self.multiline
        if self.code_language:
            result["code_language"] = self.code_language
        if self.group:
            result["group"] = self.group
        if self.order:
            result["order"] = self.order

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ParamDef:
        """Create from dictionary."""
        options = []
        if "options" in data:
            options = [ParamOption.from_dict(opt) for opt in data["options"]]

        return cls(
            type=ParamType(data.get("type", "string")),
            required=data.get("required", False),
            default=data.get("default"),
            label=data.get("label"),
            description=data.get("description"),
            placeholder=data.get("placeholder"),
            options=options,
            validation=data.get("validation", {}),
            depends_on=data.get("depends_on", []),
            visible_when=data.get("visible_when"),
            dynamic_options=data.get("dynamic_options"),
            secret=data.get("secret", False),
            multiline=data.get("multiline", False),
            code_language=data.get("code_language"),
            group=data.get("group"),
            order=data.get("order", 0),
        )


@dataclass
class ParamsSchema:
    """
    Complete parameter schema for a module.

    Attributes:
        params: Dictionary of parameter definitions
        groups: UI grouping configuration
        validation_order: Order to validate params (for dependencies)
    """

    params: Dict[str, ParamDef] = field(default_factory=dict)
    groups: List[Dict[str, str]] = field(default_factory=list)
    validation_order: List[str] = field(default_factory=list)

    def validate(self, values: Dict[str, Any]) -> tuple[bool, Dict[str, str]]:
        """
        Validate all parameter values.

        Args:
            values: Parameter values to validate

        Returns:
            Tuple of (is_valid, errors_by_param_name)
        """
        errors = {}

        # Determine validation order
        order = self.validation_order or list(self.params.keys())

        for param_name in order:
            if param_name not in self.params:
                continue

            param_def = self.params[param_name]
            value = values.get(param_name)

            # Check visibility condition
            if param_def.visible_when:
                if not self._evaluate_condition(param_def.visible_when, values):
                    continue  # Skip validation for hidden params

            valid, error = param_def.validate(value, values)
            if not valid:
                errors[param_name] = error

        return len(errors) == 0, errors

    def _evaluate_condition(self, condition: str, values: Dict[str, Any]) -> bool:
        """Evaluate a visibility condition."""
        # Simple condition format: "param_name == value" or "param_name != value"
        # or "param_name" (truthy check)
        try:
            if "==" in condition:
                param, expected = condition.split("==")
                param = param.strip()
                expected = expected.strip().strip("'\"")
                return str(values.get(param)) == expected
            elif "!=" in condition:
                param, expected = condition.split("!=")
                param = param.strip()
                expected = expected.strip().strip("'\"")
                return str(values.get(param)) != expected
            else:
                # Truthy check
                return bool(values.get(condition.strip()))
        except Exception as e:
            logger.debug(f"Condition parse failed for '{condition}': {e}")
            return True  # Default to visible on parse errors

    def get_defaults(self) -> Dict[str, Any]:
        """Get default values for all parameters."""
        return {
            name: param_def.get_default()
            for name, param_def in self.params.items()
            if param_def.default is not None
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "params": {name: p.to_dict() for name, p in self.params.items()},
            "groups": self.groups,
            "validation_order": self.validation_order,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ParamsSchema:
        """Create from dictionary."""
        params = {}
        params_data = data.get("params", data)  # Support flat format

        for name, param_data in params_data.items():
            if isinstance(param_data, dict):
                params[name] = ParamDef.from_dict(param_data)

        return cls(
            params=params,
            groups=data.get("groups", []),
            validation_order=data.get("validation_order", []),
        )

    @classmethod
    def from_flyto_core_schema(cls, schema: Dict[str, Any]) -> ParamsSchema:
        """
        Convert flyto-core params_schema format to ParamsSchema.

        flyto-core format:
        {
            "url": {
                "type": "string",
                "required": true,
                "label": {"en": "URL", "zh": "网址"},
                "description": {"en": "...", "zh": "..."}
            }
        }
        """
        params = {}

        for name, param_data in schema.items():
            if not isinstance(param_data, dict):
                continue

            # Handle i18n labels (take English or first available)
            label = param_data.get("label")
            if isinstance(label, dict):
                label = label.get("en") or next(iter(label.values()), None)

            description = param_data.get("description")
            if isinstance(description, dict):
                description = description.get("en") or next(iter(description.values()), None)

            placeholder = param_data.get("placeholder")
            if isinstance(placeholder, dict):
                placeholder = placeholder.get("en") or next(iter(placeholder.values()), None)

            # Handle options
            options = []
            if "options" in param_data:
                for opt in param_data["options"]:
                    if isinstance(opt, dict):
                        opt_label = opt.get("label")
                        if isinstance(opt_label, dict):
                            opt_label = opt_label.get("en") or next(iter(opt_label.values()), "")
                        options.append(ParamOption(
                            value=opt.get("value", opt_label),
                            label=opt_label or str(opt.get("value", "")),
                        ))
                    else:
                        options.append(ParamOption(value=opt, label=str(opt)))

            params[name] = ParamDef(
                type=ParamType(param_data.get("type", "string")),
                required=param_data.get("required", False),
                default=param_data.get("default"),
                label=label,
                description=description,
                placeholder=placeholder,
                options=options,
                validation={
                    k: v for k, v in param_data.items()
                    if k in ("min", "max", "pattern", "minLength", "maxLength")
                },
                secret=param_data.get("secret", False),
                multiline=param_data.get("multiline", False),
            )

        return cls(params=params)
