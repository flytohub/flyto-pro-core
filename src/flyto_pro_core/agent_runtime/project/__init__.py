"""
Project Module - Three-layer tracking and state management.

Goal → Task → Step hierarchy with persistent state.
"""

from .goal_task_step import (
    Goal,
    Task,
    Step,
    StepStatus,
    TaskStatus,
    GoalStatus,
    StepArtifact,
    TaskChecklist,
)
from .project_state import (
    ProjectState,
    ProjectConfig,
    ProjectStateManager,
)
from .flyto_directory import (
    FlytoDirectory,
    DirectoryStructure,
)

__all__ = [
    # Goal-Task-Step
    "Goal",
    "Task",
    "Step",
    "StepStatus",
    "TaskStatus",
    "GoalStatus",
    "StepArtifact",
    "TaskChecklist",
    # State
    "ProjectState",
    "ProjectConfig",
    "ProjectStateManager",
    # Directory
    "FlytoDirectory",
    "DirectoryStructure",
]
