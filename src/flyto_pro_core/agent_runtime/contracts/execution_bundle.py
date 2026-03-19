"""
Execution Bundle - Reproducible execution package.

Same bundle should produce same result (or explainable differences).
"""

import hashlib
import platform
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .contract_meta import ContractMeta


@dataclass
class EnvironmentFingerprint:
    """
    Environment fingerprint for reproducibility.

    Used to determine if an execution can be replayed.
    """

    os: str = ""  # e.g. "macos-14.0"
    browser: str = ""  # e.g. "chrome-120"
    viewport: str = ""  # e.g. "1920x1080"
    locale: str = ""  # e.g. "zh-TW"
    timezone: str = ""  # e.g. "Asia/Taipei"
    network_mode: str = "online"  # online, offline, throttled

    # External dependency versions
    external_deps: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self.os:
            self.os = f"{platform.system()}-{platform.release()}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "os": self.os,
            "browser": self.browser,
            "viewport": self.viewport,
            "locale": self.locale,
            "timezone": self.timezone,
            "network_mode": self.network_mode,
            "external_deps": self.external_deps,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnvironmentFingerprint":
        """Create from dictionary."""
        return cls(
            os=data.get("os", ""),
            browser=data.get("browser", ""),
            viewport=data.get("viewport", ""),
            locale=data.get("locale", ""),
            timezone=data.get("timezone", ""),
            network_mode=data.get("network_mode", "online"),
            external_deps=data.get("external_deps", {}),
        )

    def is_compatible(self, other: "EnvironmentFingerprint") -> bool:
        """
        Check if two environments are compatible for replay.

        Compatible means:
        - Same OS family
        - Same browser (if browser-based)
        - Same network mode
        """
        # OS family check (not exact version)
        self_os_family = self.os.split("-")[0].lower()
        other_os_family = other.os.split("-")[0].lower()
        if self_os_family != other_os_family:
            return False

        # Browser check (if both have browser)
        if self.browser and other.browser:
            self_browser = self.browser.split("-")[0].lower()
            other_browser = other.browser.split("-")[0].lower()
            if self_browser != other_browser:
                return False

        # Network mode must match
        if self.network_mode != other.network_mode:
            return False

        return True

    def get_hash(self) -> str:
        """Get hash of environment fingerprint."""
        content = f"{self.os}:{self.browser}:{self.viewport}:{self.locale}:{self.timezone}:{self.network_mode}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class ExecutionBundle:
    """
    Reproducible execution package.

    Contains everything needed to replay an execution.
    """

    # Metadata
    meta: ContractMeta = field(
        default_factory=lambda: ContractMeta(
            contract_name="ExecutionBundle",
            version="1.0.0",
            compatible_with=["^1.0"],
        )
    )

    # Identity
    bundle_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Workflow definition
    workflow_yaml: str = ""
    workflow_version: str = ""

    # Module versions
    module_versions: Dict[str, str] = field(default_factory=dict)

    # Environment
    environment: EnvironmentFingerprint = field(default_factory=EnvironmentFingerprint)

    # Random seeds (if any)
    seeds: Dict[str, int] = field(default_factory=dict)

    # Evidence pointers
    evidence_pointers: List[str] = field(default_factory=list)

    # Verifier configuration
    verifier_config: Dict[str, Any] = field(default_factory=dict)

    # Execution result summary
    result_summary: Dict[str, Any] = field(default_factory=dict)

    # Variables used
    variables: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "meta": self.meta.to_dict(),
            "bundle_id": self.bundle_id,
            "created_at": self.created_at,
            "workflow_yaml": self.workflow_yaml,
            "workflow_version": self.workflow_version,
            "module_versions": self.module_versions,
            "environment": self.environment.to_dict(),
            "seeds": self.seeds,
            "evidence_pointers": self.evidence_pointers,
            "verifier_config": self.verifier_config,
            "result_summary": self.result_summary,
            "variables": self.variables,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionBundle":
        """Create from dictionary."""
        return cls(
            meta=ContractMeta.from_dict(data.get("meta", {})),
            bundle_id=data.get("bundle_id", ""),
            created_at=data.get("created_at", ""),
            workflow_yaml=data.get("workflow_yaml", ""),
            workflow_version=data.get("workflow_version", ""),
            module_versions=data.get("module_versions", {}),
            environment=EnvironmentFingerprint.from_dict(data.get("environment", {})),
            seeds=data.get("seeds", {}),
            evidence_pointers=data.get("evidence_pointers", []),
            verifier_config=data.get("verifier_config", {}),
            result_summary=data.get("result_summary", {}),
            variables=data.get("variables", {}),
        )

    def can_replay(self, current_env: EnvironmentFingerprint) -> tuple[bool, str]:
        """
        Check if this bundle can be replayed in current environment.

        Returns:
            Tuple of (can_replay, reason)
        """
        if not self.environment.is_compatible(current_env):
            return False, "Environment not compatible"

        return True, "Compatible"

    def get_hash(self) -> str:
        """Get hash of execution bundle for comparison."""
        content = f"{self.workflow_yaml}:{self.workflow_version}:{self.environment.get_hash()}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def validate(self) -> List[str]:
        """Validate the execution bundle."""
        errors = []

        if not self.bundle_id:
            errors.append("bundle_id is required")

        if not self.workflow_yaml:
            errors.append("workflow_yaml is required")

        return errors


# JSON Schema for validation
EXECUTION_BUNDLE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "bundle_id": {"type": "string", "minLength": 1},
        "created_at": {"type": "string"},
        "workflow_yaml": {"type": "string"},
        "workflow_version": {"type": "string"},
        "module_versions": {
            "type": "object",
            "additionalProperties": {"type": "string"},
        },
        "environment": {
            "type": "object",
            "properties": {
                "os": {"type": "string"},
                "browser": {"type": "string"},
                "viewport": {"type": "string"},
                "locale": {"type": "string"},
                "timezone": {"type": "string"},
                "network_mode": {"enum": ["online", "offline", "throttled"]},
                "external_deps": {"type": "object"},
            },
        },
        "seeds": {
            "type": "object",
            "additionalProperties": {"type": "integer"},
        },
        "evidence_pointers": {
            "type": "array",
            "items": {"type": "string"},
        },
        "verifier_config": {"type": "object"},
        "result_summary": {"type": "object"},
        "variables": {"type": "object"},
    },
    "required": ["bundle_id", "workflow_yaml"],
}
