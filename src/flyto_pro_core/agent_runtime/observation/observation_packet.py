"""
Observation Packet - Structured world state.

This is what the Agent "sees" - not natural language, but structured data.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..contracts.contract_meta import ContractMeta


@dataclass
class TableSnapshot:
    """Database table snapshot."""

    table_name: str
    row_count: int
    checksum: str = ""  # Data fingerprint
    sample_rows: List[Dict[str, Any]] = field(default_factory=list)
    key_queries: Dict[str, Any] = field(default_factory=dict)  # Predefined query results

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_name": self.table_name,
            "row_count": self.row_count,
            "checksum": self.checksum,
            "sample_rows": self.sample_rows,
            "key_queries": self.key_queries,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TableSnapshot":
        return cls(
            table_name=data.get("table_name", ""),
            row_count=data.get("row_count", 0),
            checksum=data.get("checksum", ""),
            sample_rows=data.get("sample_rows", []),
            key_queries=data.get("key_queries", {}),
        )


@dataclass
class FileInfo:
    """File information."""

    path: str
    size: int = 0
    hash: str = ""  # SHA256
    exists: bool = True
    content_preview: Optional[str] = None  # First 500 chars

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "size": self.size,
            "hash": self.hash,
            "exists": self.exists,
            "content_preview": self.content_preview,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileInfo":
        return cls(
            path=data.get("path", ""),
            size=data.get("size", 0),
            hash=data.get("hash", ""),
            exists=data.get("exists", True),
            content_preview=data.get("content_preview"),
        )


@dataclass
class RequestInfo:
    """HTTP request information."""

    method: str
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    body_preview: Optional[str] = None
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "url": self.url,
            "headers": self.headers,
            "body_preview": self.body_preview,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RequestInfo":
        return cls(
            method=data.get("method", ""),
            url=data.get("url", ""),
            headers=data.get("headers", {}),
            body_preview=data.get("body_preview"),
            timestamp=data.get("timestamp", ""),
        )


@dataclass
class ResponseInfo:
    """HTTP response information."""

    status_code: int
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    body_preview: Optional[str] = None
    duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status_code": self.status_code,
            "url": self.url,
            "headers": self.headers,
            "body_preview": self.body_preview,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResponseInfo":
        return cls(
            status_code=data.get("status_code", 0),
            url=data.get("url", ""),
            headers=data.get("headers", {}),
            body_preview=data.get("body_preview"),
            duration_ms=data.get("duration_ms", 0),
        )


@dataclass
class StepTrace:
    """Execution step trace."""

    step_id: str
    module_id: str
    started_at: str
    ended_at: str
    status: str  # running, completed, failed
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "module_id": self.module_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "status": self.status,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StepTrace":
        return cls(
            step_id=data.get("step_id", ""),
            module_id=data.get("module_id", ""),
            started_at=data.get("started_at", ""),
            ended_at=data.get("ended_at", ""),
            status=data.get("status", ""),
            error=data.get("error"),
        )


@dataclass
class ModuleIO:
    """Module input/output record."""

    module_id: str
    step_id: str
    input_params: Dict[str, Any] = field(default_factory=dict)
    output_result: Dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module_id": self.module_id,
            "step_id": self.step_id,
            "input_params": self.input_params,
            "output_result": self.output_result,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModuleIO":
        return cls(
            module_id=data.get("module_id", ""),
            step_id=data.get("step_id", ""),
            input_params=data.get("input_params", {}),
            output_result=data.get("output_result", {}),
            duration_ms=data.get("duration_ms", 0),
        )


@dataclass
class BrowserObservation:
    """Browser state observation."""

    url: str = ""
    title: str = ""
    dom_snapshot: Dict[str, Any] = field(default_factory=dict)  # Key selectors
    console_errors: List[str] = field(default_factory=list)
    console_warnings: List[str] = field(default_factory=list)
    network_failed: List[str] = field(default_factory=list)
    screenshot_hash: str = ""
    screenshot_path: str = ""
    cookies: Dict[str, str] = field(default_factory=dict)
    local_storage: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "dom_snapshot": self.dom_snapshot,
            "console_errors": self.console_errors,
            "console_warnings": self.console_warnings,
            "network_failed": self.network_failed,
            "screenshot_hash": self.screenshot_hash,
            "screenshot_path": self.screenshot_path,
            "cookies": self.cookies,
            "local_storage": self.local_storage,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BrowserObservation":
        return cls(
            url=data.get("url", ""),
            title=data.get("title", ""),
            dom_snapshot=data.get("dom_snapshot", {}),
            console_errors=data.get("console_errors", []),
            console_warnings=data.get("console_warnings", []),
            network_failed=data.get("network_failed", []),
            screenshot_hash=data.get("screenshot_hash", ""),
            screenshot_path=data.get("screenshot_path", ""),
            cookies=data.get("cookies", {}),
            local_storage=data.get("local_storage", {}),
        )

    def has_errors(self) -> bool:
        """Check if there are any console errors."""
        return len(self.console_errors) > 0


@dataclass
class DatabaseObservation:
    """Database state observation."""

    connection_status: str = "connected"
    tables_snapshot: Dict[str, TableSnapshot] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connection_status": self.connection_status,
            "tables_snapshot": {
                k: v.to_dict() for k, v in self.tables_snapshot.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatabaseObservation":
        return cls(
            connection_status=data.get("connection_status", "connected"),
            tables_snapshot={
                k: TableSnapshot.from_dict(v)
                for k, v in data.get("tables_snapshot", {}).items()
            },
        )


@dataclass
class FileSystemObservation:
    """File system state observation."""

    files_created: List[FileInfo] = field(default_factory=list)
    files_modified: List[FileInfo] = field(default_factory=list)
    files_deleted: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "files_created": [f.to_dict() for f in self.files_created],
            "files_modified": [f.to_dict() for f in self.files_modified],
            "files_deleted": self.files_deleted,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileSystemObservation":
        return cls(
            files_created=[
                FileInfo.from_dict(f) for f in data.get("files_created", [])
            ],
            files_modified=[
                FileInfo.from_dict(f) for f in data.get("files_modified", [])
            ],
            files_deleted=data.get("files_deleted", []),
        )


@dataclass
class NetworkObservation:
    """Network state observation."""

    requests_made: List[RequestInfo] = field(default_factory=list)
    responses_received: List[ResponseInfo] = field(default_factory=list)
    failed_requests: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requests_made": [r.to_dict() for r in self.requests_made],
            "responses_received": [r.to_dict() for r in self.responses_received],
            "failed_requests": self.failed_requests,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NetworkObservation":
        return cls(
            requests_made=[
                RequestInfo.from_dict(r) for r in data.get("requests_made", [])
            ],
            responses_received=[
                ResponseInfo.from_dict(r) for r in data.get("responses_received", [])
            ],
            failed_requests=data.get("failed_requests", []),
        )


@dataclass
class RuntimeObservation:
    """Runtime execution observation."""

    step_traces: List[StepTrace] = field(default_factory=list)
    module_ios: List[ModuleIO] = field(default_factory=list)
    error_stacks: List[str] = field(default_factory=list)
    execution_time_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_traces": [s.to_dict() for s in self.step_traces],
            "module_ios": [m.to_dict() for m in self.module_ios],
            "error_stacks": self.error_stacks,
            "execution_time_ms": self.execution_time_ms,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuntimeObservation":
        return cls(
            step_traces=[
                StepTrace.from_dict(s) for s in data.get("step_traces", [])
            ],
            module_ios=[ModuleIO.from_dict(m) for m in data.get("module_ios", [])],
            error_stacks=data.get("error_stacks", []),
            execution_time_ms=data.get("execution_time_ms", 0),
        )


@dataclass
class ObservationPacket:
    """
    Structured world state - Agent's eyes.

    This is NOT natural language description.
    It's machine-readable, structured data for deterministic verification.
    """

    # Metadata
    meta: ContractMeta = field(
        default_factory=lambda: ContractMeta(
            contract_name="ObservationPacket",
            version="1.0.0",
            compatible_with=["^1.0"],
        )
    )

    # Identity
    observation_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Observations
    browser: Optional[BrowserObservation] = None
    database: Optional[DatabaseObservation] = None
    filesystem: Optional[FileSystemObservation] = None
    network: Optional[NetworkObservation] = None
    runtime: Optional[RuntimeObservation] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "meta": self.meta.to_dict(),
            "observation_id": self.observation_id,
            "timestamp": self.timestamp,
            "browser": self.browser.to_dict() if self.browser else None,
            "database": self.database.to_dict() if self.database else None,
            "filesystem": self.filesystem.to_dict() if self.filesystem else None,
            "network": self.network.to_dict() if self.network else None,
            "runtime": self.runtime.to_dict() if self.runtime else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ObservationPacket":
        """Create from dictionary."""
        return cls(
            meta=ContractMeta.from_dict(data.get("meta", {})),
            observation_id=data.get("observation_id", ""),
            timestamp=data.get("timestamp", ""),
            browser=(
                BrowserObservation.from_dict(data["browser"])
                if data.get("browser")
                else None
            ),
            database=(
                DatabaseObservation.from_dict(data["database"])
                if data.get("database")
                else None
            ),
            filesystem=(
                FileSystemObservation.from_dict(data["filesystem"])
                if data.get("filesystem")
                else None
            ),
            network=(
                NetworkObservation.from_dict(data["network"])
                if data.get("network")
                else None
            ),
            runtime=(
                RuntimeObservation.from_dict(data["runtime"])
                if data.get("runtime")
                else None
            ),
        )

    def get_hash(self) -> str:
        """Get hash of observation for comparison."""
        import json

        content = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def has_errors(self) -> bool:
        """Check if any observation has errors."""
        if self.browser and self.browser.has_errors():
            return True
        if self.runtime and self.runtime.error_stacks:
            return True
        if self.network and self.network.failed_requests:
            return True
        return False

    def get_summary(self) -> Dict[str, Any]:
        """Get a compact summary of observations."""
        summary = {
            "observation_id": self.observation_id,
            "timestamp": self.timestamp,
            "has_errors": self.has_errors(),
        }

        if self.browser:
            summary["browser"] = {
                "url": self.browser.url,
                "console_errors": len(self.browser.console_errors),
                "has_screenshot": bool(self.browser.screenshot_path),
            }

        if self.database:
            summary["database"] = {
                "status": self.database.connection_status,
                "tables_observed": len(self.database.tables_snapshot),
            }

        if self.filesystem:
            summary["filesystem"] = {
                "files_created": len(self.filesystem.files_created),
                "files_modified": len(self.filesystem.files_modified),
                "files_deleted": len(self.filesystem.files_deleted),
            }

        if self.network:
            summary["network"] = {
                "requests": len(self.network.requests_made),
                "failed": len(self.network.failed_requests),
            }

        if self.runtime:
            summary["runtime"] = {
                "steps": len(self.runtime.step_traces),
                "errors": len(self.runtime.error_stacks),
                "execution_time_ms": self.runtime.execution_time_ms,
            }

        return summary


# JSON Schema for validation
OBSERVATION_PACKET_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "observation_id": {"type": "string"},
        "timestamp": {"type": "string"},
        "browser": {
            "type": ["object", "null"],
            "properties": {
                "url": {"type": "string"},
                "title": {"type": "string"},
                "console_errors": {"type": "array", "items": {"type": "string"}},
                "screenshot_hash": {"type": "string"},
            },
        },
        "database": {
            "type": ["object", "null"],
            "properties": {
                "connection_status": {"type": "string"},
                "tables_snapshot": {"type": "object"},
            },
        },
        "filesystem": {
            "type": ["object", "null"],
            "properties": {
                "files_created": {"type": "array"},
                "files_modified": {"type": "array"},
                "files_deleted": {"type": "array"},
            },
        },
        "network": {
            "type": ["object", "null"],
            "properties": {
                "requests_made": {"type": "array"},
                "failed_requests": {"type": "array"},
            },
        },
        "runtime": {
            "type": ["object", "null"],
            "properties": {
                "step_traces": {"type": "array"},
                "error_stacks": {"type": "array"},
                "execution_time_ms": {"type": "integer"},
            },
        },
    },
}
