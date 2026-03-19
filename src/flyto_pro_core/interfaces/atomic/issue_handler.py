"""
Issue Handler - Atomic Module

Single responsibility: Issue handling utilities
Stateless: Pure functions
"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def create_issue(
    message: str,
    severity: str,
    category: str,
    line: Optional[int] = None,
    column: Optional[int] = None,
    rule_id: Optional[str] = None,
    suggestion: Optional[str] = None,
    deduction: float = 0.0
) -> Dict[str, Any]:
    """
    Create an issue structure

    Args:
        message: Issue message
        severity: Issue severity (error, warning, info, hint)
        category: Issue category
        line: Line number
        column: Column number
        rule_id: Rule identifier
        suggestion: Suggested fix
        deduction: Score deduction

    Returns:
        {
            "ok": bool,
            "issue": issue dictionary,
            "error": str or None
        }
    """
    try:
        return {
            "ok": True,
            "issue": {
                "message": message,
                "severity": severity,
                "category": category,
                "line": line,
                "column": column,
                "rule_id": rule_id,
                "suggestion": suggestion,
                "deduction": deduction
            },
            "error": None
        }

    except Exception as e:
        logger.error(f"Issue creation failed: {e}")
        return {
            "ok": False,
            "issue": {},
            "error": str(e)
        }


def issue_to_dict(
    issue: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Convert issue to dictionary format

    Args:
        issue: Issue dictionary

    Returns:
        {
            "ok": bool,
            "dict": formatted dictionary,
            "error": str or None
        }
    """
    try:
        return {
            "ok": True,
            "dict": {
                "message": issue.get("message", ""),
                "severity": issue.get("severity", "info"),
                "category": issue.get("category", ""),
                "line": issue.get("line"),
                "column": issue.get("column"),
                "rule_id": issue.get("rule_id"),
                "suggestion": issue.get("suggestion"),
                "deduction": issue.get("deduction", 0.0)
            },
            "error": None
        }

    except Exception as e:
        logger.error(f"Issue to dict failed: {e}")
        return {
            "ok": False,
            "dict": {},
            "error": str(e)
        }


def filter_issues_by_severity(
    issues: List[Dict[str, Any]],
    severity: str
) -> Dict[str, Any]:
    """
    Filter issues by severity level

    Args:
        issues: List of issue dictionaries
        severity: Severity level to filter by

    Returns:
        {
            "ok": bool,
            "issues": filtered list,
            "error": str or None
        }
    """
    try:
        filtered = [
            issue for issue in issues
            if issue.get("severity", "").lower() == severity.lower()
        ]

        return {
            "ok": True,
            "issues": filtered,
            "error": None
        }

    except Exception as e:
        logger.error(f"Issue filtering failed: {e}")
        return {
            "ok": False,
            "issues": [],
            "error": str(e)
        }


def filter_issues_by_category(
    issues: List[Dict[str, Any]],
    category: str
) -> Dict[str, Any]:
    """
    Filter issues by category

    Args:
        issues: List of issue dictionaries
        category: Category to filter by

    Returns:
        {
            "ok": bool,
            "issues": filtered list,
            "error": str or None
        }
    """
    try:
        filtered = [
            issue for issue in issues
            if issue.get("category", "").lower() == category.lower()
        ]

        return {
            "ok": True,
            "issues": filtered,
            "error": None
        }

    except Exception as e:
        logger.error(f"Issue filtering failed: {e}")
        return {
            "ok": False,
            "issues": [],
            "error": str(e)
        }


def get_total_deduction(
    issues: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate total score deduction from issues

    Args:
        issues: List of issue dictionaries

    Returns:
        {
            "ok": bool,
            "total_deduction": float,
            "error": str or None
        }
    """
    try:
        total = sum(issue.get("deduction", 0.0) for issue in issues)

        return {
            "ok": True,
            "total_deduction": total,
            "error": None
        }

    except Exception as e:
        logger.error(f"Deduction calculation failed: {e}")
        return {
            "ok": False,
            "total_deduction": 0.0,
            "error": str(e)
        }
