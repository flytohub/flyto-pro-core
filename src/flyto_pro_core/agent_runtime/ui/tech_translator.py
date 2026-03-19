"""
Tech Decision Translator - Translate technical content for users.

Converts technical terms, decisions, and errors into user-friendly
language that non-technical stakeholders can understand.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class TranslationContext:
    """Context for translation."""

    user_technical_level: str = "beginner"  # beginner, intermediate, advanced
    domain: str = "web"  # web, mobile, backend, data, etc.
    project_type: str = ""
    custom_terms: Dict[str, str] = field(default_factory=dict)


class TechDecisionTranslator:
    """
    Translates technical content for different audience levels.

    Examples:
    - "HTTP 500 Internal Server Error" -> "The server encountered an error"
    - "npm install --save-dev" -> "Installing development dependencies"
    - "CORS policy violation" -> "Security restrictions preventing API access"
    """

    def __init__(self):
        # Technical term translations by level
        self._translations: Dict[str, Dict[str, str]] = {
            "beginner": {},
            "intermediate": {},
            "advanced": {},
        }

        # Error message patterns
        self._error_patterns: List[Tuple[str, str]] = []

        # Action translations
        self._action_translations: Dict[str, str] = {}

        # Initialize default translations
        self._init_defaults()

    def _init_defaults(self) -> None:
        """Initialize default translations."""
        # Beginner-level translations
        self._translations["beginner"].update({
            "API": "connection to external service",
            "database": "data storage",
            "server": "web server",
            "client": "browser",
            "frontend": "what users see",
            "backend": "behind-the-scenes processing",
            "deploy": "publish online",
            "repository": "code storage",
            "branch": "version of code",
            "merge": "combine code changes",
            "commit": "save code changes",
            "dependency": "required component",
            "package": "pre-built component",
            "module": "code unit",
            "function": "action",
            "variable": "stored value",
            "parameter": "input value",
            "return value": "result",
            "exception": "error",
            "stack trace": "error details",
            "timeout": "took too long",
            "authentication": "login verification",
            "authorization": "access permission",
            "token": "access key",
            "session": "login period",
            "cache": "temporary storage",
            "queue": "waiting list",
            "webhook": "automatic notification",
            "endpoint": "service address",
        })

        # Intermediate-level (more technical but still simplified)
        self._translations["intermediate"].update({
            "API": "API (Application Programming Interface)",
            "REST": "REST API",
            "GraphQL": "GraphQL API",
            "HTTP": "HTTP protocol",
            "CORS": "Cross-Origin Resource Sharing",
            "JWT": "JSON Web Token",
            "OAuth": "OAuth authentication",
            "SSL/TLS": "encrypted connection",
            "DNS": "domain name system",
            "CDN": "content delivery network",
            "CI/CD": "automated testing and deployment",
            "Docker": "containerized application",
            "Kubernetes": "container orchestration",
        })

        # Error pattern translations
        self._error_patterns = [
            (r"HTTP 500.*", "Server error occurred"),
            (r"HTTP 404.*", "Page or resource not found"),
            (r"HTTP 403.*", "Access denied"),
            (r"HTTP 401.*", "Authentication required"),
            (r"Connection refused.*", "Could not connect to server"),
            (r"Timeout.*", "Operation took too long"),
            (r"ENOENT.*", "File not found"),
            (r"EACCES.*", "Permission denied"),
            (r"OutOfMemory.*", "System ran out of memory"),
            (r"SyntaxError.*", "Code syntax issue"),
            (r"TypeError.*", "Incorrect data type"),
            (r"ReferenceError.*", "Missing reference"),
            (r"CORS.*policy.*", "Security restrictions blocking request"),
            (r"SSL.*certificate.*", "Security certificate issue"),
        ]

        # Action translations
        self._action_translations = {
            "npm install": "Installing dependencies",
            "pip install": "Installing Python packages",
            "git clone": "Downloading code",
            "git pull": "Getting latest changes",
            "git push": "Uploading changes",
            "git commit": "Saving changes",
            "docker build": "Building container",
            "docker run": "Starting container",
            "pytest": "Running tests",
            "npm test": "Running tests",
            "npm run build": "Building project",
            "npm run dev": "Starting development server",
            "make": "Building project",
            "kubectl apply": "Deploying to cluster",
        }

    def translate_term(
        self,
        term: str,
        context: Optional[TranslationContext] = None,
    ) -> str:
        """Translate a technical term."""
        context = context or TranslationContext()

        # Check custom terms first
        if context.custom_terms and term in context.custom_terms:
            return context.custom_terms[term]

        # Get translations for user level
        level_translations = self._translations.get(
            context.user_technical_level,
            self._translations["beginner"],
        )

        # Try exact match
        if term in level_translations:
            return level_translations[term]

        # Try case-insensitive match
        term_lower = term.lower()
        for key, value in level_translations.items():
            if key.lower() == term_lower:
                return value

        return term  # Return original if no translation

    def translate_error(
        self,
        error_message: str,
        context: Optional[TranslationContext] = None,
    ) -> str:
        """Translate an error message."""
        context = context or TranslationContext()

        # Check patterns
        for pattern, translation in self._error_patterns:
            if re.search(pattern, error_message, re.IGNORECASE):
                if context.user_technical_level == "advanced":
                    return f"{translation} ({error_message})"
                return translation

        # Default: simplify the error
        if context.user_technical_level == "beginner":
            # Remove technical details
            simplified = re.sub(r"at \d+:\d+", "", error_message)
            simplified = re.sub(r"in [\w/]+\.[\w]+", "", simplified)
            simplified = re.sub(r"0x[0-9a-fA-F]+", "", simplified)
            return simplified.strip() or "An error occurred"

        return error_message

    def translate_action(
        self,
        action: str,
        context: Optional[TranslationContext] = None,
    ) -> str:
        """Translate a technical action."""
        context = context or TranslationContext()

        # Check exact match
        if action in self._action_translations:
            return self._action_translations[action]

        # Check prefix match
        for cmd, translation in self._action_translations.items():
            if action.startswith(cmd):
                return translation

        # Parse and simplify common patterns
        if action.startswith("npm "):
            return f"Running npm command: {action[4:]}"
        if action.startswith("git "):
            return f"Git operation: {action[4:]}"
        if action.startswith("docker "):
            return f"Docker operation: {action[7:]}"

        return action

    def translate_decision(
        self,
        decision_type: str,
        technical_data: Dict[str, Any],
        context: Optional[TranslationContext] = None,
    ) -> Dict[str, str]:
        """
        Translate a technical decision for user display.

        Returns dict with:
        - title: User-friendly title
        - description: Explanation
        - impact: What will happen
        """
        context = context or TranslationContext()

        translators = {
            "file_operation": self._translate_file_operation,
            "database_operation": self._translate_db_operation,
            "api_call": self._translate_api_call,
            "dependency_change": self._translate_dependency_change,
            "config_change": self._translate_config_change,
            "deployment": self._translate_deployment,
        }

        translator = translators.get(
            decision_type,
            self._translate_default,
        )

        return translator(technical_data, context)

    def _translate_file_operation(
        self,
        data: Dict[str, Any],
        context: TranslationContext,
    ) -> Dict[str, str]:
        """Translate file operation."""
        operation = data.get("operation", "modify")
        files = data.get("files", [])
        file_count = len(files)

        titles = {
            "create": "Create new files",
            "modify": "Modify files",
            "delete": "Delete files",
            "move": "Move files",
            "copy": "Copy files",
        }

        title = titles.get(operation, f"File {operation}")

        if file_count == 1:
            description = f"This will {operation} the file: {files[0]}"
        else:
            description = f"This will {operation} {file_count} files"

        impact = ""
        if operation == "delete":
            impact = "These files will be permanently removed"
        elif operation == "modify":
            impact = "The content of these files will be changed"

        return {
            "title": title,
            "description": description,
            "impact": impact,
        }

    def _translate_db_operation(
        self,
        data: Dict[str, Any],
        context: TranslationContext,
    ) -> Dict[str, str]:
        """Translate database operation."""
        operation = data.get("operation", "query")
        table = data.get("table", "")
        rows = data.get("rows_affected", 0)

        titles = {
            "insert": "Add data",
            "update": "Update data",
            "delete": "Remove data",
            "query": "Read data",
        }

        title = titles.get(operation, f"Database {operation}")

        if context.user_technical_level == "beginner":
            description = f"This will {operation} information in the database"
        else:
            description = f"This will {operation} {rows} rows in table '{table}'"

        impact = ""
        if operation in ("delete", "update"):
            impact = f"This will affect {rows} records"

        return {
            "title": title,
            "description": description,
            "impact": impact,
        }

    def _translate_api_call(
        self,
        data: Dict[str, Any],
        context: TranslationContext,
    ) -> Dict[str, str]:
        """Translate API call."""
        method = data.get("method", "GET")
        endpoint = data.get("endpoint", "")
        cost = data.get("estimated_cost", 0)

        if context.user_technical_level == "beginner":
            title = "Connect to external service"
            description = "This will communicate with an external service"
        else:
            title = f"API Call: {method}"
            description = f"Call {method} {endpoint}"

        impact = ""
        if cost > 0:
            impact = f"This may cost approximately ${cost:.4f}"

        return {
            "title": title,
            "description": description,
            "impact": impact,
        }

    def _translate_dependency_change(
        self,
        data: Dict[str, Any],
        context: TranslationContext,
    ) -> Dict[str, str]:
        """Translate dependency change."""
        operation = data.get("operation", "add")
        package = data.get("package", "")
        version = data.get("version", "")

        if operation == "add":
            title = "Add new component"
            description = f"Add {package} to the project"
        elif operation == "remove":
            title = "Remove component"
            description = f"Remove {package} from the project"
        else:
            title = "Update component"
            description = f"Update {package} to version {version}"

        impact = "This will modify project dependencies"

        return {
            "title": title,
            "description": description,
            "impact": impact,
        }

    def _translate_config_change(
        self,
        data: Dict[str, Any],
        context: TranslationContext,
    ) -> Dict[str, str]:
        """Translate configuration change."""
        file = data.get("file", "configuration")
        changes = data.get("changes", {})

        title = "Update settings"
        description = f"Modify {len(changes)} settings in {file}"
        impact = "Application behavior may change"

        return {
            "title": title,
            "description": description,
            "impact": impact,
        }

    def _translate_deployment(
        self,
        data: Dict[str, Any],
        context: TranslationContext,
    ) -> Dict[str, str]:
        """Translate deployment action."""
        target = data.get("target", "production")
        action = data.get("action", "deploy")

        title = f"Deploy to {target}"
        description = f"Publish changes to {target} environment"
        impact = "Users will see the new changes"

        return {
            "title": title,
            "description": description,
            "impact": impact,
        }

    def _translate_default(
        self,
        data: Dict[str, Any],
        context: TranslationContext,
    ) -> Dict[str, str]:
        """Default translation."""
        return {
            "title": data.get("title", "Action Required"),
            "description": data.get("description", "A decision needs to be made"),
            "impact": data.get("impact", ""),
        }

    def register_term(
        self,
        term: str,
        translation: str,
        level: str = "beginner",
    ) -> None:
        """Register a custom term translation."""
        if level in self._translations:
            self._translations[level][term] = translation

    def register_error_pattern(
        self,
        pattern: str,
        translation: str,
    ) -> None:
        """Register a custom error pattern."""
        self._error_patterns.append((pattern, translation))


# Singleton instance
_translator_instance: Optional[TechDecisionTranslator] = None


def get_tech_translator() -> TechDecisionTranslator:
    """Get the singleton translator."""
    global _translator_instance
    if _translator_instance is None:
        _translator_instance = TechDecisionTranslator()
    return _translator_instance
