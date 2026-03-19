"""
Quality Report - Atomic Module

Single responsibility: Quality report generation
Stateless: Pure functions
"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def create_quality_report(
    score: float,
    issues: Optional[List[Dict[str, Any]]] = None,
    max_score: float = 10.0,
    passed: bool = True,
    summary: str = "",
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a quality report structure

    Args:
        score: Quality score
        issues: List of issue dictionaries
        max_score: Maximum possible score
        passed: Whether quality check passed
        summary: Summary description
        metadata: Additional metadata

    Returns:
        {
            "ok": bool,
            "report": {
                "score": float,
                "max_score": float,
                "issues": list,
                "passed": bool,
                "summary": str,
                "metadata": dict
            },
            "error": str or None
        }
    """
    try:
        return {
            "ok": True,
            "report": {
                "score": score,
                "max_score": max_score,
                "issues": issues or [],
                "passed": passed,
                "summary": summary,
                "metadata": metadata or {}
            },
            "error": None
        }

    except Exception as e:
        logger.error(f"Report creation failed: {e}")
        return {
            "ok": False,
            "report": {},
            "error": str(e)
        }


def calculate_normalized_score(
    score: float,
    max_score: float
) -> Dict[str, Any]:
    """
    Calculate normalized score as 0-1 ratio

    Args:
        score: Current score
        max_score: Maximum possible score

    Returns:
        {
            "ok": bool,
            "normalized_score": float (0.0 to 1.0),
            "error": str or None
        }
    """
    try:
        if max_score <= 0:
            return {
                "ok": False,
                "normalized_score": 0.0,
                "error": "max_score must be positive"
            }

        return {
            "ok": True,
            "normalized_score": score / max_score,
            "error": None
        }

    except Exception as e:
        logger.error(f"Score normalization failed: {e}")
        return {
            "ok": False,
            "normalized_score": 0.0,
            "error": str(e)
        }


def count_issues_by_severity(
    issues: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Count issues by severity level

    Args:
        issues: List of issue dictionaries

    Returns:
        {
            "ok": bool,
            "counts": {
                "error": int,
                "warning": int,
                "info": int,
                "hint": int,
                "total": int
            },
            "error": str or None
        }
    """
    try:
        counts = {
            "error": 0,
            "warning": 0,
            "info": 0,
            "hint": 0,
            "total": len(issues)
        }

        for issue in issues:
            severity = issue.get("severity", "").lower()
            if severity in counts:
                counts[severity] += 1

        return {
            "ok": True,
            "counts": counts,
            "error": None
        }

    except Exception as e:
        logger.error(f"Issue counting failed: {e}")
        return {
            "ok": False,
            "counts": {},
            "error": str(e)
        }


def report_to_dict(
    report: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Convert report to dictionary format

    Args:
        report: Report dictionary

    Returns:
        {
            "ok": bool,
            "dict": formatted dictionary,
            "error": str or None
        }
    """
    try:
        result = {
            "score": report.get("score", 0),
            "max_score": report.get("max_score", 10.0),
            "passed": report.get("passed", False),
            "summary": report.get("summary", ""),
            "issues": report.get("issues", []),
            "metadata": report.get("metadata", {})
        }

        return {
            "ok": True,
            "dict": result,
            "error": None
        }

    except Exception as e:
        logger.error(f"Report to dict failed: {e}")
        return {
            "ok": False,
            "dict": {},
            "error": str(e)
        }
