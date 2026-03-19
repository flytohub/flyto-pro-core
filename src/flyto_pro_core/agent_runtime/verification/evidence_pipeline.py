"""
Evidence Pipeline - Raw evidence to derived evidence.

Two-layer architecture:
- RawEvidence: Original data (screenshot, HAR, console log)
- DerivedEvidence: Computed results for verification
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from ..contracts.contract_meta import ContractMeta


class EvidenceType(Enum):
    """Types of evidence."""

    # Raw types
    SCREENSHOT = "screenshot"
    HAR = "har"
    CONSOLE_LOG = "console_log"
    DB_DUMP = "db_dump"
    FILE_CONTENT = "file_content"
    HTML_SNAPSHOT = "html_snapshot"
    NETWORK_TRACE = "network_trace"

    # Derived types
    PIXEL_DIFF = "pixel_diff"
    DOM_QUERY = "dom_query"
    CHECKSUM = "checksum"
    SCHEMA_VALIDATION = "schema_validation"
    TEXT_MATCH = "text_match"
    OCR_RESULT = "ocr_result"


class RetentionPolicy(Enum):
    """Evidence retention policy."""

    KEEP_FOREVER = "keep_forever"
    KEEP_7D = "keep_7d"
    KEEP_ON_FAILURE = "keep_on_failure"
    DELETE_AFTER_VERIFY = "delete_after_verify"


@dataclass
class RawEvidence:
    """
    Raw evidence - original data for debug and audit.

    This is stored but NOT sent to LLM due to size.
    """

    # Metadata
    meta: ContractMeta = field(
        default_factory=lambda: ContractMeta(
            contract_name="RawEvidence",
            version="1.0.0",
        )
    )

    # Identity
    evidence_id: str = ""
    evidence_type: EvidenceType = EvidenceType.SCREENSHOT
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Raw data
    raw_data: bytes = b""
    storage_path: str = ""
    size_bytes: int = 0
    hash: str = ""  # SHA256

    # Retention
    retention_policy: RetentionPolicy = RetentionPolicy.KEEP_ON_FAILURE

    def __post_init__(self):
        if self.raw_data and not self.hash:
            self.hash = hashlib.sha256(self.raw_data).hexdigest()
            self.size_bytes = len(self.raw_data)
        if not self.evidence_id:
            self.evidence_id = str(uuid.uuid4())[:12]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (without raw_data)."""
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type.value,
            "timestamp": self.timestamp,
            "storage_path": self.storage_path,
            "size_bytes": self.size_bytes,
            "hash": self.hash,
            "retention_policy": self.retention_policy.value,
        }

    @classmethod
    def from_file(
        cls,
        file_path: str,
        evidence_type: EvidenceType,
    ) -> "RawEvidence":
        """Create from file."""
        with open(file_path, "rb") as f:
            data = f.read()

        return cls(
            evidence_type=evidence_type,
            raw_data=data,
            storage_path=file_path,
        )


@dataclass
class DerivedEvidence:
    """
    Derived evidence - computed results for verification.

    This is what the verifier uses, not the raw data.
    """

    # Identity
    evidence_id: str = ""
    raw_evidence_id: str = ""  # Source raw evidence
    derived_type: EvidenceType = EvidenceType.PIXEL_DIFF
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Derived result
    result: Any = None  # pixel diff score, selector values, etc.

    # Derivation method (for reproducibility)
    derivation_method: str = ""  # e.g. "pixel_diff_ssim", "dom_query"
    derivation_config: Dict[str, Any] = field(default_factory=dict)

    # Execution stats
    computation_time_ms: int = 0

    def __post_init__(self):
        if not self.evidence_id:
            self.evidence_id = str(uuid.uuid4())[:12]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "evidence_id": self.evidence_id,
            "raw_evidence_id": self.raw_evidence_id,
            "derived_type": self.derived_type.value,
            "timestamp": self.timestamp,
            "result": self.result,
            "derivation_method": self.derivation_method,
            "derivation_config": self.derivation_config,
            "computation_time_ms": self.computation_time_ms,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DerivedEvidence":
        """Create from dictionary."""
        return cls(
            evidence_id=data.get("evidence_id", ""),
            raw_evidence_id=data.get("raw_evidence_id", ""),
            derived_type=EvidenceType(data.get("derived_type", "pixel_diff")),
            timestamp=data.get("timestamp", ""),
            result=data.get("result"),
            derivation_method=data.get("derivation_method", ""),
            derivation_config=data.get("derivation_config", {}),
            computation_time_ms=data.get("computation_time_ms", 0),
        )


class EvidencePipeline:
    """
    Pipeline for processing evidence.

    Raw → Derived → Compare
    """

    def __init__(self, storage_path: str = "/tmp/flyto_evidence"):
        self.storage_path = storage_path
        self._derivers: Dict[str, Callable] = {}
        self._raw_store: Dict[str, RawEvidence] = {}
        self._derived_store: Dict[str, DerivedEvidence] = {}

        # Register default derivers
        self._register_default_derivers()

    def _register_default_derivers(self) -> None:
        """Register default derivation methods."""
        self._derivers["pixel_diff_ssim"] = self._derive_pixel_diff_ssim
        self._derivers["dom_query"] = self._derive_dom_query
        self._derivers["checksum"] = self._derive_checksum
        self._derivers["text_match"] = self._derive_text_match
        self._derivers["json_schema"] = self._derive_json_schema

    def register_deriver(
        self,
        method_name: str,
        deriver: Callable[[RawEvidence, Dict], DerivedEvidence],
    ) -> None:
        """Register a custom deriver."""
        self._derivers[method_name] = deriver

    def store_raw(self, evidence: RawEvidence) -> str:
        """Store raw evidence and return ID."""
        self._raw_store[evidence.evidence_id] = evidence
        return evidence.evidence_id

    def get_raw(self, evidence_id: str) -> Optional[RawEvidence]:
        """Get raw evidence by ID."""
        return self._raw_store.get(evidence_id)

    def derive(
        self,
        raw_evidence_id: str,
        method: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> DerivedEvidence:
        """
        Derive from raw evidence.

        Args:
            raw_evidence_id: ID of raw evidence
            method: Derivation method name
            config: Configuration for derivation

        Returns:
            DerivedEvidence with computed result
        """
        raw = self.get_raw(raw_evidence_id)
        if not raw:
            raise ValueError(f"Raw evidence not found: {raw_evidence_id}")

        deriver = self._derivers.get(method)
        if not deriver:
            raise ValueError(f"Unknown derivation method: {method}")

        import time

        start = time.time()
        derived = deriver(raw, config or {})
        derived.computation_time_ms = int((time.time() - start) * 1000)
        derived.raw_evidence_id = raw_evidence_id
        derived.derivation_method = method
        derived.derivation_config = config or {}

        self._derived_store[derived.evidence_id] = derived
        return derived

    def compare(
        self,
        derived: DerivedEvidence,
        expected: Any,
        threshold: Optional[float] = None,
    ) -> tuple[bool, float]:
        """
        Compare derived evidence to expected value.

        Returns:
            Tuple of (passed, score)
        """
        actual = derived.result

        # Exact match
        if threshold is None:
            return actual == expected, 1.0 if actual == expected else 0.0

        # Threshold-based match (for similarity scores)
        if isinstance(actual, (int, float)):
            score = float(actual)
            return score >= threshold, score

        # String similarity
        if isinstance(actual, str) and isinstance(expected, str):
            from difflib import SequenceMatcher

            score = SequenceMatcher(None, actual, expected).ratio()
            return score >= threshold, score

        return False, 0.0

    # Default derivers
    def _derive_pixel_diff_ssim(
        self,
        raw: RawEvidence,
        config: Dict[str, Any],
    ) -> DerivedEvidence:
        """Compute SSIM pixel difference."""
        # Placeholder - in real implementation, use skimage or similar
        # For now, return hash comparison
        expected_hash = config.get("expected_hash", "")
        is_match = raw.hash == expected_hash if expected_hash else True
        score = 1.0 if is_match else 0.0

        return DerivedEvidence(
            derived_type=EvidenceType.PIXEL_DIFF,
            result={
                "ssim_score": score,
                "is_match": is_match,
                "actual_hash": raw.hash,
                "expected_hash": expected_hash,
            },
        )

    def _derive_dom_query(
        self,
        raw: RawEvidence,
        config: Dict[str, Any],
    ) -> DerivedEvidence:
        """Query DOM elements."""
        selector = config.get("selector", "")
        attribute = config.get("attribute", "text")

        # Parse HTML and query
        # Placeholder implementation
        result = {
            "selector": selector,
            "found": True,  # Would actually query DOM
            "value": "",
            "count": 1,
        }

        return DerivedEvidence(
            derived_type=EvidenceType.DOM_QUERY,
            result=result,
        )

    def _derive_checksum(
        self,
        raw: RawEvidence,
        config: Dict[str, Any],
    ) -> DerivedEvidence:
        """Compute checksum."""
        algorithm = config.get("algorithm", "sha256")

        if algorithm == "sha256":
            checksum = hashlib.sha256(raw.raw_data).hexdigest()
        elif algorithm == "md5":
            checksum = hashlib.md5(raw.raw_data).hexdigest()
        else:
            checksum = raw.hash

        return DerivedEvidence(
            derived_type=EvidenceType.CHECKSUM,
            result={
                "checksum": checksum,
                "algorithm": algorithm,
                "size_bytes": raw.size_bytes,
            },
        )

    def _derive_text_match(
        self,
        raw: RawEvidence,
        config: Dict[str, Any],
    ) -> DerivedEvidence:
        """Match text patterns."""
        import re

        pattern = config.get("pattern", "")
        text = raw.raw_data.decode("utf-8", errors="ignore")

        matches = re.findall(pattern, text) if pattern else []

        return DerivedEvidence(
            derived_type=EvidenceType.TEXT_MATCH,
            result={
                "pattern": pattern,
                "matches": matches,
                "count": len(matches),
                "found": len(matches) > 0,
            },
        )

    def _derive_json_schema(
        self,
        raw: RawEvidence,
        config: Dict[str, Any],
    ) -> DerivedEvidence:
        """Validate JSON against schema."""
        schema = config.get("schema", {})

        try:
            data = json.loads(raw.raw_data.decode("utf-8"))
            # Would use jsonschema for real validation
            is_valid = True
            errors = []
        except json.JSONDecodeError as e:
            is_valid = False
            errors = [str(e)]
            data = None

        return DerivedEvidence(
            derived_type=EvidenceType.SCHEMA_VALIDATION,
            result={
                "is_valid": is_valid,
                "errors": errors,
                "data": data,
            },
        )

    def cleanup(
        self,
        keep_ids: Optional[List[str]] = None,
        keep_on_failure: bool = True,
    ) -> int:
        """
        Cleanup evidence based on retention policy.

        Returns:
            Number of items cleaned up
        """
        cleaned = 0
        keep_ids = keep_ids or []

        to_remove = []
        for eid, evidence in self._raw_store.items():
            if eid in keep_ids:
                continue

            if (
                evidence.retention_policy == RetentionPolicy.DELETE_AFTER_VERIFY
                or (
                    evidence.retention_policy == RetentionPolicy.KEEP_ON_FAILURE
                    and not keep_on_failure
                )
            ):
                to_remove.append(eid)

        for eid in to_remove:
            del self._raw_store[eid]
            cleaned += 1

        return cleaned


# Singleton instance
_pipeline_instance: Optional[EvidencePipeline] = None


def get_evidence_pipeline() -> EvidencePipeline:
    """Get the singleton evidence pipeline."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = EvidencePipeline()
    return _pipeline_instance
