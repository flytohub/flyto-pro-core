"""
Core Utilities - Shared patterns for flyto-pro

Provides:
- safe_access: Safe list/dict/attribute access to prevent IndexError/KeyError
- validators: Fluent validation for parameters
- container: Dependency Injection container
"""

from .container import (
    ServiceContainer,
    ServiceScope,
    container,
    register_core_services,
    get_qdrant_client,
    get_job_manager,
    get_contract_registry,
)

from .safe_access import (
    SafeAccessError,
    safe_first,
    safe_last,
    safe_index,
    safe_get,
    safe_split_first,
    safe_attr,
    safe_chain,
    safe_response_content,
    safe_result_data,
)

from .validators import (
    ValidationError,
    Validator,
    validate_not_none,
    validate_string,
    validate_int,
    validate_list,
    validate_dict,
    safe_int,
    safe_float,
)

__all__ = [
    # Container
    "ServiceContainer",
    "ServiceScope",
    "container",
    "register_core_services",
    "get_qdrant_client",
    "get_job_manager",
    "get_contract_registry",
    # Safe access
    "SafeAccessError",
    "safe_first",
    "safe_last",
    "safe_index",
    "safe_get",
    "safe_split_first",
    "safe_attr",
    "safe_chain",
    "safe_response_content",
    "safe_result_data",
    # Validators
    "ValidationError",
    "Validator",
    "validate_not_none",
    "validate_string",
    "validate_int",
    "validate_list",
    "validate_dict",
    "safe_int",
    "safe_float",
]
