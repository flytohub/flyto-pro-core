"""
Contract Meta - Version management for all contracts.

Without contract versioning, Agent will "die old" - unable to evolve.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ContractMeta:
    """
    Version metadata for all contracts.

    Every contract must carry this metadata for:
    - EMS fix targeting specific contract versions
    - ExecutionBundle replay with correct verifier
    - flyto-pro upgrades without breaking old projects
    """

    contract_name: str  # e.g. "PlanContract"
    version: str  # semver e.g. "1.0.0"
    compatible_with: List[str] = field(default_factory=list)  # e.g. ["^0.9", "^1.0"]
    checksum: str = ""  # schema hash
    generated_by: str = ""  # e.g. "flyto-pro@abc123"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def __post_init__(self):
        if not self.checksum:
            self.checksum = self._compute_checksum()

    def _compute_checksum(self) -> str:
        """Compute checksum from contract name and version."""
        content = f"{self.contract_name}:{self.version}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "contract_name": self.contract_name,
            "version": self.version,
            "compatible_with": self.compatible_with,
            "checksum": self.checksum,
            "generated_by": self.generated_by,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContractMeta":
        """Create from dictionary."""
        return cls(
            contract_name=data["contract_name"],
            version=data["version"],
            compatible_with=data.get("compatible_with", []),
            checksum=data.get("checksum", ""),
            generated_by=data.get("generated_by", ""),
            created_at=data.get("created_at", ""),
        )


def parse_semver(version: str) -> Tuple[int, int, int]:
    """Parse semantic version string to tuple."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        raise ValueError(f"Invalid semver: {version}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def matches_version_range(version: str, range_spec: str) -> bool:
    """
    Check if version matches a version range specification.

    Supports:
    - Exact: "1.0.0"
    - Caret: "^1.0.0" (compatible with 1.x.x)
    - Tilde: "~1.0.0" (compatible with 1.0.x)
    """
    try:
        v_major, v_minor, v_patch = parse_semver(version)

        if range_spec.startswith("^"):
            # Caret: compatible with same major version
            r_major, r_minor, r_patch = parse_semver(range_spec[1:])
            if r_major == 0:
                # For 0.x.x, caret means same minor
                return v_major == 0 and v_minor == r_minor and v_patch >= r_patch
            return v_major == r_major and (v_minor, v_patch) >= (r_minor, r_patch)

        elif range_spec.startswith("~"):
            # Tilde: compatible with same minor version
            r_major, r_minor, r_patch = parse_semver(range_spec[1:])
            return v_major == r_major and v_minor == r_minor and v_patch >= r_patch

        else:
            # Exact match
            r_major, r_minor, r_patch = parse_semver(range_spec)
            return (v_major, v_minor, v_patch) == (r_major, r_minor, r_patch)

    except ValueError:
        return False


def validate_contract_version(
    contract_meta: ContractMeta,
    runtime_version: str,
) -> Tuple[bool, str]:
    """
    Validate if a contract is compatible with the runtime version.

    Returns:
        Tuple of (is_compatible, reason)
    """
    # Check if runtime version is in compatible_with list
    for range_spec in contract_meta.compatible_with:
        if matches_version_range(runtime_version, range_spec):
            return True, f"Compatible via {range_spec}"

    # Check if versions match exactly
    if contract_meta.version == runtime_version:
        return True, "Exact version match"

    # Check if same major version (loose compatibility)
    try:
        c_major, _, _ = parse_semver(contract_meta.version)
        r_major, _, _ = parse_semver(runtime_version)
        if c_major == r_major:
            return True, f"Same major version {c_major}"
    except ValueError:
        pass

    return False, f"Version mismatch: contract={contract_meta.version}, runtime={runtime_version}"


class ContractRegistry:
    """
    Registry for contract schemas and migrations.
    """

    def __init__(self):
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._migrations: Dict[str, List[callable]] = {}

    def register_schema(
        self,
        contract_name: str,
        version: str,
        schema: Dict[str, Any],
    ) -> None:
        """Register a contract schema."""
        key = f"{contract_name}:{version}"
        self._schemas[key] = schema

    def get_schema(
        self,
        contract_name: str,
        version: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a contract schema."""
        key = f"{contract_name}:{version}"
        return self._schemas.get(key)

    def register_migration(
        self,
        contract_name: str,
        from_version: str,
        to_version: str,
        migration_fn: callable,
    ) -> None:
        """Register a migration function."""
        key = f"{contract_name}:{from_version}:{to_version}"
        if key not in self._migrations:
            self._migrations[key] = []
        self._migrations[key].append(migration_fn)

    def migrate(
        self,
        contract: Any,
        target_version: str,
    ) -> Any:
        """
        Migrate a contract to a target version.

        Raises:
            ValueError: If no migration path exists
        """
        if not hasattr(contract, "meta"):
            raise ValueError("Contract must have 'meta' attribute")

        current_version = contract.meta.version
        if current_version == target_version:
            return contract

        key = f"{contract.meta.contract_name}:{current_version}:{target_version}"
        migrations = self._migrations.get(key, [])

        if not migrations:
            raise ValueError(
                f"No migration path from {current_version} to {target_version}"
            )

        result = contract
        for migration_fn in migrations:
            result = migration_fn(result)

        return result


# Global registry instance
contract_registry = ContractRegistry()
