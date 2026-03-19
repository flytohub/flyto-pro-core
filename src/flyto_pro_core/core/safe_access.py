"""
Safe Access Utilities - Prevent IndexError and KeyError crashes

Provides safe access patterns for lists, dicts, and nested structures.
Use these utilities instead of direct [0] access.
"""

from typing import Any, Dict, List, Optional, TypeVar, Callable

T = TypeVar("T")


class SafeAccessError(Exception):
    """Raised when safe access fails and no default is provided."""

    def __init__(self, message: str, path: str = None):
        self.message = message
        self.path = path
        super().__init__(message)


def safe_first(
    items: List[T],
    default: T = None,
    error_msg: str = None,
) -> Optional[T]:
    """
    Safely get the first item from a list.

    Args:
        items: List to access
        default: Default value if list is empty (None if not provided)
        error_msg: If provided, raise SafeAccessError instead of returning default

    Returns:
        First item or default value

    Raises:
        SafeAccessError: If list is empty and error_msg is provided

    Usage:
        # Instead of: content = message.content[0].text
        content = safe_first(message.content)
        if content:
            text = content.text

        # Or with error:
        content = safe_first(message.content, error_msg="Empty response content")
    """
    if items and len(items) > 0:
        return items[0]

    if error_msg:
        raise SafeAccessError(error_msg, path="[0]")

    return default


def safe_last(
    items: List[T],
    default: T = None,
    error_msg: str = None,
) -> Optional[T]:
    """Safely get the last item from a list."""
    if items and len(items) > 0:
        return items[-1]

    if error_msg:
        raise SafeAccessError(error_msg, path="[-1]")

    return default


def safe_index(
    items: List[T],
    index: int,
    default: T = None,
    error_msg: str = None,
) -> Optional[T]:
    """
    Safely get an item at a specific index.

    Args:
        items: List to access
        index: Index to access
        default: Default value if index out of bounds
        error_msg: If provided, raise SafeAccessError instead of returning default

    Returns:
        Item at index or default value
    """
    if items and 0 <= index < len(items):
        return items[index]

    if error_msg:
        raise SafeAccessError(error_msg, path=f"[{index}]")

    return default


def safe_get(
    obj: Dict[str, Any],
    *keys: str,
    default: Any = None,
    error_msg: str = None,
) -> Any:
    """
    Safely get a nested value from a dictionary.

    Args:
        obj: Dictionary to access
        *keys: Keys to traverse (supports nested access)
        default: Default value if key not found
        error_msg: If provided, raise SafeAccessError instead of returning default

    Returns:
        Value at key path or default

    Usage:
        # Instead of: result["results"][0]["data"]
        data = safe_get(result, "results", 0, "data")
    """
    current = obj
    path_parts = []

    for key in keys:
        path_parts.append(str(key))

        if current is None:
            if error_msg:
                raise SafeAccessError(error_msg, path=".".join(path_parts))
            return default

        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, (list, tuple)) and isinstance(key, int):
            if 0 <= key < len(current):
                current = current[key]
            else:
                if error_msg:
                    raise SafeAccessError(error_msg, path=".".join(path_parts))
                return default
        else:
            if error_msg:
                raise SafeAccessError(error_msg, path=".".join(path_parts))
            return default

    return current if current is not None else default


def safe_split_first(
    text: str,
    separator: str = None,
    default: str = None,
    error_msg: str = None,
) -> Optional[str]:
    """
    Safely get the first part of a split string.

    Args:
        text: String to split
        separator: Separator to use (None for whitespace)
        default: Default if split produces empty result
        error_msg: If provided, raise SafeAccessError instead of returning default

    Usage:
        # Instead of: words = line.split(); cmd = words[0]
        cmd = safe_split_first(line)
    """
    if not text:
        if error_msg:
            raise SafeAccessError(error_msg)
        return default

    parts = text.split(separator) if separator else text.split()
    return safe_first(parts, default=default, error_msg=error_msg)


def safe_attr(
    obj: Any,
    attr: str,
    default: Any = None,
    error_msg: str = None,
) -> Any:
    """
    Safely get an attribute from an object.

    Args:
        obj: Object to access
        attr: Attribute name
        default: Default if attribute doesn't exist
        error_msg: If provided, raise SafeAccessError instead of returning default

    Usage:
        # Instead of: content = response.choices[0].message.content
        choice = safe_first(response.choices)
        content = safe_attr(safe_attr(choice, "message"), "content")
    """
    if obj is None:
        if error_msg:
            raise SafeAccessError(error_msg, path=attr)
        return default

    return getattr(obj, attr, default)


def safe_chain(
    obj: Any,
    *accessors: str,
    default: Any = None,
    error_msg: str = None,
) -> Any:
    """
    Safely traverse a chain of attributes and indices.

    Args:
        obj: Starting object
        *accessors: Chain of attribute names or indices
            - String: attribute access
            - "[0]", "[-1]": index access
            - "key": dict key access

    Usage:
        # Instead of: response.choices[0].message.content
        content = safe_chain(response, "choices", "[0]", "message", "content")
    """
    current = obj
    path_parts = []

    for accessor in accessors:
        path_parts.append(accessor)

        if current is None:
            if error_msg:
                raise SafeAccessError(error_msg, path=" -> ".join(path_parts))
            return default

        # Index access: "[0]", "[-1]"
        if accessor.startswith("[") and accessor.endswith("]"):
            try:
                index = int(accessor[1:-1])
            except ValueError:
                if error_msg:
                    raise SafeAccessError(f"Invalid index: {accessor}", path=" -> ".join(path_parts))
                return default

            if isinstance(current, (list, tuple)):
                if -len(current) <= index < len(current):
                    current = current[index]
                else:
                    if error_msg:
                        raise SafeAccessError(error_msg, path=" -> ".join(path_parts))
                    return default
            else:
                if error_msg:
                    raise SafeAccessError(f"Cannot index {type(current).__name__}", path=" -> ".join(path_parts))
                return default

        # Dict or attribute access
        elif isinstance(current, dict):
            current = current.get(accessor)

        elif hasattr(current, accessor):
            current = getattr(current, accessor)

        else:
            if error_msg:
                raise SafeAccessError(error_msg, path=" -> ".join(path_parts))
            return default

    return current if current is not None else default


# Type-safe helpers for common patterns

def safe_response_content(response: Any, default: str = "") -> str:
    """
    Safely extract content from OpenAI-style response.

    Handles: response.choices[0].message.content
    """
    choice = safe_first(safe_attr(response, "choices", []))
    if not choice:
        return default
    message = safe_attr(choice, "message")
    if not message:
        return default
    return safe_attr(message, "content", default)


def safe_result_data(result: Dict[str, Any], default: Any = None) -> Any:
    """
    Safely extract data from result dict.

    Handles: result["results"][0] or result["data"][0]
    """
    results = result.get("results") or result.get("data") or []
    return safe_first(results, default=default)
