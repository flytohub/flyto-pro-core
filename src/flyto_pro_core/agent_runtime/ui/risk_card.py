"""
Risk Card - User-friendly risk confirmation cards.

Presents risks to users in a clear, understandable format
with appropriate severity indicators.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class RiskLevel(Enum):
    """Risk severity levels."""

    LOW = "low"  # Minor impact, easily reversible
    MEDIUM = "medium"  # Moderate impact, may require effort to reverse
    HIGH = "high"  # Significant impact, difficult to reverse
    CRITICAL = "critical"  # Severe impact, irreversible


@dataclass
class RiskFactor:
    """A single risk factor."""

    factor_id: str = ""
    title: str = ""
    description: str = ""
    level: RiskLevel = RiskLevel.LOW
    reversible: bool = True
    mitigation: str = ""  # How to mitigate this risk
    affected_areas: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.factor_id:
            self.factor_id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_id": self.factor_id,
            "title": self.title,
            "description": self.description,
            "level": self.level.value,
            "reversible": self.reversible,
            "mitigation": self.mitigation,
            "affected_areas": self.affected_areas,
        }


@dataclass
class RiskCard:
    """
    A risk confirmation card for user display.

    Presents risks in a clear, non-technical format.
    """

    card_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Main content
    title: str = ""
    summary: str = ""  # One-line summary
    overall_level: RiskLevel = RiskLevel.LOW

    # Risk factors
    factors: List[RiskFactor] = field(default_factory=list)

    # What will happen
    what_will_happen: List[str] = field(default_factory=list)
    what_could_go_wrong: List[str] = field(default_factory=list)

    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    requires_backup: bool = False
    requires_confirmation: bool = True

    # Actions
    proceed_label: str = "Proceed"
    cancel_label: str = "Cancel"
    backup_label: str = "Backup First"

    # Metadata
    source_action: str = ""  # What action triggered this
    affected_resources: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.card_id:
            self.card_id = str(uuid.uuid4())[:12]

        # Auto-calculate overall level from factors
        if self.factors and self.overall_level == RiskLevel.LOW:
            levels = [f.level for f in self.factors]
            if RiskLevel.CRITICAL in levels:
                self.overall_level = RiskLevel.CRITICAL
            elif RiskLevel.HIGH in levels:
                self.overall_level = RiskLevel.HIGH
            elif RiskLevel.MEDIUM in levels:
                self.overall_level = RiskLevel.MEDIUM

    def add_factor(self, factor: RiskFactor) -> None:
        """Add a risk factor."""
        self.factors.append(factor)

        # Update overall level
        if factor.level.value > self.overall_level.value:
            self.overall_level = factor.level

        # Auto-require backup for high/critical risks
        if factor.level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            self.requires_backup = True

    def get_highest_risk(self) -> Optional[RiskFactor]:
        """Get the highest risk factor."""
        if not self.factors:
            return None

        return max(
            self.factors,
            key=lambda f: ["low", "medium", "high", "critical"].index(f.level.value),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "card_id": self.card_id,
            "timestamp": self.timestamp,
            "title": self.title,
            "summary": self.summary,
            "overall_level": self.overall_level.value,
            "factors": [f.to_dict() for f in self.factors],
            "what_will_happen": self.what_will_happen,
            "what_could_go_wrong": self.what_could_go_wrong,
            "recommendations": self.recommendations,
            "requires_backup": self.requires_backup,
            "requires_confirmation": self.requires_confirmation,
            "proceed_label": self.proceed_label,
            "cancel_label": self.cancel_label,
            "backup_label": self.backup_label,
            "source_action": self.source_action,
            "affected_resources": self.affected_resources,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskCard":
        factors = []
        for f_data in data.get("factors", []):
            factors.append(
                RiskFactor(
                    factor_id=f_data.get("factor_id", ""),
                    title=f_data.get("title", ""),
                    description=f_data.get("description", ""),
                    level=RiskLevel(f_data.get("level", "low")),
                    reversible=f_data.get("reversible", True),
                    mitigation=f_data.get("mitigation", ""),
                    affected_areas=f_data.get("affected_areas", []),
                )
            )

        return cls(
            card_id=data.get("card_id", ""),
            timestamp=data.get("timestamp", ""),
            title=data.get("title", ""),
            summary=data.get("summary", ""),
            overall_level=RiskLevel(data.get("overall_level", "low")),
            factors=factors,
            what_will_happen=data.get("what_will_happen", []),
            what_could_go_wrong=data.get("what_could_go_wrong", []),
            recommendations=data.get("recommendations", []),
            requires_backup=data.get("requires_backup", False),
            requires_confirmation=data.get("requires_confirmation", True),
            proceed_label=data.get("proceed_label", "Proceed"),
            cancel_label=data.get("cancel_label", "Cancel"),
            backup_label=data.get("backup_label", "Backup First"),
            source_action=data.get("source_action", ""),
            affected_resources=data.get("affected_resources", []),
        )


class RiskCardBuilder:
    """Fluent builder for RiskCard."""

    def __init__(self):
        self._card = RiskCard()

    def title(self, title: str) -> "RiskCardBuilder":
        """Set card title."""
        self._card.title = title
        return self

    def summary(self, summary: str) -> "RiskCardBuilder":
        """Set summary."""
        self._card.summary = summary
        return self

    def level(self, level: RiskLevel) -> "RiskCardBuilder":
        """Set overall level."""
        self._card.overall_level = level
        return self

    def factor(
        self,
        title: str,
        description: str = "",
        level: RiskLevel = RiskLevel.LOW,
        reversible: bool = True,
        mitigation: str = "",
    ) -> "RiskCardBuilder":
        """Add a risk factor."""
        self._card.add_factor(
            RiskFactor(
                title=title,
                description=description,
                level=level,
                reversible=reversible,
                mitigation=mitigation,
            )
        )
        return self

    def will_happen(self, *items: str) -> "RiskCardBuilder":
        """Add what will happen items."""
        self._card.what_will_happen.extend(items)
        return self

    def could_go_wrong(self, *items: str) -> "RiskCardBuilder":
        """Add what could go wrong items."""
        self._card.what_could_go_wrong.extend(items)
        return self

    def recommend(self, *items: str) -> "RiskCardBuilder":
        """Add recommendations."""
        self._card.recommendations.extend(items)
        return self

    def require_backup(self, required: bool = True) -> "RiskCardBuilder":
        """Set backup requirement."""
        self._card.requires_backup = required
        return self

    def source_action(self, action: str) -> "RiskCardBuilder":
        """Set source action."""
        self._card.source_action = action
        return self

    def affected_resources(self, *resources: str) -> "RiskCardBuilder":
        """Add affected resources."""
        self._card.affected_resources.extend(resources)
        return self

    def build(self) -> RiskCard:
        """Build the risk card."""
        return self._card


class RiskAssessor:
    """
    Assesses risk for common operations.

    Provides pre-built risk cards for common scenarios.
    """

    @staticmethod
    def assess_file_deletion(
        files: List[str],
        has_backup: bool = False,
    ) -> RiskCard:
        """Assess risk of file deletion."""
        file_count = len(files)

        builder = (
            RiskCardBuilder()
            .title(f"Delete {file_count} file(s)")
            .summary(f"You are about to delete {file_count} file(s)")
            .factor(
                title="Permanent deletion",
                description="Deleted files cannot be recovered unless backed up",
                level=RiskLevel.HIGH if not has_backup else RiskLevel.MEDIUM,
                reversible=has_backup,
                mitigation="Create a backup before deleting",
            )
            .will_happen(
                f"{file_count} file(s) will be permanently deleted",
            )
            .could_go_wrong(
                "Important files could be lost if not backed up",
                "Other code may depend on these files",
            )
            .recommend(
                "Review the file list carefully",
                "Create a backup if unsure",
            )
            .affected_resources(*files)
            .source_action("file_delete")
        )

        if not has_backup:
            builder.require_backup()

        return builder.build()

    @staticmethod
    def assess_database_modification(
        operation: str,
        table: str,
        rows_affected: int,
        has_backup: bool = False,
    ) -> RiskCard:
        """Assess risk of database modification."""
        level = RiskLevel.MEDIUM
        if operation == "delete":
            level = RiskLevel.HIGH
        if rows_affected > 100:
            level = RiskLevel.HIGH
        if rows_affected > 1000:
            level = RiskLevel.CRITICAL

        builder = (
            RiskCardBuilder()
            .title(f"Database {operation}")
            .summary(f"{operation.title()} {rows_affected} rows in {table}")
            .factor(
                title=f"Data {operation}",
                description=f"{rows_affected} rows will be affected",
                level=level,
                reversible=has_backup,
                mitigation="Create a database backup first",
            )
            .will_happen(
                f"{rows_affected} rows in '{table}' will be {operation}d",
            )
            .could_go_wrong(
                "Data loss if wrong rows are affected",
                "Application behavior may change",
                "Related data may become inconsistent",
            )
            .recommend(
                "Verify the query criteria",
                "Create a backup before proceeding",
                "Test on a smaller dataset first",
            )
            .affected_resources(table)
            .source_action(f"db_{operation}")
        )

        if not has_backup or rows_affected > 100:
            builder.require_backup()

        return builder.build()

    @staticmethod
    def assess_deployment(
        environment: str,
        changes_count: int,
        has_tests_passed: bool = True,
    ) -> RiskCard:
        """Assess risk of deployment."""
        level = RiskLevel.LOW
        if environment == "production":
            level = RiskLevel.HIGH if has_tests_passed else RiskLevel.CRITICAL
        elif environment == "staging":
            level = RiskLevel.MEDIUM

        builder = (
            RiskCardBuilder()
            .title(f"Deploy to {environment}")
            .summary(f"Deploy {changes_count} changes to {environment}")
            .factor(
                title="Production deployment" if environment == "production" else "Environment deployment",
                description=f"Changes will be visible to {'all users' if environment == 'production' else 'testers'}",
                level=level,
                reversible=True,
                mitigation="Keep rollback plan ready",
            )
            .will_happen(
                f"{changes_count} changes will be deployed",
                f"{'Users' if environment == 'production' else 'Testers'} will see the new version",
            )
            .could_go_wrong(
                "New bugs may be introduced",
                "Performance may be affected",
                "Users may experience issues",
            )
            .recommend(
                "Review all changes before deploying",
                "Prepare a rollback plan",
                "Monitor after deployment",
            )
            .source_action("deployment")
        )

        if not has_tests_passed:
            builder.factor(
                title="Tests not passing",
                description="Some tests are failing",
                level=RiskLevel.HIGH,
                reversible=True,
                mitigation="Fix failing tests before deploying",
            )

        return builder.build()
