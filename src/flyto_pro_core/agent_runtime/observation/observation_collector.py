"""
Observation Collector - Collects structured world state.

This is a pro module that can be registered and used in workflows.
"""

import hashlib
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .observation_packet import (
    BrowserObservation,
    DatabaseObservation,
    FileInfo,
    FileSystemObservation,
    ModuleIO,
    NetworkObservation,
    ObservationPacket,
    RequestInfo,
    ResponseInfo,
    RuntimeObservation,
    StepTrace,
    TableSnapshot,
)

logger = logging.getLogger(__name__)


class ObservationCollector:
    """
    Collects observations from various sources.

    This is the Agent's "eyes" - it sees the world and reports back
    in structured, machine-readable format.
    """

    def __init__(self):
        self._observations: List[ObservationPacket] = []
        self._step_traces: List[StepTrace] = []
        self._module_ios: List[ModuleIO] = []
        self._requests: List[RequestInfo] = []
        self._responses: List[ResponseInfo] = []

    def start_observation(self) -> str:
        """Start a new observation session."""
        observation_id = str(uuid.uuid4())[:8]
        logger.debug(f"Starting observation session: {observation_id}")
        return observation_id

    def collect_browser(
        self,
        url: str,
        title: str = "",
        dom_snapshot: Optional[Dict[str, Any]] = None,
        console_errors: Optional[List[str]] = None,
        console_warnings: Optional[List[str]] = None,
        screenshot_path: Optional[str] = None,
        cookies: Optional[Dict[str, str]] = None,
        local_storage: Optional[Dict[str, str]] = None,
    ) -> BrowserObservation:
        """Collect browser observation."""
        screenshot_hash = ""
        if screenshot_path:
            try:
                with open(screenshot_path, "rb") as f:
                    screenshot_hash = hashlib.sha256(f.read()).hexdigest()[:16]
            except Exception as e:
                logger.warning(f"Failed to hash screenshot: {e}")

        return BrowserObservation(
            url=url,
            title=title,
            dom_snapshot=dom_snapshot or {},
            console_errors=console_errors or [],
            console_warnings=console_warnings or [],
            screenshot_hash=screenshot_hash,
            screenshot_path=screenshot_path or "",
            cookies=cookies or {},
            local_storage=local_storage or {},
        )

    def collect_database(
        self,
        connection_status: str = "connected",
        tables: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> DatabaseObservation:
        """Collect database observation."""
        tables_snapshot = {}
        if tables:
            for name, data in tables.items():
                tables_snapshot[name] = TableSnapshot(
                    table_name=name,
                    row_count=data.get("row_count", 0),
                    checksum=data.get("checksum", ""),
                    sample_rows=data.get("sample_rows", []),
                    key_queries=data.get("key_queries", {}),
                )

        return DatabaseObservation(
            connection_status=connection_status,
            tables_snapshot=tables_snapshot,
        )

    def collect_filesystem(
        self,
        files_created: Optional[List[Dict[str, Any]]] = None,
        files_modified: Optional[List[Dict[str, Any]]] = None,
        files_deleted: Optional[List[str]] = None,
    ) -> FileSystemObservation:
        """Collect filesystem observation."""
        return FileSystemObservation(
            files_created=[
                FileInfo(
                    path=f.get("path", ""),
                    size=f.get("size", 0),
                    hash=f.get("hash", ""),
                    exists=f.get("exists", True),
                    content_preview=f.get("content_preview"),
                )
                for f in (files_created or [])
            ],
            files_modified=[
                FileInfo(
                    path=f.get("path", ""),
                    size=f.get("size", 0),
                    hash=f.get("hash", ""),
                    exists=f.get("exists", True),
                    content_preview=f.get("content_preview"),
                )
                for f in (files_modified or [])
            ],
            files_deleted=files_deleted or [],
        )

    def record_step_start(
        self,
        step_id: str,
        module_id: str,
    ) -> None:
        """Record step start."""
        trace = StepTrace(
            step_id=step_id,
            module_id=module_id,
            started_at=datetime.utcnow().isoformat(),
            ended_at="",
            status="running",
        )
        self._step_traces.append(trace)

    def record_step_end(
        self,
        step_id: str,
        status: str = "completed",
        error: Optional[str] = None,
    ) -> None:
        """Record step end."""
        for trace in self._step_traces:
            if trace.step_id == step_id:
                trace.ended_at = datetime.utcnow().isoformat()
                trace.status = status
                trace.error = error
                break

    def record_module_io(
        self,
        module_id: str,
        step_id: str,
        input_params: Dict[str, Any],
        output_result: Dict[str, Any],
        duration_ms: int = 0,
    ) -> None:
        """Record module input/output."""
        self._module_ios.append(
            ModuleIO(
                module_id=module_id,
                step_id=step_id,
                input_params=input_params,
                output_result=output_result,
                duration_ms=duration_ms,
            )
        )

    def record_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body_preview: Optional[str] = None,
    ) -> None:
        """Record HTTP request."""
        self._requests.append(
            RequestInfo(
                method=method,
                url=url,
                headers=headers or {},
                body_preview=body_preview,
                timestamp=datetime.utcnow().isoformat(),
            )
        )

    def record_response(
        self,
        status_code: int,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body_preview: Optional[str] = None,
        duration_ms: int = 0,
    ) -> None:
        """Record HTTP response."""
        self._responses.append(
            ResponseInfo(
                status_code=status_code,
                url=url,
                headers=headers or {},
                body_preview=body_preview,
                duration_ms=duration_ms,
            )
        )

    def collect_runtime(
        self,
        error_stacks: Optional[List[str]] = None,
        execution_time_ms: int = 0,
    ) -> RuntimeObservation:
        """Collect runtime observation."""
        return RuntimeObservation(
            step_traces=list(self._step_traces),
            module_ios=list(self._module_ios),
            error_stacks=error_stacks or [],
            execution_time_ms=execution_time_ms,
        )

    def collect_network(
        self,
        failed_requests: Optional[List[str]] = None,
    ) -> NetworkObservation:
        """Collect network observation."""
        return NetworkObservation(
            requests_made=list(self._requests),
            responses_received=list(self._responses),
            failed_requests=failed_requests or [],
        )

    def build_packet(
        self,
        observation_id: Optional[str] = None,
        browser: Optional[BrowserObservation] = None,
        database: Optional[DatabaseObservation] = None,
        filesystem: Optional[FileSystemObservation] = None,
        include_runtime: bool = True,
        include_network: bool = True,
        error_stacks: Optional[List[str]] = None,
        execution_time_ms: int = 0,
    ) -> ObservationPacket:
        """Build a complete observation packet."""
        return ObservationPacket(
            observation_id=observation_id or str(uuid.uuid4())[:8],
            timestamp=datetime.utcnow().isoformat(),
            browser=browser,
            database=database,
            filesystem=filesystem,
            network=self.collect_network() if include_network else None,
            runtime=(
                self.collect_runtime(error_stacks, execution_time_ms)
                if include_runtime
                else None
            ),
        )

    def reset(self) -> None:
        """Reset all collected data."""
        self._observations = []
        self._step_traces = []
        self._module_ios = []
        self._requests = []
        self._responses = []

    def get_last_observation(self) -> Optional[ObservationPacket]:
        """Get the last observation."""
        return self._observations[-1] if self._observations else None


# Singleton instance
_collector_instance: Optional[ObservationCollector] = None


def get_observation_collector() -> ObservationCollector:
    """Get the singleton observation collector."""
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = ObservationCollector()
    return _collector_instance
