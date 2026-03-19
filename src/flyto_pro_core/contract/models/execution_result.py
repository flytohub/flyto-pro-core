"""
Execution Result Models

Defines the contract for module execution results, including:
- Event-based routing (__event__)
- Scope injection (__scope__)
- Standard result format

This is the ONLY allowed format for module returns.
The Contract Engine uses these to determine next steps and scope injection.

Example:
    # Simple success
    return {
        "ok": True,
        "data": {"url": "https://...", "title": "Page Title"},
    }

    # Loop iteration
    return {
        "__event__": "iterate",
        "__scope__": {"loop.item": current_item, "loop.index": 0},
        "ok": True,
        "data": current_item,
    }

    # Loop completion
    return {
        "__event__": "done",
        "ok": True,
        "data": {"iterations": 10, "results": [...]},
    }

    # Branch decision
    return {
        "__event__": "true",  # or "false"
        "ok": True,
        "data": {"condition_value": True},
    }

    # Switch case
    return {
        "__event__": "case:premium",
        "ok": True,
        "data": {"matched_case": "premium"},
    }
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from datetime import datetime


class ExecutionEvent(str, Enum):
    """Standard execution events for routing."""

    # Control flow events
    ITERATE = "iterate"  # Loop continues with next item
    DONE = "done"  # Loop/process completed
    TRUE = "true"  # Condition is true
    FALSE = "false"  # Condition is false
    DEFAULT = "default"  # Switch default case
    NEXT = "next"  # Continue to next node
    SKIP = "skip"  # Skip current iteration
    BREAK = "break"  # Break from loop
    ERROR = "error"  # Error occurred

    @classmethod
    def case(cls, case_id: str) -> str:
        """Create a case event for switch statements."""
        return f"case:{case_id}"

    @classmethod
    def is_case(cls, event: str) -> bool:
        """Check if event is a case event."""
        return event.startswith("case:")

    @classmethod
    def get_case_id(cls, event: str) -> Optional[str]:
        """Extract case ID from case event."""
        if cls.is_case(event):
            return event[5:]  # Remove "case:" prefix
        return None


@dataclass
class ScopeData:
    """
    Scope data to be injected into child nodes.

    This is how loop items, error info, etc. become available
    to nodes within a control flow block.

    Attributes:
        variables: Key-value pairs for scope (e.g., {"loop.item": {...}})
        parent_scope: Reference to parent scope (for nested loops)
        node_id: Node that created this scope
        created_at: When scope was created
    """

    variables: Dict[str, Any] = field(default_factory=dict)
    parent_scope: Optional[ScopeData] = None
    node_id: Optional[str] = None
    created_at: Optional[str] = None

    def get(self, key: str, default: Any = None) -> Any:
        """Get a scope variable, checking parent scopes if not found."""
        if key in self.variables:
            return self.variables[key]
        if self.parent_scope:
            return self.parent_scope.get(key, default)
        return default

    def set(self, key: str, value: Any) -> None:
        """Set a scope variable."""
        self.variables[key] = value

    def merge(self, other: Dict[str, Any]) -> None:
        """Merge variables from another dict."""
        self.variables.update(other)

    def flatten(self) -> Dict[str, Any]:
        """Flatten scope including parent scopes."""
        result = {}
        if self.parent_scope:
            result.update(self.parent_scope.flatten())
        result.update(self.variables)
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variables": self.variables,
            "node_id": self.node_id,
            "created_at": self.created_at,
        }


@dataclass
class ExecutionResult:
    """
    Standard execution result format.

    All module executions must return this format (or dict convertible to it).

    Attributes:
        ok: Whether execution succeeded
        data: Result data
        error: Error message if failed
        error_code: Error code if failed
        event: Routing event (__event__)
        scope: Scope injection (__scope__)
        degraded: Whether result is degraded (circuit breaker fallback)
        metadata: Additional execution metadata
        duration_ms: Execution duration in milliseconds
    """

    ok: bool
    data: Any = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    event: Optional[str] = None
    scope: Optional[Dict[str, Any]] = None
    degraded: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[float] = None

    def get_routing_port(self) -> str:
        """
        Determine which output port to route to based on event.

        Returns:
            Port ID to route to
        """
        if not self.event:
            return "out"  # Default output port

        # Map events to ports
        event_port_map = {
            ExecutionEvent.ITERATE.value: "body",
            ExecutionEvent.DONE.value: "done",
            ExecutionEvent.TRUE.value: "true",
            ExecutionEvent.FALSE.value: "false",
            ExecutionEvent.DEFAULT.value: "default",
            ExecutionEvent.NEXT.value: "out",
            ExecutionEvent.ERROR.value: "catch",
        }

        # Check for case events
        if ExecutionEvent.is_case(self.event):
            return self.event  # e.g., "case:premium"

        return event_port_map.get(self.event, "out")

    def get_scope_data(self) -> Optional[ScopeData]:
        """Get scope data if present."""
        if self.scope:
            return ScopeData(variables=self.scope)
        return None

    def is_continue(self) -> bool:
        """Check if execution should continue (not error/break)."""
        return self.ok and self.event not in (
            ExecutionEvent.ERROR.value,
            ExecutionEvent.BREAK.value,
        )

    def is_iteration(self) -> bool:
        """Check if this is a loop iteration."""
        return self.event == ExecutionEvent.ITERATE.value

    def is_completion(self) -> bool:
        """Check if this is a completion event."""
        return self.event == ExecutionEvent.DONE.value

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "ok": self.ok,
            "data": self.data,
        }
        if self.error:
            result["error"] = self.error
        if self.error_code:
            result["error_code"] = self.error_code
        if self.event:
            result["__event__"] = self.event
        if self.scope:
            result["__scope__"] = self.scope
        if self.degraded:
            result["degraded"] = self.degraded
        if self.metadata:
            result["metadata"] = self.metadata
        if self.duration_ms:
            result["duration_ms"] = self.duration_ms
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExecutionResult:
        return cls(
            ok=data.get("ok", True),
            data=data.get("data"),
            error=data.get("error"),
            error_code=data.get("error_code"),
            event=data.get("__event__"),
            scope=data.get("__scope__"),
            degraded=data.get("degraded", False),
            metadata=data.get("metadata", {}),
            duration_ms=data.get("duration_ms"),
        )

    @classmethod
    def success(cls, data: Any = None, **kwargs) -> ExecutionResult:
        """Create a success result."""
        return cls(ok=True, data=data, **kwargs)

    @classmethod
    def failure(cls, error: str, error_code: Optional[str] = None, **kwargs) -> ExecutionResult:
        """Create a failure result."""
        return cls(ok=False, error=error, error_code=error_code, **kwargs)

    @classmethod
    def iterate(cls, item: Any, index: int, **kwargs) -> ExecutionResult:
        """Create a loop iteration result."""
        return cls(
            ok=True,
            data=item,
            event=ExecutionEvent.ITERATE.value,
            scope={"loop.item": item, "loop.index": index},
            **kwargs,
        )

    @classmethod
    def done(cls, data: Any = None, **kwargs) -> ExecutionResult:
        """Create a loop completion result."""
        return cls(ok=True, data=data, event=ExecutionEvent.DONE.value, **kwargs)

    @classmethod
    def branch(cls, condition: bool, data: Any = None, **kwargs) -> ExecutionResult:
        """Create a branching result."""
        return cls(
            ok=True,
            data=data,
            event=ExecutionEvent.TRUE.value if condition else ExecutionEvent.FALSE.value,
            **kwargs,
        )

    @classmethod
    def switch_case(cls, case_id: str, data: Any = None, **kwargs) -> ExecutionResult:
        """Create a switch case result."""
        return cls(
            ok=True,
            data=data,
            event=ExecutionEvent.case(case_id),
            **kwargs,
        )

    @classmethod
    def switch_default(cls, data: Any = None, **kwargs) -> ExecutionResult:
        """Create a switch default result."""
        return cls(
            ok=True,
            data=data,
            event=ExecutionEvent.DEFAULT.value,
            **kwargs,
        )


@dataclass
class ExecutionTrace:
    """
    Trace of a workflow execution for observability.

    Attributes:
        execution_id: Unique execution identifier
        workflow_id: Workflow being executed
        started_at: Execution start time
        completed_at: Execution end time
        status: Current status
        node_traces: Trace for each node
        total_duration_ms: Total execution time
        error: Error if failed
    """

    execution_id: str
    workflow_id: str
    started_at: str
    completed_at: Optional[str] = None
    status: str = "running"
    node_traces: List[Dict[str, Any]] = field(default_factory=list)
    total_duration_ms: Optional[float] = None
    error: Optional[str] = None

    def add_node_trace(
        self,
        node_id: str,
        module_id: str,
        started_at: str,
        completed_at: Optional[str] = None,
        status: str = "running",
        result: Optional[ExecutionResult] = None,
        duration_ms: Optional[float] = None,
    ) -> None:
        """Add a node execution trace."""
        self.node_traces.append({
            "node_id": node_id,
            "module_id": module_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "status": status,
            "result": result.to_dict() if result else None,
            "duration_ms": duration_ms,
        })

    def complete(self, status: str = "completed", error: Optional[str] = None) -> None:
        """Mark execution as complete."""
        self.completed_at = datetime.utcnow().isoformat()
        self.status = status
        self.error = error

        if self.node_traces:
            # Calculate total duration from first to last node
            try:
                first = datetime.fromisoformat(self.started_at)
                last = datetime.fromisoformat(self.completed_at)
                self.total_duration_ms = (last - first).total_seconds() * 1000
            except (ValueError, TypeError):
                pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "node_traces": self.node_traces,
            "total_duration_ms": self.total_duration_ms,
            "error": self.error,
        }
