"""
Progress Tracker - Real-time progress updates for UI.

Provides structured progress data at multiple levels:
- Goal level (overall project progress)
- Task level (current task progress)
- Step level (current step progress)
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ProgressLevel(Enum):
    """Level of progress update."""

    GOAL = "goal"
    TASK = "task"
    STEP = "step"


@dataclass
class ProgressUpdate:
    """A single progress update."""

    update_id: str = ""
    level: ProgressLevel = ProgressLevel.STEP
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Identity
    goal_id: str = ""
    task_id: str = ""
    step_id: str = ""

    # Progress
    status: str = ""  # pending, in_progress, completed, failed
    progress_percent: float = 0.0
    message: str = ""

    # Details
    current_action: str = ""
    items_completed: int = 0
    items_total: int = 0

    # Timing
    started_at: Optional[str] = None
    estimated_remaining_ms: int = 0

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.update_id:
            self.update_id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "update_id": self.update_id,
            "level": self.level.value,
            "timestamp": self.timestamp,
            "goal_id": self.goal_id,
            "task_id": self.task_id,
            "step_id": self.step_id,
            "status": self.status,
            "progress_percent": self.progress_percent,
            "message": self.message,
            "current_action": self.current_action,
            "items_completed": self.items_completed,
            "items_total": self.items_total,
            "started_at": self.started_at,
            "estimated_remaining_ms": self.estimated_remaining_ms,
            "metadata": self.metadata,
        }


# Type for progress callback
ProgressCallback = Callable[[ProgressUpdate], None]


class ProgressTracker:
    """
    Tracks and broadcasts progress updates.

    Maintains state for goals, tasks, and steps, and notifies
    listeners of changes.
    """

    def __init__(self):
        self._callbacks: List[ProgressCallback] = []
        self._current_goal_id: str = ""
        self._current_task_id: str = ""
        self._current_step_id: str = ""
        self._history: List[ProgressUpdate] = []
        self._goal_progress: Dict[str, Dict[str, Any]] = {}
        self._task_progress: Dict[str, Dict[str, Any]] = {}
        self._step_progress: Dict[str, Dict[str, Any]] = {}

    def add_callback(self, callback: ProgressCallback) -> None:
        """Add a progress callback."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: ProgressCallback) -> None:
        """Remove a progress callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify(self, update: ProgressUpdate) -> None:
        """Notify all callbacks of update."""
        self._history.append(update)
        for callback in self._callbacks:
            try:
                callback(update)
            except Exception:
                pass  # Don't let callback errors stop progress

    def start_goal(
        self,
        goal_id: str,
        name: str,
        total_tasks: int,
    ) -> ProgressUpdate:
        """Start tracking a goal."""
        self._current_goal_id = goal_id
        self._goal_progress[goal_id] = {
            "name": name,
            "total_tasks": total_tasks,
            "completed_tasks": 0,
            "started_at": datetime.utcnow().isoformat(),
        }

        update = ProgressUpdate(
            level=ProgressLevel.GOAL,
            goal_id=goal_id,
            status="in_progress",
            message=f"Starting: {name}",
            items_total=total_tasks,
            started_at=self._goal_progress[goal_id]["started_at"],
        )

        self._notify(update)
        return update

    def update_goal(
        self,
        goal_id: str,
        completed_tasks: int,
        message: str = "",
    ) -> ProgressUpdate:
        """Update goal progress."""
        if goal_id not in self._goal_progress:
            return self.start_goal(goal_id, "Unknown Goal", completed_tasks)

        progress = self._goal_progress[goal_id]
        progress["completed_tasks"] = completed_tasks

        percent = (
            completed_tasks / progress["total_tasks"] * 100
            if progress["total_tasks"] > 0
            else 0
        )

        update = ProgressUpdate(
            level=ProgressLevel.GOAL,
            goal_id=goal_id,
            status="in_progress",
            progress_percent=percent,
            message=message or f"Progress: {completed_tasks}/{progress['total_tasks']} tasks",
            items_completed=completed_tasks,
            items_total=progress["total_tasks"],
            started_at=progress["started_at"],
        )

        self._notify(update)
        return update

    def complete_goal(
        self,
        goal_id: str,
        success: bool = True,
        message: str = "",
    ) -> ProgressUpdate:
        """Complete goal tracking."""
        if goal_id not in self._goal_progress:
            self._goal_progress[goal_id] = {"total_tasks": 0, "completed_tasks": 0}

        progress = self._goal_progress[goal_id]

        update = ProgressUpdate(
            level=ProgressLevel.GOAL,
            goal_id=goal_id,
            status="completed" if success else "failed",
            progress_percent=100.0 if success else progress.get("completed_tasks", 0) / max(progress.get("total_tasks", 1), 1) * 100,
            message=message or ("Goal completed" if success else "Goal failed"),
            items_completed=progress.get("completed_tasks", 0),
            items_total=progress.get("total_tasks", 0),
        )

        self._notify(update)
        return update

    def start_task(
        self,
        task_id: str,
        name: str,
        total_steps: int,
        goal_id: str = "",
    ) -> ProgressUpdate:
        """Start tracking a task."""
        self._current_task_id = task_id
        goal_id = goal_id or self._current_goal_id

        self._task_progress[task_id] = {
            "name": name,
            "goal_id": goal_id,
            "total_steps": total_steps,
            "completed_steps": 0,
            "started_at": datetime.utcnow().isoformat(),
        }

        update = ProgressUpdate(
            level=ProgressLevel.TASK,
            goal_id=goal_id,
            task_id=task_id,
            status="in_progress",
            message=f"Starting task: {name}",
            items_total=total_steps,
            started_at=self._task_progress[task_id]["started_at"],
        )

        self._notify(update)
        return update

    def update_task(
        self,
        task_id: str,
        completed_steps: int,
        current_action: str = "",
        message: str = "",
    ) -> ProgressUpdate:
        """Update task progress."""
        if task_id not in self._task_progress:
            return self.start_task(task_id, "Unknown Task", completed_steps)

        progress = self._task_progress[task_id]
        progress["completed_steps"] = completed_steps

        percent = (
            completed_steps / progress["total_steps"] * 100
            if progress["total_steps"] > 0
            else 0
        )

        update = ProgressUpdate(
            level=ProgressLevel.TASK,
            goal_id=progress.get("goal_id", ""),
            task_id=task_id,
            status="in_progress",
            progress_percent=percent,
            message=message or f"Step {completed_steps}/{progress['total_steps']}",
            current_action=current_action,
            items_completed=completed_steps,
            items_total=progress["total_steps"],
            started_at=progress["started_at"],
        )

        self._notify(update)
        return update

    def complete_task(
        self,
        task_id: str,
        success: bool = True,
        message: str = "",
    ) -> ProgressUpdate:
        """Complete task tracking."""
        if task_id not in self._task_progress:
            self._task_progress[task_id] = {
                "goal_id": self._current_goal_id,
                "total_steps": 0,
                "completed_steps": 0,
            }

        progress = self._task_progress[task_id]

        update = ProgressUpdate(
            level=ProgressLevel.TASK,
            goal_id=progress.get("goal_id", ""),
            task_id=task_id,
            status="completed" if success else "failed",
            progress_percent=100.0 if success else 0,
            message=message or ("Task completed" if success else "Task failed"),
            items_completed=progress.get("completed_steps", 0),
            items_total=progress.get("total_steps", 0),
        )

        self._notify(update)

        # Update parent goal
        if progress.get("goal_id") in self._goal_progress:
            goal_progress = self._goal_progress[progress["goal_id"]]
            if success:
                goal_progress["completed_tasks"] = goal_progress.get("completed_tasks", 0) + 1
                self.update_goal(progress["goal_id"], goal_progress["completed_tasks"])

        return update

    def step_started(
        self,
        step_id: str,
        module_id: str,
        description: str = "",
        task_id: str = "",
    ) -> ProgressUpdate:
        """Mark step as started."""
        self._current_step_id = step_id
        task_id = task_id or self._current_task_id

        self._step_progress[step_id] = {
            "task_id": task_id,
            "module_id": module_id,
            "description": description,
            "started_at": datetime.utcnow().isoformat(),
        }

        # Get goal_id from task
        goal_id = ""
        if task_id in self._task_progress:
            goal_id = self._task_progress[task_id].get("goal_id", "")

        update = ProgressUpdate(
            level=ProgressLevel.STEP,
            goal_id=goal_id,
            task_id=task_id,
            step_id=step_id,
            status="in_progress",
            current_action=module_id,
            message=description or f"Executing: {module_id}",
            started_at=self._step_progress[step_id]["started_at"],
        )

        self._notify(update)
        return update

    def step_completed(
        self,
        step_id: str,
        success: bool = True,
        message: str = "",
        duration_ms: int = 0,
    ) -> ProgressUpdate:
        """Mark step as completed."""
        if step_id not in self._step_progress:
            self._step_progress[step_id] = {
                "task_id": self._current_task_id,
                "module_id": "unknown",
            }

        progress = self._step_progress[step_id]
        task_id = progress.get("task_id", "")

        # Get goal_id from task
        goal_id = ""
        if task_id in self._task_progress:
            goal_id = self._task_progress[task_id].get("goal_id", "")

        update = ProgressUpdate(
            level=ProgressLevel.STEP,
            goal_id=goal_id,
            task_id=task_id,
            step_id=step_id,
            status="completed" if success else "failed",
            progress_percent=100.0 if success else 0,
            message=message or ("Step completed" if success else "Step failed"),
            current_action=progress.get("module_id", ""),
            metadata={"duration_ms": duration_ms},
        )

        self._notify(update)

        # Update parent task
        if success and task_id in self._task_progress:
            task_progress = self._task_progress[task_id]
            task_progress["completed_steps"] = task_progress.get("completed_steps", 0) + 1
            self.update_task(task_id, task_progress["completed_steps"])

        return update

    def get_current_state(self) -> Dict[str, Any]:
        """Get current progress state."""
        return {
            "current_goal_id": self._current_goal_id,
            "current_task_id": self._current_task_id,
            "current_step_id": self._current_step_id,
            "goals": self._goal_progress,
            "tasks": self._task_progress,
            "steps": self._step_progress,
        }

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get progress history."""
        return [u.to_dict() for u in self._history[-limit:]]


# Singleton instance
_tracker_instance: Optional[ProgressTracker] = None


def get_progress_tracker() -> ProgressTracker:
    """Get the singleton progress tracker."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = ProgressTracker()
    return _tracker_instance
