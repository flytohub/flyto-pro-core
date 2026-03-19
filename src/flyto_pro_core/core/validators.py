"""
Shared Validators - Common validation patterns

Provides reusable validation functions to reduce code duplication
and ensure consistent error handling across the codebase.
"""

import re
import logging
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ValidationError(Exception):
    """Raised when validation fails."""

    def __init__(
        self,
        message: str,
        code: str = None,
        param_name: str = None,
        suggestion: str = None,
    ):
        self.message = message
        self.code = code or "VALIDATION_ERROR"
        self.param_name = param_name
        self.suggestion = suggestion
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.message,
            "code": self.code,
            "param": self.param_name,
            "suggestion": self.suggestion,
        }


class Validator:
    """
    Fluent validator for parameters.

    Usage:
        Validator.value(user_id).not_none().is_string().matches(r'^[a-zA-Z0-9]+$')
        Validator.value(limit).not_none().is_int().in_range(1, 100)
    """

    def __init__(self, value: Any, param_name: str = "value"):
        self._value = value
        self._param_name = param_name

    @classmethod
    def value(cls, val: Any, name: str = "value") -> "Validator":
        """Create a new validator for a value."""
        return cls(val, name)

    def not_none(self, message: str = None) -> "Validator":
        """Ensure value is not None."""
        if self._value is None:
            raise ValidationError(
                message or f"{self._param_name} cannot be None",
                code=f"INVALID_{self._param_name.upper()}",
                param_name=self._param_name,
            )
        return self

    def not_empty(self, message: str = None) -> "Validator":
        """Ensure value is not empty (works for str, list, dict)."""
        if not self._value:
            raise ValidationError(
                message or f"{self._param_name} cannot be empty",
                code=f"EMPTY_{self._param_name.upper()}",
                param_name=self._param_name,
            )
        return self

    def is_string(self, message: str = None) -> "Validator":
        """Ensure value is a string."""
        if not isinstance(self._value, str):
            raise ValidationError(
                message or f"{self._param_name} must be a string",
                code="INVALID_TYPE",
                param_name=self._param_name,
            )
        return self

    def is_int(self, message: str = None) -> "Validator":
        """Ensure value is an integer."""
        if not isinstance(self._value, int) or isinstance(self._value, bool):
            raise ValidationError(
                message or f"{self._param_name} must be an integer",
                code="INVALID_TYPE",
                param_name=self._param_name,
            )
        return self

    def is_float(self, message: str = None) -> "Validator":
        """Ensure value is a float or int."""
        if not isinstance(self._value, (int, float)) or isinstance(self._value, bool):
            raise ValidationError(
                message or f"{self._param_name} must be a number",
                code="INVALID_TYPE",
                param_name=self._param_name,
            )
        return self

    def is_list(self, message: str = None) -> "Validator":
        """Ensure value is a list."""
        if not isinstance(self._value, list):
            raise ValidationError(
                message or f"{self._param_name} must be a list",
                code="INVALID_TYPE",
                param_name=self._param_name,
            )
        return self

    def is_dict(self, message: str = None) -> "Validator":
        """Ensure value is a dictionary."""
        if not isinstance(self._value, dict):
            raise ValidationError(
                message or f"{self._param_name} must be a dictionary",
                code="INVALID_TYPE",
                param_name=self._param_name,
            )
        return self

    def is_type(self, expected_type: Type, message: str = None) -> "Validator":
        """Ensure value is of a specific type."""
        if not isinstance(self._value, expected_type):
            raise ValidationError(
                message or f"{self._param_name} must be {expected_type.__name__}",
                code="INVALID_TYPE",
                param_name=self._param_name,
            )
        return self

    def in_range(
        self,
        min_val: Union[int, float] = None,
        max_val: Union[int, float] = None,
        message: str = None,
    ) -> "Validator":
        """Ensure numeric value is within range."""
        if min_val is not None and self._value < min_val:
            raise ValidationError(
                message or f"{self._param_name} must be >= {min_val}",
                code="OUT_OF_RANGE",
                param_name=self._param_name,
            )
        if max_val is not None and self._value > max_val:
            raise ValidationError(
                message or f"{self._param_name} must be <= {max_val}",
                code="OUT_OF_RANGE",
                param_name=self._param_name,
            )
        return self

    def max_length(self, max_len: int, message: str = None) -> "Validator":
        """Ensure string/list length doesn't exceed max."""
        if len(self._value) > max_len:
            raise ValidationError(
                message or f"{self._param_name} exceeds max length {max_len}",
                code="TOO_LONG",
                param_name=self._param_name,
            )
        return self

    def min_length(self, min_len: int, message: str = None) -> "Validator":
        """Ensure string/list length is at least min."""
        if len(self._value) < min_len:
            raise ValidationError(
                message or f"{self._param_name} must be at least {min_len} characters",
                code="TOO_SHORT",
                param_name=self._param_name,
            )
        return self

    def matches(self, pattern: str, message: str = None) -> "Validator":
        """Ensure string matches regex pattern."""
        if not re.match(pattern, self._value):
            raise ValidationError(
                message or f"{self._param_name} has invalid format",
                code="INVALID_FORMAT",
                param_name=self._param_name,
            )
        return self

    def one_of(self, allowed: List[Any], message: str = None) -> "Validator":
        """Ensure value is one of allowed values."""
        if self._value not in allowed:
            raise ValidationError(
                message or f"{self._param_name} must be one of {allowed}",
                code="INVALID_VALUE",
                param_name=self._param_name,
            )
        return self

    def satisfies(
        self,
        predicate: Callable[[Any], bool],
        message: str = None,
    ) -> "Validator":
        """Ensure value satisfies custom predicate."""
        if not predicate(self._value):
            raise ValidationError(
                message or f"{self._param_name} validation failed",
                code="VALIDATION_FAILED",
                param_name=self._param_name,
            )
        return self

    def get(self) -> Any:
        """Get the validated value."""
        return self._value


# Convenience functions for common validations

def validate_not_none(value: T, param_name: str = "value") -> T:
    """Validate value is not None."""
    Validator.value(value, param_name).not_none()
    return value


def validate_string(
    value: Any,
    param_name: str = "value",
    max_length: int = None,
    pattern: str = None,
) -> str:
    """Validate and return string value."""
    v = Validator.value(value, param_name).not_none().is_string()
    if max_length:
        v.max_length(max_length)
    if pattern:
        v.matches(pattern)
    return value


def validate_int(
    value: Any,
    param_name: str = "value",
    min_val: int = None,
    max_val: int = None,
) -> int:
    """Validate and return integer value."""
    v = Validator.value(value, param_name).not_none().is_int()
    if min_val is not None or max_val is not None:
        v.in_range(min_val, max_val)
    return value


def validate_list(
    value: Any,
    param_name: str = "value",
    min_length: int = None,
    max_length: int = None,
) -> list:
    """Validate and return list value."""
    v = Validator.value(value, param_name).not_none().is_list()
    if min_length:
        v.min_length(min_length)
    if max_length:
        v.max_length(max_length)
    return value


def validate_dict(
    value: Any,
    param_name: str = "value",
    required_keys: List[str] = None,
) -> dict:
    """Validate and return dict value."""
    Validator.value(value, param_name).not_none().is_dict()
    if required_keys:
        missing = [k for k in required_keys if k not in value]
        if missing:
            raise ValidationError(
                f"{param_name} missing required keys: {missing}",
                code="MISSING_KEYS",
                param_name=param_name,
            )
    return value


def safe_int(
    value: Any,
    default: int = 0,
    param_name: str = "value",
) -> int:
    """Safely convert value to int, returning default on failure."""
    try:
        return int(value)
    except (ValueError, TypeError) as e:
        logger.debug(f"Failed to convert {param_name} to int: {e}")
        return default


def safe_float(
    value: Any,
    default: float = 0.0,
    param_name: str = "value",
) -> float:
    """Safely convert value to float, returning default on failure."""
    try:
        return float(value)
    except (ValueError, TypeError) as e:
        logger.debug(f"Failed to convert {param_name} to float: {e}")
        return default
