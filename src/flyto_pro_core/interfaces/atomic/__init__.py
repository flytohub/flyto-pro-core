"""
Atomic Interfaces Modules

Single-responsibility modules for quality interfaces.
All modules are stateless pure functions.

Modules:
- quality_report: Quality report generation
- issue_handler: Issue handling utilities
"""

from .quality_report import (
    create_quality_report,
    calculate_normalized_score,
    count_issues_by_severity,
    report_to_dict,
)
from .issue_handler import (
    create_issue,
    issue_to_dict,
    filter_issues_by_severity,
    filter_issues_by_category,
    get_total_deduction,
)

__all__ = [
    # Quality report
    "create_quality_report",
    "calculate_normalized_score",
    "count_issues_by_severity",
    "report_to_dict",
    # Issue handler
    "create_issue",
    "issue_to_dict",
    "filter_issues_by_severity",
    "filter_issues_by_category",
    "get_total_deduction",
]
