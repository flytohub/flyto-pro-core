"""
Observation Module - Agent's eyes.

Collects structured world state for deterministic verification.
"""

from .observation_packet import (
    ObservationPacket,
    BrowserObservation,
    DatabaseObservation,
    FileSystemObservation,
    NetworkObservation,
    RuntimeObservation,
    TableSnapshot,
    FileInfo,
    RequestInfo,
    ResponseInfo,
    StepTrace,
    ModuleIO,
)
from .observation_collector import ObservationCollector, get_observation_collector

__all__ = [
    "ObservationPacket",
    "BrowserObservation",
    "DatabaseObservation",
    "FileSystemObservation",
    "NetworkObservation",
    "RuntimeObservation",
    "TableSnapshot",
    "FileInfo",
    "RequestInfo",
    "ResponseInfo",
    "StepTrace",
    "ModuleIO",
    "ObservationCollector",
    "get_observation_collector",
]
