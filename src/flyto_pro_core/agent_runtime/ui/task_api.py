"""
Task API - API for task management from frontend.

Provides endpoints for:
- Task reordering (drag-and-drop)
- Task status updates
- Task CRUD operations
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..project.goal_task_step import Goal, Task, TaskStatus, Step, StepStatus


@dataclass
class TaskReorderRequest:
    """Request to reorder tasks."""

    goal_id: str
    task_ids: List[str]  # New order of task IDs
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class TaskUpdateRequest:
    """Request to update a task."""

    task_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TaskCreateRequest:
    """Request to create a task."""

    goal_id: str
    name: str
    description: str = ""
    priority: int = 0
    depends_on: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    steps: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class TaskResponse:
    """Response for task operations."""

    success: bool = True
    message: str = ""
    task: Optional[Dict[str, Any]] = None
    tasks: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


class TaskAPI:
    """
    API for managing tasks from the frontend.

    Provides a clean interface for task operations
    that can be called from UI components.
    """

    def __init__(self, state_manager=None):
        self._state_manager = state_manager
        self._goals: Dict[str, Goal] = {}

    def set_state_manager(self, manager) -> None:
        """Set the project state manager."""
        self._state_manager = manager

    def register_goal(self, goal: Goal) -> None:
        """Register a goal for task management."""
        self._goals[goal.goal_id] = goal

    def get_tasks(self, goal_id: str) -> TaskResponse:
        """Get all tasks for a goal."""
        goal = self._goals.get(goal_id)
        if not goal:
            return TaskResponse(
                success=False,
                error=f"Goal not found: {goal_id}",
            )

        return TaskResponse(
            success=True,
            tasks=[t.to_dict() for t in goal.tasks],
        )

    def get_task(self, task_id: str) -> TaskResponse:
        """Get a single task."""
        for goal in self._goals.values():
            for task in goal.tasks:
                if task.task_id == task_id:
                    return TaskResponse(
                        success=True,
                        task=task.to_dict(),
                    )

        return TaskResponse(
            success=False,
            error=f"Task not found: {task_id}",
        )

    def create_task(self, request: TaskCreateRequest) -> TaskResponse:
        """Create a new task."""
        goal = self._goals.get(request.goal_id)
        if not goal:
            return TaskResponse(
                success=False,
                error=f"Goal not found: {request.goal_id}",
            )

        # Create task
        task = Task(
            goal_id=request.goal_id,
            name=request.name,
            description=request.description,
            priority=request.priority,
            depends_on=request.depends_on,
            tags=request.tags,
        )

        # Add steps if provided
        for step_data in request.steps:
            step = Step(
                module_id=step_data.get("module_id", ""),
                description=step_data.get("description", ""),
                params=step_data.get("params", {}),
            )
            task.add_step(step)

        # Add to goal
        goal.add_task(task)

        return TaskResponse(
            success=True,
            message="Task created successfully",
            task=task.to_dict(),
        )

    def update_task(self, request: TaskUpdateRequest) -> TaskResponse:
        """Update a task."""
        for goal in self._goals.values():
            for task in goal.tasks:
                if task.task_id == request.task_id:
                    # Update fields
                    if request.name is not None:
                        task.name = request.name
                    if request.description is not None:
                        task.description = request.description
                    if request.status is not None:
                        task.status = TaskStatus(request.status)
                    if request.priority is not None:
                        task.priority = request.priority
                    if request.tags is not None:
                        task.tags = request.tags
                    if request.metadata is not None:
                        task.metadata.update(request.metadata)

                    return TaskResponse(
                        success=True,
                        message="Task updated successfully",
                        task=task.to_dict(),
                    )

        return TaskResponse(
            success=False,
            error=f"Task not found: {request.task_id}",
        )

    def delete_task(self, task_id: str) -> TaskResponse:
        """Delete a task."""
        for goal in self._goals.values():
            for i, task in enumerate(goal.tasks):
                if task.task_id == task_id:
                    goal.tasks.pop(i)
                    return TaskResponse(
                        success=True,
                        message="Task deleted successfully",
                    )

        return TaskResponse(
            success=False,
            error=f"Task not found: {task_id}",
        )

    def reorder_tasks(self, request: TaskReorderRequest) -> TaskResponse:
        """Reorder tasks within a goal."""
        goal = self._goals.get(request.goal_id)
        if not goal:
            return TaskResponse(
                success=False,
                error=f"Goal not found: {request.goal_id}",
            )

        # Validate all task IDs exist
        existing_ids = {t.task_id for t in goal.tasks}
        requested_ids = set(request.task_ids)

        if existing_ids != requested_ids:
            missing = existing_ids - requested_ids
            extra = requested_ids - existing_ids
            return TaskResponse(
                success=False,
                error=f"Task ID mismatch. Missing: {missing}, Extra: {extra}",
            )

        # Create task lookup
        task_map = {t.task_id: t for t in goal.tasks}

        # Reorder
        goal.tasks = [task_map[tid] for tid in request.task_ids]

        # Update order field
        for i, task in enumerate(goal.tasks):
            task.order = i

        return TaskResponse(
            success=True,
            message="Tasks reordered successfully",
            tasks=[t.to_dict() for t in goal.tasks],
        )

    def move_task(
        self,
        task_id: str,
        new_position: int,
    ) -> TaskResponse:
        """Move a task to a new position."""
        for goal in self._goals.values():
            for i, task in enumerate(goal.tasks):
                if task.task_id == task_id:
                    if new_position < 0 or new_position >= len(goal.tasks):
                        return TaskResponse(
                            success=False,
                            error=f"Invalid position: {new_position}",
                        )

                    # Remove from current position
                    goal.tasks.pop(i)

                    # Insert at new position
                    goal.tasks.insert(new_position, task)

                    # Update order fields
                    for j, t in enumerate(goal.tasks):
                        t.order = j

                    return TaskResponse(
                        success=True,
                        message="Task moved successfully",
                        tasks=[t.to_dict() for t in goal.tasks],
                    )

        return TaskResponse(
            success=False,
            error=f"Task not found: {task_id}",
        )

    def start_task(self, task_id: str) -> TaskResponse:
        """Start a task."""
        for goal in self._goals.values():
            for task in goal.tasks:
                if task.task_id == task_id:
                    task.start()
                    return TaskResponse(
                        success=True,
                        message="Task started",
                        task=task.to_dict(),
                    )

        return TaskResponse(
            success=False,
            error=f"Task not found: {task_id}",
        )

    def complete_task(
        self,
        task_id: str,
        success: bool = True,
    ) -> TaskResponse:
        """Complete a task."""
        for goal in self._goals.values():
            for task in goal.tasks:
                if task.task_id == task_id:
                    if success:
                        task.complete()
                    else:
                        task.fail()

                    return TaskResponse(
                        success=True,
                        message=f"Task {'completed' if success else 'failed'}",
                        task=task.to_dict(),
                    )

        return TaskResponse(
            success=False,
            error=f"Task not found: {task_id}",
        )

    def pause_task(self, task_id: str) -> TaskResponse:
        """Pause a task."""
        for goal in self._goals.values():
            for task in goal.tasks:
                if task.task_id == task_id:
                    task.status = TaskStatus.PAUSED
                    return TaskResponse(
                        success=True,
                        message="Task paused",
                        task=task.to_dict(),
                    )

        return TaskResponse(
            success=False,
            error=f"Task not found: {task_id}",
        )

    def get_task_progress(self, task_id: str) -> TaskResponse:
        """Get task progress."""
        for goal in self._goals.values():
            for task in goal.tasks:
                if task.task_id == task_id:
                    progress = task.get_progress()
                    return TaskResponse(
                        success=True,
                        task=progress,
                    )

        return TaskResponse(
            success=False,
            error=f"Task not found: {task_id}",
        )

    def get_goal_progress(self, goal_id: str) -> TaskResponse:
        """Get goal progress."""
        goal = self._goals.get(goal_id)
        if not goal:
            return TaskResponse(
                success=False,
                error=f"Goal not found: {goal_id}",
            )

        progress = goal.get_progress()
        return TaskResponse(
            success=True,
            task=progress,
        )

    def add_step_to_task(
        self,
        task_id: str,
        module_id: str,
        description: str = "",
        params: Optional[Dict[str, Any]] = None,
    ) -> TaskResponse:
        """Add a step to a task."""
        for goal in self._goals.values():
            for task in goal.tasks:
                if task.task_id == task_id:
                    step = Step(
                        module_id=module_id,
                        description=description,
                        params=params or {},
                    )
                    task.add_step(step)

                    return TaskResponse(
                        success=True,
                        message="Step added",
                        task=task.to_dict(),
                    )

        return TaskResponse(
            success=False,
            error=f"Task not found: {task_id}",
        )


# Singleton instance
_api_instance: Optional[TaskAPI] = None


def get_task_api() -> TaskAPI:
    """Get the singleton task API."""
    global _api_instance
    if _api_instance is None:
        _api_instance = TaskAPI()
    return _api_instance
