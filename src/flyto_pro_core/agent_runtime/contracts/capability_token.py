"""
Capability Token - Permission boundary for agent actions.

This is the ONLY security mechanism. Without it, even the best verification
can be bypassed by "help me delete all data".
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from .contract_meta import ContractMeta


class CapabilityScope(Enum):
    """Capability scope definitions."""

    # Browser
    BROWSER_READ = "browser.read"  # Screenshots, DOM reading
    BROWSER_WRITE = "browser.write"  # Click, type, interact
    BROWSER_NAVIGATE = "browser.navigate"  # Change URL

    # Database
    DB_READ = "db.read"  # SELECT
    DB_WRITE = "db.write"  # INSERT, UPDATE
    DB_DELETE = "db.delete"  # DELETE, DROP (dangerous)

    # File System
    FS_READ = "fs.read"
    FS_WRITE = "fs.write"
    FS_DELETE = "fs.delete"

    # Network
    NET_INTERNAL = "net.internal"  # Local network
    NET_EXTERNAL = "net.external"  # Internet

    # High Risk
    PAYMENT = "payment"  # Payment operations
    EMAIL = "email"  # Send emails
    DEPLOY = "deploy"  # Production deployment
    ADMIN = "admin"  # Admin operations

    # Code Execution
    SHELL = "shell"  # Shell commands
    CODE_PYTHON = "code.python"  # Python execution
    CODE_JS = "code.js"  # JavaScript execution


# Scope hierarchy (parent includes children)
SCOPE_HIERARCHY = {
    "browser.*": [
        CapabilityScope.BROWSER_READ,
        CapabilityScope.BROWSER_WRITE,
        CapabilityScope.BROWSER_NAVIGATE,
    ],
    "db.*": [
        CapabilityScope.DB_READ,
        CapabilityScope.DB_WRITE,
        CapabilityScope.DB_DELETE,
    ],
    "fs.*": [
        CapabilityScope.FS_READ,
        CapabilityScope.FS_WRITE,
        CapabilityScope.FS_DELETE,
    ],
    "net.*": [
        CapabilityScope.NET_INTERNAL,
        CapabilityScope.NET_EXTERNAL,
    ],
    "code.*": [
        CapabilityScope.SHELL,
        CapabilityScope.CODE_PYTHON,
        CapabilityScope.CODE_JS,
    ],
}

# Module to required scopes mapping
MODULE_CAPABILITY_REQUIREMENTS: Dict[str, List[str]] = {
    "browser.screenshot": ["browser.read"],
    "browser.click": ["browser.write"],
    "browser.type": ["browser.write"],
    "browser.goto": ["browser.navigate"],
    "http.get": ["net.external"],
    "http.post": ["net.external"],
    "file.read": ["fs.read"],
    "file.write": ["fs.write"],
    "file.delete": ["fs.delete"],
    "db.query": ["db.read"],
    "db.insert": ["db.write"],
    "db.delete": ["db.delete"],
    "shell.exec": ["shell"],
    "code.python": ["code.python"],
}


@dataclass
class CapabilityToken:
    """
    Capability token for agent permissions.

    Agent can only execute within token scope.
    """

    # Metadata
    meta: ContractMeta = field(
        default_factory=lambda: ContractMeta(
            contract_name="CapabilityToken",
            version="1.0.0",
            compatible_with=["^1.0"],
        )
    )

    # Identity
    token_id: str = ""
    issued_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: str = ""
    issued_by: str = ""  # "user", "admin", "policy"

    # Scopes
    scopes: List[str] = field(default_factory=list)

    # Limits
    rate_limit: Optional[int] = None  # Max calls per minute
    cost_limit: Optional[float] = None  # Max cost in USD

    # Usage tracking
    usage_count: int = 0
    usage_cost: float = 0.0

    def __post_init__(self):
        if not self.expires_at:
            # Default 1 hour expiry
            expiry = datetime.utcnow() + timedelta(hours=1)
            self.expires_at = expiry.isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "meta": self.meta.to_dict(),
            "token_id": self.token_id,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "issued_by": self.issued_by,
            "scopes": self.scopes,
            "rate_limit": self.rate_limit,
            "cost_limit": self.cost_limit,
            "usage_count": self.usage_count,
            "usage_cost": self.usage_cost,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CapabilityToken":
        """Create from dictionary."""
        return cls(
            meta=ContractMeta.from_dict(data.get("meta", {})),
            token_id=data.get("token_id", ""),
            issued_at=data.get("issued_at", ""),
            expires_at=data.get("expires_at", ""),
            issued_by=data.get("issued_by", ""),
            scopes=data.get("scopes", []),
            rate_limit=data.get("rate_limit"),
            cost_limit=data.get("cost_limit"),
            usage_count=data.get("usage_count", 0),
            usage_cost=data.get("usage_cost", 0.0),
        )

    def is_expired(self) -> bool:
        """Check if token has expired."""
        try:
            expiry = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            return datetime.utcnow() > expiry.replace(tzinfo=None)
        except (ValueError, AttributeError):
            return True

    def has_scope(self, scope: str) -> bool:
        """Check if token has a specific scope."""
        if scope in self.scopes:
            return True

        # Check wildcard scopes
        for s in self.scopes:
            if s.endswith(".*"):
                prefix = s[:-2]
                if scope.startswith(prefix):
                    return True

        return False

    def get_all_scopes(self) -> Set[str]:
        """Get all scopes including expanded wildcards."""
        result = set(self.scopes)

        for scope in self.scopes:
            if scope in SCOPE_HIERARCHY:
                for cap in SCOPE_HIERARCHY[scope]:
                    result.add(cap.value)

        return result


class CapabilityGuard:
    """
    Kernel-level capability guard.

    Checks permissions before any module execution.
    """

    def __init__(self, token: CapabilityToken):
        self.token = token
        self._call_count = 0
        self._last_minute = datetime.utcnow().replace(second=0, microsecond=0)

    def can_execute(
        self,
        module_id: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        """
        Check if module can be executed.

        Returns:
            Tuple of (allowed, reason)
        """
        # Check expiry
        if self.token.is_expired():
            return False, "Token expired"

        # Check rate limit
        if self.token.rate_limit:
            current_minute = datetime.utcnow().replace(second=0, microsecond=0)
            if current_minute == self._last_minute:
                if self._call_count >= self.token.rate_limit:
                    return False, f"Rate limit exceeded ({self.token.rate_limit}/min)"
            else:
                self._last_minute = current_minute
                self._call_count = 0

        # Check cost limit
        if self.token.cost_limit:
            if self.token.usage_cost >= self.token.cost_limit:
                return False, f"Cost limit exceeded (${self.token.cost_limit})"

        # Get required scopes for module
        required_scopes = self._get_required_scopes(module_id, params)

        # Check each required scope
        for scope in required_scopes:
            if not self.token.has_scope(scope):
                return False, f"Missing capability: {scope}"

        return True, "Allowed"

    def _get_required_scopes(
        self,
        module_id: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Get required scopes for a module."""
        # Check predefined mappings
        if module_id in MODULE_CAPABILITY_REQUIREMENTS:
            return MODULE_CAPABILITY_REQUIREMENTS[module_id]

        # Infer from module_id pattern
        scopes = []
        parts = module_id.split(".")

        if len(parts) >= 2:
            category = parts[0]
            action = parts[1] if len(parts) > 1 else ""

            if category == "browser":
                if action in ("screenshot", "get_dom", "get_text"):
                    scopes.append("browser.read")
                elif action in ("click", "type", "select"):
                    scopes.append("browser.write")
                elif action in ("goto", "navigate", "open"):
                    scopes.append("browser.navigate")
                else:
                    scopes.append("browser.read")  # Default to read

            elif category == "http":
                scopes.append("net.external")

            elif category == "file":
                if action in ("read", "exists", "list"):
                    scopes.append("fs.read")
                elif action in ("write", "create", "copy"):
                    scopes.append("fs.write")
                elif action in ("delete", "remove"):
                    scopes.append("fs.delete")

            elif category == "db":
                if action in ("query", "select", "read"):
                    scopes.append("db.read")
                elif action in ("insert", "update", "write"):
                    scopes.append("db.write")
                elif action in ("delete", "drop", "truncate"):
                    scopes.append("db.delete")

            elif category == "shell":
                scopes.append("shell")

        return scopes

    def check_before_plan(self, plan: Any) -> List[str]:
        """
        Check plan before execution.

        Returns list of missing capabilities.
        """
        missing = []

        # Check required capabilities from plan
        if hasattr(plan, "required_capabilities"):
            for cap in plan.required_capabilities:
                if not self.token.has_scope(cap):
                    missing.append(cap)

        return missing

    def record_usage(self, cost: float = 0.0) -> None:
        """Record usage after successful execution."""
        self._call_count += 1
        self.token.usage_count += 1
        self.token.usage_cost += cost

    def get_status(self) -> Dict[str, Any]:
        """Get current guard status."""
        return {
            "token_id": self.token.token_id,
            "is_expired": self.token.is_expired(),
            "scopes": list(self.token.get_all_scopes()),
            "usage_count": self.token.usage_count,
            "usage_cost": self.token.usage_cost,
            "rate_limit": self.token.rate_limit,
            "cost_limit": self.token.cost_limit,
        }


class CapabilityTokenBuilder:
    """Builder for creating capability tokens."""

    @staticmethod
    def for_readonly(
        token_id: str,
        issued_by: str = "policy",
        expires_in_hours: int = 1,
    ) -> CapabilityToken:
        """Create a read-only token."""
        expiry = datetime.utcnow() + timedelta(hours=expires_in_hours)
        return CapabilityToken(
            token_id=token_id,
            issued_by=issued_by,
            expires_at=expiry.isoformat(),
            scopes=[
                "browser.read",
                "fs.read",
                "db.read",
                "net.external",
            ],
        )

    @staticmethod
    def for_standard(
        token_id: str,
        issued_by: str = "user",
        expires_in_hours: int = 4,
    ) -> CapabilityToken:
        """Create a standard token with common capabilities."""
        expiry = datetime.utcnow() + timedelta(hours=expires_in_hours)
        return CapabilityToken(
            token_id=token_id,
            issued_by=issued_by,
            expires_at=expiry.isoformat(),
            scopes=[
                "browser.*",
                "fs.read",
                "fs.write",
                "db.read",
                "db.write",
                "net.external",
            ],
        )

    @staticmethod
    def for_admin(
        token_id: str,
        issued_by: str = "admin",
        expires_in_hours: int = 1,
    ) -> CapabilityToken:
        """Create an admin token with all capabilities."""
        expiry = datetime.utcnow() + timedelta(hours=expires_in_hours)
        return CapabilityToken(
            token_id=token_id,
            issued_by=issued_by,
            expires_at=expiry.isoformat(),
            scopes=[
                "browser.*",
                "db.*",
                "fs.*",
                "net.*",
                "code.*",
                "shell",
                "admin",
            ],
            rate_limit=100,
            cost_limit=100.0,
        )


# JSON Schema for validation
CAPABILITY_TOKEN_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "token_id": {"type": "string", "minLength": 1},
        "issued_at": {"type": "string"},
        "expires_at": {"type": "string"},
        "issued_by": {"enum": ["user", "admin", "policy", "system"]},
        "scopes": {
            "type": "array",
            "items": {"type": "string"},
        },
        "rate_limit": {"type": ["integer", "null"], "minimum": 1},
        "cost_limit": {"type": ["number", "null"], "minimum": 0},
    },
    "required": ["token_id", "scopes"],
}
