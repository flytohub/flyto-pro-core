"""
Decision Card Builder - Fluent API for building decision cards.

Translates technical decisions into user-friendly cards.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ..contracts.decision_card import (
    DecisionCard,
    DecisionOption,
    DecisionContext,
    UserDecision,
)
from .intervention_types import (
    InterventionOption,
    InterventionPoint,
    InterventionRequest,
    InterventionType,
    InterventionPriority,
)


@dataclass
class OptionBuilder:
    """Builder for decision options."""

    _option: DecisionOption = field(default_factory=DecisionOption)

    def id(self, option_id: str) -> "OptionBuilder":
        """Set option ID."""
        self._option.option_id = option_id
        return self

    def label(self, label: str) -> "OptionBuilder":
        """Set display label."""
        self._option.label = label
        return self

    def description(self, desc: str) -> "OptionBuilder":
        """Set description."""
        self._option.description = desc
        return self

    def recommended(self, is_recommended: bool = True) -> "OptionBuilder":
        """Mark as recommended."""
        self._option.is_recommended = is_recommended
        return self

    def dangerous(self, is_dangerous: bool = True) -> "OptionBuilder":
        """Mark as dangerous."""
        self._option.is_dangerous = is_dangerous
        return self

    def consequence(self, consequence: str) -> "OptionBuilder":
        """Add a consequence."""
        self._option.consequences.append(consequence)
        return self

    def consequences(self, consequences: List[str]) -> "OptionBuilder":
        """Set all consequences."""
        self._option.consequences = consequences
        return self

    def metadata(self, key: str, value: Any) -> "OptionBuilder":
        """Add metadata."""
        self._option.metadata[key] = value
        return self

    def action(self, action: Dict[str, Any]) -> "OptionBuilder":
        """Set action to execute if selected."""
        self._option.action = action
        return self

    def build(self) -> DecisionOption:
        """Build the option."""
        if not self._option.option_id:
            self._option.option_id = str(uuid.uuid4())[:8]
        return self._option


class DecisionCardBuilder:
    """
    Fluent builder for DecisionCard.

    Example:
        card = (DecisionCardBuilder()
            .type("choose_approach")
            .title("How to implement authentication?")
            .description("Choose the authentication method for the API.")
            .option(OptionBuilder()
                .label("JWT")
                .description("Stateless, scalable")
                .recommended()
                .build())
            .option(OptionBuilder()
                .label("Session")
                .description("Traditional, server-side")
                .build())
            .context({"api_type": "REST"})
            .build())
    """

    def __init__(self):
        self._card = DecisionCard()
        self._context = DecisionContext()

    def id(self, card_id: str) -> "DecisionCardBuilder":
        """Set card ID."""
        self._card.card_id = card_id
        return self

    def type(self, decision_type: str) -> "DecisionCardBuilder":
        """Set decision type."""
        self._card.decision_type = decision_type
        return self

    def title(self, title: str) -> "DecisionCardBuilder":
        """Set title."""
        self._card.title = title
        return self

    def description(self, description: str) -> "DecisionCardBuilder":
        """Set description."""
        self._card.description = description
        return self

    def priority(self, priority: str) -> "DecisionCardBuilder":
        """Set priority (critical, high, medium, low)."""
        self._card.priority = priority
        return self

    def option(self, option: DecisionOption) -> "DecisionCardBuilder":
        """Add an option."""
        self._card.options.append(option)
        return self

    def options(self, options: List[DecisionOption]) -> "DecisionCardBuilder":
        """Set all options."""
        self._card.options = options
        return self

    def context(self, context: Dict[str, Any]) -> "DecisionCardBuilder":
        """Set context data."""
        self._context.additional_context = context
        return self

    def step_context(
        self,
        step_id: str,
        task_id: str = "",
        goal_id: str = "",
    ) -> "DecisionCardBuilder":
        """Set step context."""
        self._context.step_id = step_id
        self._context.task_id = task_id
        self._context.goal_id = goal_id
        return self

    def evidence(self, evidence_id: str) -> "DecisionCardBuilder":
        """Add evidence reference."""
        self._context.relevant_evidence.append(evidence_id)
        return self

    def current_state(self, state: str) -> "DecisionCardBuilder":
        """Set current state description."""
        self._context.current_state = state
        return self

    def allow_text_input(
        self,
        allowed: bool = True,
        prompt: str = "",
    ) -> "DecisionCardBuilder":
        """Allow free-form text input."""
        self._card.allow_text_input = allowed
        self._card.text_input_prompt = prompt
        return self

    def blocking(self, is_blocking: bool = True) -> "DecisionCardBuilder":
        """Set whether this blocks execution."""
        self._card.is_blocking = is_blocking
        return self

    def timeout(self, timeout_ms: int) -> "DecisionCardBuilder":
        """Set auto-timeout in milliseconds."""
        self._card.timeout_ms = timeout_ms
        return self

    def default_option(self, option_id: str) -> "DecisionCardBuilder":
        """Set default option for auto-approve."""
        self._card.default_option_id = option_id
        return self

    def build(self) -> DecisionCard:
        """Build the decision card."""
        if not self._card.card_id:
            self._card.card_id = str(uuid.uuid4())[:12]
        self._card.context = self._context
        return self._card


class TechToUserTranslator:
    """
    Translates technical decisions to user-friendly language.

    This is the bridge between AI decisions and human understanding.
    """

    def __init__(self):
        self._templates: Dict[str, Callable] = {
            "file_delete": self._translate_file_delete,
            "db_modify": self._translate_db_modify,
            "api_call": self._translate_api_call,
            "dependency_add": self._translate_dependency_add,
            "config_change": self._translate_config_change,
        }

    def translate(
        self,
        decision_type: str,
        technical_data: Dict[str, Any],
    ) -> DecisionCard:
        """Translate technical decision to user-friendly card."""
        translator = self._templates.get(decision_type)
        if translator:
            return translator(technical_data)

        # Default translation
        return self._default_translation(decision_type, technical_data)

    def register_translator(
        self,
        decision_type: str,
        translator: Callable[[Dict[str, Any]], DecisionCard],
    ) -> None:
        """Register custom translator."""
        self._templates[decision_type] = translator

    def _default_translation(
        self,
        decision_type: str,
        data: Dict[str, Any],
    ) -> DecisionCard:
        """Default translation for unknown types."""
        return (
            DecisionCardBuilder()
            .type(decision_type)
            .title(data.get("title", f"Decision: {decision_type}"))
            .description(data.get("description", "Please make a decision."))
            .option(
                OptionBuilder()
                .label("Proceed")
                .description("Continue with the operation")
                .recommended()
                .build()
            )
            .option(
                OptionBuilder()
                .label("Cancel")
                .description("Cancel the operation")
                .build()
            )
            .build()
        )

    def _translate_file_delete(self, data: Dict[str, Any]) -> DecisionCard:
        """Translate file deletion decision."""
        files = data.get("files", [])
        file_list = ", ".join(files[:3])
        if len(files) > 3:
            file_list += f" and {len(files) - 3} more"

        return (
            DecisionCardBuilder()
            .type("file_delete")
            .title("Delete Files?")
            .description(f"The following files will be deleted: {file_list}")
            .priority("high")
            .option(
                OptionBuilder()
                .label("Delete")
                .description("Permanently delete the files")
                .dangerous()
                .consequence("Files cannot be recovered")
                .build()
            )
            .option(
                OptionBuilder()
                .label("Keep")
                .description("Do not delete the files")
                .recommended()
                .build()
            )
            .option(
                OptionBuilder()
                .label("Backup First")
                .description("Create backup before deleting")
                .build()
            )
            .context({"files": files})
            .build()
        )

    def _translate_db_modify(self, data: Dict[str, Any]) -> DecisionCard:
        """Translate database modification decision."""
        operation = data.get("operation", "modify")
        table = data.get("table", "unknown")
        rows_affected = data.get("rows_affected", 0)

        return (
            DecisionCardBuilder()
            .type("db_modify")
            .title(f"Database {operation.title()}?")
            .description(
                f"This will {operation} {rows_affected} rows in table '{table}'."
            )
            .priority("critical" if operation == "delete" else "high")
            .option(
                OptionBuilder()
                .label("Execute")
                .description(f"Proceed with {operation}")
                .dangerous(operation == "delete")
                .build()
            )
            .option(
                OptionBuilder()
                .label("Cancel")
                .description("Do not modify the database")
                .recommended()
                .build()
            )
            .option(
                OptionBuilder()
                .label("Preview")
                .description("Show affected rows first")
                .build()
            )
            .context(data)
            .build()
        )

    def _translate_api_call(self, data: Dict[str, Any]) -> DecisionCard:
        """Translate external API call decision."""
        endpoint = data.get("endpoint", "unknown")
        method = data.get("method", "GET")
        cost = data.get("estimated_cost", 0)

        builder = (
            DecisionCardBuilder()
            .type("api_call")
            .title("External API Call?")
            .description(f"Call {method} {endpoint}")
        )

        if cost > 0:
            builder.priority("high")
            builder.option(
                OptionBuilder()
                .label("Proceed")
                .description(f"Estimated cost: ${cost:.4f}")
                .consequence(f"Will cost approximately ${cost:.4f}")
                .build()
            )
        else:
            builder.option(
                OptionBuilder()
                .label("Proceed")
                .description("Make the API call")
                .recommended()
                .build()
            )

        builder.option(
            OptionBuilder()
            .label("Skip")
            .description("Do not call the API")
            .build()
        )

        return builder.context(data).build()

    def _translate_dependency_add(self, data: Dict[str, Any]) -> DecisionCard:
        """Translate dependency addition decision."""
        package = data.get("package", "unknown")
        version = data.get("version", "latest")

        return (
            DecisionCardBuilder()
            .type("dependency_add")
            .title("Add Dependency?")
            .description(f"Add {package}@{version} to the project.")
            .option(
                OptionBuilder()
                .label("Add")
                .description(f"Install {package}")
                .recommended()
                .build()
            )
            .option(
                OptionBuilder()
                .label("Skip")
                .description("Do not add the dependency")
                .build()
            )
            .option(
                OptionBuilder()
                .label("Different Version")
                .description("Choose a different version")
                .metadata("requires_input", True)
                .build()
            )
            .allow_text_input(True, "Enter version (e.g., 1.2.3):")
            .context(data)
            .build()
        )

    def _translate_config_change(self, data: Dict[str, Any]) -> DecisionCard:
        """Translate configuration change decision."""
        file = data.get("file", "config")
        changes = data.get("changes", {})

        change_desc = ", ".join(f"{k}={v}" for k, v in list(changes.items())[:3])
        if len(changes) > 3:
            change_desc += f" and {len(changes) - 3} more"

        return (
            DecisionCardBuilder()
            .type("config_change")
            .title("Modify Configuration?")
            .description(f"Changes to {file}: {change_desc}")
            .option(
                OptionBuilder()
                .label("Apply")
                .description("Apply the configuration changes")
                .recommended()
                .build()
            )
            .option(
                OptionBuilder()
                .label("Skip")
                .description("Keep current configuration")
                .build()
            )
            .option(
                OptionBuilder()
                .label("Review")
                .description("Review changes in detail")
                .build()
            )
            .context(data)
            .build()
        )


def card_to_intervention_request(
    card: DecisionCard,
    point_type: InterventionType = InterventionType.CHOOSE_APPROACH,
) -> InterventionRequest:
    """Convert DecisionCard to InterventionRequest."""
    # Create intervention point
    point = InterventionPoint(
        point_id=f"point-{card.card_id}",
        point_type=point_type,
        priority=InterventionPriority(card.priority),
        title=card.title,
        description=card.description,
        auto_approve_after_ms=card.timeout_ms,
        step_id=card.context.step_id if card.context else None,
        task_id=card.context.task_id if card.context else None,
        goal_id=card.context.goal_id if card.context else None,
    )

    # Convert options
    options = [
        InterventionOption(
            option_id=opt.option_id,
            label=opt.label,
            description=opt.description,
            is_recommended=opt.is_recommended,
            is_dangerous=opt.is_dangerous,
            consequences=opt.consequences,
            metadata=opt.metadata,
        )
        for opt in card.options
    ]

    return InterventionRequest(
        request_id=card.card_id,
        intervention_point=point,
        options=options,
        is_blocking=card.is_blocking,
        current_state_summary=(
            card.context.additional_context if card.context else {}
        ),
        relevant_evidence=(
            card.context.relevant_evidence if card.context else []
        ),
        allow_text_input=card.allow_text_input,
        text_input_prompt=card.text_input_prompt,
    )


# Singleton translator
_translator_instance: Optional[TechToUserTranslator] = None


def get_translator() -> TechToUserTranslator:
    """Get the singleton translator."""
    global _translator_instance
    if _translator_instance is None:
        _translator_instance = TechToUserTranslator()
    return _translator_instance
