"""
Observation Adapter - Captures observations from various sources.

Provides helpers to capture observations from:
- Browser automation (Playwright, Selenium)
- Database connections
- File system operations
- Network requests
"""

import hashlib
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..observation import (
    ObservationPacket,
    BrowserObservation,
    DatabaseObservation,
    FileSystemObservation,
    NetworkObservation,
    RuntimeObservation,
    ObservationCollector,
    TableSnapshot,
    FileInfo,
    RequestInfo,
    ResponseInfo,
    StepTrace,
)

logger = logging.getLogger(__name__)


@dataclass
class PlaywrightPageInfo:
    """Information from Playwright page."""

    url: str = ""
    title: str = ""
    screenshot_path: str = ""
    console_errors: List[str] = None
    console_warnings: List[str] = None
    network_failed: List[str] = None


async def capture_browser_observation(
    page=None,
    screenshot_path: str = "",
    dom_selectors: Optional[List[str]] = None,
) -> BrowserObservation:
    """
    Capture browser observation from Playwright page.

    Args:
        page: Playwright page object
        screenshot_path: Path to save screenshot (optional)
        dom_selectors: CSS selectors to capture DOM state for

    Returns:
        BrowserObservation with current browser state
    """
    url = ""
    title = ""
    dom_snapshot = {}
    console_errors = []
    console_warnings = []
    screenshot_hash = ""
    cookies = {}
    local_storage = {}

    if page:
        try:
            # Get basic info
            url = page.url
            title = await page.title()

            # Capture screenshot if path provided
            if screenshot_path:
                await page.screenshot(path=screenshot_path)
                with open(screenshot_path, "rb") as f:
                    screenshot_hash = hashlib.sha256(f.read()).hexdigest()[:16]

            # Capture DOM snapshots for specific selectors
            if dom_selectors:
                for selector in dom_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        dom_snapshot[selector] = {
                            "count": len(elements),
                            "visible": await elements[0].is_visible() if elements else False,
                        }
                    except Exception:
                        dom_snapshot[selector] = {"count": 0, "visible": False}

            # Get cookies
            try:
                browser_cookies = await page.context.cookies()
                cookies = {c["name"]: c["value"] for c in browser_cookies}
            except Exception:
                pass

            # Get local storage
            try:
                local_storage = await page.evaluate(
                    "() => Object.assign({}, localStorage)"
                )
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Error capturing browser observation: {e}")
            console_errors.append(str(e))

    return BrowserObservation(
        url=url,
        title=title,
        dom_snapshot=dom_snapshot,
        console_errors=console_errors,
        console_warnings=console_warnings,
        screenshot_hash=screenshot_hash,
        screenshot_path=screenshot_path,
        cookies=cookies,
        local_storage=local_storage,
    )


def capture_execution_observation(
    step_traces: Optional[List[Dict[str, Any]]] = None,
    module_ios: Optional[List[Dict[str, Any]]] = None,
    error_stacks: Optional[List[str]] = None,
    execution_time_ms: int = 0,
) -> RuntimeObservation:
    """
    Capture runtime observation from execution data.

    Args:
        step_traces: List of step execution traces
        module_ios: List of module input/output records
        error_stacks: List of error stack traces
        execution_time_ms: Total execution time

    Returns:
        RuntimeObservation with execution data
    """
    traces = []
    ios = []

    if step_traces:
        for trace in step_traces:
            traces.append(
                StepTrace(
                    step_id=trace.get("step_id", ""),
                    module_id=trace.get("module_id", ""),
                    started_at=trace.get("started_at", ""),
                    ended_at=trace.get("ended_at", ""),
                    status=trace.get("status", ""),
                    error=trace.get("error"),
                )
            )

    if module_ios:
        from ..observation.observation_packet import ModuleIO

        for io in module_ios:
            ios.append(
                ModuleIO(
                    module_id=io.get("module_id", ""),
                    step_id=io.get("step_id", ""),
                    input_params=io.get("input", {}),
                    output_result=io.get("output", {}),
                    duration_ms=io.get("duration_ms", 0),
                )
            )

    return RuntimeObservation(
        step_traces=traces,
        module_ios=ios,
        error_stacks=error_stacks or [],
        execution_time_ms=execution_time_ms,
    )


def capture_file_observation(
    created_files: Optional[List[str]] = None,
    modified_files: Optional[List[str]] = None,
    deleted_files: Optional[List[str]] = None,
) -> FileSystemObservation:
    """
    Capture file system observation.

    Args:
        created_files: List of created file paths
        modified_files: List of modified file paths
        deleted_files: List of deleted file paths

    Returns:
        FileSystemObservation with file state
    """
    created = []
    modified = []

    for path in (created_files or []):
        info = _get_file_info(path)
        if info:
            created.append(info)

    for path in (modified_files or []):
        info = _get_file_info(path)
        if info:
            modified.append(info)

    return FileSystemObservation(
        files_created=created,
        files_modified=modified,
        files_deleted=deleted_files or [],
    )


def _get_file_info(path: str) -> Optional[FileInfo]:
    """Get FileInfo for a path."""
    if not os.path.exists(path):
        return FileInfo(path=path, exists=False)

    try:
        stat = os.stat(path)
        file_hash = ""
        content_preview = None

        # Calculate hash for files under 10MB
        if stat.st_size < 10 * 1024 * 1024:
            with open(path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()[:16]

        # Get content preview for text files
        if stat.st_size < 1024 * 1024:  # Under 1MB
            try:
                with open(path, "r") as f:
                    content_preview = f.read(500)
            except UnicodeDecodeError:
                pass

        return FileInfo(
            path=path,
            size=stat.st_size,
            hash=file_hash,
            exists=True,
            content_preview=content_preview,
        )

    except Exception as e:
        logger.warning(f"Error getting file info for {path}: {e}")
        return FileInfo(path=path, exists=True)


def capture_database_observation(
    connection_status: str = "connected",
    tables: Optional[Dict[str, Dict[str, Any]]] = None,
) -> DatabaseObservation:
    """
    Capture database observation.

    Args:
        connection_status: Current connection status
        tables: Dict of table name -> table info

    Returns:
        DatabaseObservation with database state
    """
    tables_snapshot = {}

    if tables:
        for name, info in tables.items():
            tables_snapshot[name] = TableSnapshot(
                table_name=name,
                row_count=info.get("row_count", 0),
                checksum=info.get("checksum", ""),
                sample_rows=info.get("sample_rows", []),
                key_queries=info.get("key_queries", {}),
            )

    return DatabaseObservation(
        connection_status=connection_status,
        tables_snapshot=tables_snapshot,
    )


class ObservationAdapter:
    """
    High-level adapter for capturing observations.

    Provides a unified interface for different observation sources.
    """

    def __init__(self):
        self._collector = ObservationCollector()

    async def capture_full(
        self,
        page=None,
        database_info: Optional[Dict[str, Any]] = None,
        file_changes: Optional[Dict[str, List[str]]] = None,
        execution_data: Optional[Dict[str, Any]] = None,
    ) -> ObservationPacket:
        """
        Capture a full observation from all sources.

        Args:
            page: Playwright page object
            database_info: Database connection and table info
            file_changes: Dict with created/modified/deleted file lists
            execution_data: Runtime execution data

        Returns:
            Complete ObservationPacket
        """
        # Browser observation
        browser = None
        if page:
            browser = await capture_browser_observation(page)

        # Database observation
        database = None
        if database_info:
            database = capture_database_observation(
                connection_status=database_info.get("status", "connected"),
                tables=database_info.get("tables"),
            )

        # File system observation
        filesystem = None
        if file_changes:
            filesystem = capture_file_observation(
                created_files=file_changes.get("created"),
                modified_files=file_changes.get("modified"),
                deleted_files=file_changes.get("deleted"),
            )

        # Runtime observation
        runtime = None
        if execution_data:
            runtime = capture_execution_observation(
                step_traces=execution_data.get("traces"),
                module_ios=execution_data.get("ios"),
                error_stacks=execution_data.get("errors"),
                execution_time_ms=execution_data.get("time_ms", 0),
            )

        # Build packet
        return self._collector.build_packet(
            browser=browser,
            database=database,
            filesystem=filesystem,
            include_runtime=runtime is not None,
            include_network=True,
        )

    def capture_quick(self, **kwargs) -> ObservationPacket:
        """
        Quick observation capture without async.

        Useful for simple observations that don't need browser data.
        """
        browser = None
        if "url" in kwargs:
            browser = BrowserObservation(
                url=kwargs.get("url", ""),
                title=kwargs.get("title", ""),
            )

        database = None
        if "db_status" in kwargs:
            database = DatabaseObservation(
                connection_status=kwargs.get("db_status", "connected"),
            )

        filesystem = None
        if "files" in kwargs:
            filesystem = capture_file_observation(
                created_files=kwargs.get("files", {}).get("created"),
                modified_files=kwargs.get("files", {}).get("modified"),
                deleted_files=kwargs.get("files", {}).get("deleted"),
            )

        return self._collector.build_packet(
            browser=browser,
            database=database,
            filesystem=filesystem,
        )
