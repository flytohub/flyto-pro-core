"""
Project State - Persistent project memory.

Stored in .flyto/ directory for long-term state.
"""

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..contracts.contract_meta import ContractMeta
from .goal_task_step import Goal, GoalStatus

logger = logging.getLogger(__name__)


@dataclass
class ProjectConfig:
    """Project configuration."""

    # Identity
    project_id: str = ""
    project_name: str = ""
    project_path: str = ""

    # Settings
    default_stop_policy: Dict[str, Any] = field(default_factory=dict)
    required_capabilities: List[str] = field(default_factory=list)
    excluded_paths: List[str] = field(default_factory=list)

    # AI Settings
    preferred_model: str = "gpt-4"
    max_tokens_per_step: int = 4000
    temperature: float = 0.7

    # EMS Settings
    ems_enabled: bool = True
    ems_scope: str = "project"  # global, project, env

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def __post_init__(self):
        if not self.project_id:
            self.project_id = str(uuid.uuid4())[:12]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "project_path": self.project_path,
            "default_stop_policy": self.default_stop_policy,
            "required_capabilities": self.required_capabilities,
            "excluded_paths": self.excluded_paths,
            "preferred_model": self.preferred_model,
            "max_tokens_per_step": self.max_tokens_per_step,
            "temperature": self.temperature,
            "ems_enabled": self.ems_enabled,
            "ems_scope": self.ems_scope,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectConfig":
        return cls(
            project_id=data.get("project_id", ""),
            project_name=data.get("project_name", ""),
            project_path=data.get("project_path", ""),
            default_stop_policy=data.get("default_stop_policy", {}),
            required_capabilities=data.get("required_capabilities", []),
            excluded_paths=data.get("excluded_paths", []),
            preferred_model=data.get("preferred_model", "gpt-4"),
            max_tokens_per_step=data.get("max_tokens_per_step", 4000),
            temperature=data.get("temperature", 0.7),
            ems_enabled=data.get("ems_enabled", True),
            ems_scope=data.get("ems_scope", "project"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


@dataclass
class ProjectState:
    """
    Complete project state.

    This is the "long-term memory" for the AI Agent.
    """

    # Metadata
    meta: ContractMeta = field(
        default_factory=lambda: ContractMeta(
            contract_name="ProjectState",
            version="1.0.0",
            compatible_with=["^1.0"],
        )
    )

    # Config
    config: ProjectConfig = field(default_factory=ProjectConfig)

    # Goals (current and historical)
    active_goals: List[Goal] = field(default_factory=list)
    completed_goals: List[Goal] = field(default_factory=list)

    # Current session
    session_id: str = ""
    session_started_at: str = ""

    # Statistics
    total_steps_executed: int = 0
    total_steps_succeeded: int = 0
    total_steps_failed: int = 0
    total_execution_time_ms: int = 0

    # EMS references
    ems_patterns_applied: List[str] = field(default_factory=list)

    # Last known state
    last_observation_id: Optional[str] = None
    last_verification_id: Optional[str] = None

    def __post_init__(self):
        if not self.session_id:
            self.session_id = str(uuid.uuid4())[:8]
            self.session_started_at = datetime.utcnow().isoformat()

    def add_goal(self, goal: Goal) -> None:
        """Add a new goal."""
        goal.project_id = self.config.project_id
        self.active_goals.append(goal)

    def complete_goal(self, goal_id: str) -> Optional[Goal]:
        """Move goal from active to completed."""
        for i, goal in enumerate(self.active_goals):
            if goal.goal_id == goal_id:
                goal.complete()
                self.completed_goals.append(goal)
                self.active_goals.pop(i)
                return goal
        return None

    def get_active_goal(self) -> Optional[Goal]:
        """Get the currently active goal."""
        for goal in self.active_goals:
            if goal.status == GoalStatus.ACTIVE:
                return goal
        return self.active_goals[0] if self.active_goals else None

    def record_step_execution(
        self,
        succeeded: bool,
        execution_time_ms: int,
    ) -> None:
        """Record step execution statistics."""
        self.total_steps_executed += 1
        if succeeded:
            self.total_steps_succeeded += 1
        else:
            self.total_steps_failed += 1
        self.total_execution_time_ms += execution_time_ms

    def get_statistics(self) -> Dict[str, Any]:
        """Get project statistics."""
        success_rate = (
            self.total_steps_succeeded / self.total_steps_executed * 100
            if self.total_steps_executed > 0
            else 0
        )

        return {
            "project_id": self.config.project_id,
            "session_id": self.session_id,
            "active_goals": len(self.active_goals),
            "completed_goals": len(self.completed_goals),
            "total_steps_executed": self.total_steps_executed,
            "total_steps_succeeded": self.total_steps_succeeded,
            "total_steps_failed": self.total_steps_failed,
            "success_rate": success_rate,
            "total_execution_time_ms": self.total_execution_time_ms,
            "ems_patterns_applied": len(self.ems_patterns_applied),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "meta": self.meta.to_dict(),
            "config": self.config.to_dict(),
            "active_goals": [g.to_dict() for g in self.active_goals],
            "completed_goals": [g.to_dict() for g in self.completed_goals],
            "session_id": self.session_id,
            "session_started_at": self.session_started_at,
            "total_steps_executed": self.total_steps_executed,
            "total_steps_succeeded": self.total_steps_succeeded,
            "total_steps_failed": self.total_steps_failed,
            "total_execution_time_ms": self.total_execution_time_ms,
            "ems_patterns_applied": self.ems_patterns_applied,
            "last_observation_id": self.last_observation_id,
            "last_verification_id": self.last_verification_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectState":
        return cls(
            meta=ContractMeta.from_dict(data.get("meta", {})),
            config=ProjectConfig.from_dict(data.get("config", {})),
            active_goals=[Goal.from_dict(g) for g in data.get("active_goals", [])],
            completed_goals=[
                Goal.from_dict(g) for g in data.get("completed_goals", [])
            ],
            session_id=data.get("session_id", ""),
            session_started_at=data.get("session_started_at", ""),
            total_steps_executed=data.get("total_steps_executed", 0),
            total_steps_succeeded=data.get("total_steps_succeeded", 0),
            total_steps_failed=data.get("total_steps_failed", 0),
            total_execution_time_ms=data.get("total_execution_time_ms", 0),
            ems_patterns_applied=data.get("ems_patterns_applied", []),
            last_observation_id=data.get("last_observation_id"),
            last_verification_id=data.get("last_verification_id"),
        )


class ProjectStateManager:
    """
    Manages project state persistence.

    Handles .flyto/ directory structure and state loading/saving.
    """

    def __init__(self, project_path: str):
        self.project_path = project_path
        self.flyto_path = os.path.join(project_path, ".flyto")
        self._state: Optional[ProjectState] = None

    def init_project(self, project_name: str = "") -> ProjectState:
        """Initialize a new project."""
        # Create .flyto directory structure
        os.makedirs(self.flyto_path, exist_ok=True)
        os.makedirs(os.path.join(self.flyto_path, "goals"), exist_ok=True)
        os.makedirs(os.path.join(self.flyto_path, "artifacts"), exist_ok=True)
        os.makedirs(os.path.join(self.flyto_path, "ems"), exist_ok=True)
        os.makedirs(os.path.join(self.flyto_path, "logs"), exist_ok=True)

        # Create config
        config = ProjectConfig(
            project_name=project_name or os.path.basename(self.project_path),
            project_path=self.project_path,
        )

        # Create state
        self._state = ProjectState(config=config)

        # Save initial state
        self.save()

        logger.info(f"Initialized project: {config.project_id}")
        return self._state

    def load(self) -> Optional[ProjectState]:
        """Load project state from .flyto/state.json."""
        state_file = os.path.join(self.flyto_path, "state.json")

        if not os.path.exists(state_file):
            return None

        try:
            with open(state_file, "r") as f:
                data = json.load(f)
            self._state = ProjectState.from_dict(data)
            logger.info(f"Loaded project state: {self._state.config.project_id}")
            return self._state
        except Exception as e:
            logger.error(f"Failed to load project state: {e}")
            return None

    def save(self) -> bool:
        """Save project state to .flyto/state.json."""
        if not self._state:
            return False

        state_file = os.path.join(self.flyto_path, "state.json")

        try:
            # Update timestamp
            self._state.config.updated_at = datetime.utcnow().isoformat()

            with open(state_file, "w") as f:
                json.dump(self._state.to_dict(), f, indent=2)

            logger.debug(f"Saved project state: {self._state.config.project_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save project state: {e}")
            return False

    def get_state(self) -> Optional[ProjectState]:
        """Get current state, loading if necessary."""
        if not self._state:
            self._state = self.load()
        return self._state

    def get_or_init(self, project_name: str = "") -> ProjectState:
        """Get existing state or initialize new project."""
        state = self.get_state()
        if state:
            return state
        return self.init_project(project_name)

    def save_goal(self, goal: Goal) -> bool:
        """Save goal to separate file for history."""
        goal_file = os.path.join(
            self.flyto_path, "goals", f"{goal.goal_id}.json"
        )

        try:
            with open(goal_file, "w") as f:
                json.dump(goal.to_dict(), f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save goal: {e}")
            return False

    def load_goal(self, goal_id: str) -> Optional[Goal]:
        """Load goal from history."""
        goal_file = os.path.join(self.flyto_path, "goals", f"{goal_id}.json")

        if not os.path.exists(goal_file):
            return None

        try:
            with open(goal_file, "r") as f:
                data = json.load(f)
            return Goal.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load goal: {e}")
            return None

    def list_goals(self) -> List[str]:
        """List all goal IDs in history."""
        goals_dir = os.path.join(self.flyto_path, "goals")
        if not os.path.exists(goals_dir):
            return []

        return [
            f[:-5]  # Remove .json
            for f in os.listdir(goals_dir)
            if f.endswith(".json")
        ]


# Singleton per project path
_managers: Dict[str, ProjectStateManager] = {}


def get_project_state_manager(project_path: str) -> ProjectStateManager:
    """Get or create project state manager for path."""
    if project_path not in _managers:
        _managers[project_path] = ProjectStateManager(project_path)
    return _managers[project_path]
