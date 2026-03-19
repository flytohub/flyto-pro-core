"""
Goal-Task-Step - Three-layer tracking hierarchy.

Goal: User intent (e.g., "Build a login page")
Task: Decomposed work unit (e.g., "Create form component")
Step: Atomic action (e.g., "Write LoginForm.tsx")
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..contracts.contract_meta import ContractMeta


class StepStatus(Enum):
    """Status of a single step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class TaskStatus(Enum):
    """Status of a task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class GoalStatus(Enum):
    """Status of a goal."""

    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


@dataclass
class StepArtifact:
    """Artifact produced by a step."""

    artifact_id: str = ""
    artifact_type: str = ""  # file, screenshot, log, db_change
    path: str = ""
    hash: str = ""
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def __post_init__(self):
        if not self.artifact_id:
            self.artifact_id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "path": self.path,
            "hash": self.hash,
            "size_bytes": self.size_bytes,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StepArtifact":
        return cls(
            artifact_id=data.get("artifact_id", ""),
            artifact_type=data.get("artifact_type", ""),
            path=data.get("path", ""),
            hash=data.get("hash", ""),
            size_bytes=data.get("size_bytes", 0),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", ""),
        )


@dataclass
class Step:
    """
    Atomic action in a task.

    Each step maps to one module execution.
    """

    step_id: str = ""
    task_id: str = ""
    module_id: str = ""
    description: str = ""
    status: StepStatus = StepStatus.PENDING

    # Execution
    params: Dict[str, Any] = field(default_factory=dict)
    result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    # Timing
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: int = 0

    # Artifacts
    artifacts: List[StepArtifact] = field(default_factory=list)

    # Verification
    observation_id: Optional[str] = None
    verification_id: Optional[str] = None
    verification_passed: Optional[bool] = None

    # Order
    order: int = 0
    retry_count: int = 0
    max_retries: int = 3

    def __post_init__(self):
        if not self.step_id:
            self.step_id = str(uuid.uuid4())[:8]

    def start(self) -> None:
        """Mark step as started."""
        self.status = StepStatus.IN_PROGRESS
        self.started_at = datetime.utcnow().isoformat()

    def complete(self, result: Dict[str, Any]) -> None:
        """Mark step as completed."""
        self.status = StepStatus.COMPLETED
        self.completed_at = datetime.utcnow().isoformat()
        self.result = result
        if self.started_at:
            start = datetime.fromisoformat(self.started_at)
            end = datetime.fromisoformat(self.completed_at)
            self.duration_ms = int((end - start).total_seconds() * 1000)

    def fail(self, error: str) -> None:
        """Mark step as failed."""
        self.status = StepStatus.FAILED
        self.error = error
        self.completed_at = datetime.utcnow().isoformat()

    def add_artifact(self, artifact: StepArtifact) -> None:
        """Add artifact to step."""
        self.artifacts.append(artifact)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "task_id": self.task_id,
            "module_id": self.module_id,
            "description": self.description,
            "status": self.status.value,
            "params": self.params,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "observation_id": self.observation_id,
            "verification_id": self.verification_id,
            "verification_passed": self.verification_passed,
            "order": self.order,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Step":
        return cls(
            step_id=data.get("step_id", ""),
            task_id=data.get("task_id", ""),
            module_id=data.get("module_id", ""),
            description=data.get("description", ""),
            status=StepStatus(data.get("status", "pending")),
            params=data.get("params", {}),
            result=data.get("result", {}),
            error=data.get("error"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            duration_ms=data.get("duration_ms", 0),
            artifacts=[
                StepArtifact.from_dict(a) for a in data.get("artifacts", [])
            ],
            observation_id=data.get("observation_id"),
            verification_id=data.get("verification_id"),
            verification_passed=data.get("verification_passed"),
            order=data.get("order", 0),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
        )


@dataclass
class TaskChecklist:
    """Checklist for task completion."""

    items: List[Dict[str, Any]] = field(default_factory=list)
    auto_generated: bool = True

    def add_item(
        self,
        description: str,
        required: bool = True,
        assertion_id: Optional[str] = None,
    ) -> str:
        """Add checklist item."""
        item_id = str(uuid.uuid4())[:8]
        self.items.append({
            "item_id": item_id,
            "description": description,
            "required": required,
            "checked": False,
            "assertion_id": assertion_id,
            "checked_at": None,
        })
        return item_id

    def check_item(self, item_id: str, passed: bool = True) -> None:
        """Mark item as checked."""
        for item in self.items:
            if item["item_id"] == item_id:
                item["checked"] = passed
                item["checked_at"] = datetime.utcnow().isoformat()
                break

    def is_complete(self) -> bool:
        """Check if all required items are checked."""
        required = [i for i in self.items if i["required"]]
        return all(i["checked"] for i in required)

    def get_progress(self) -> Dict[str, Any]:
        """Get completion progress."""
        total = len(self.items)
        checked = sum(1 for i in self.items if i["checked"])
        required_total = sum(1 for i in self.items if i["required"])
        required_checked = sum(
            1 for i in self.items if i["required"] and i["checked"]
        )

        return {
            "total": total,
            "checked": checked,
            "percentage": (checked / total * 100) if total > 0 else 100,
            "required_total": required_total,
            "required_checked": required_checked,
            "is_complete": self.is_complete(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": self.items,
            "auto_generated": self.auto_generated,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskChecklist":
        return cls(
            items=data.get("items", []),
            auto_generated=data.get("auto_generated", True),
        )


@dataclass
class Task:
    """
    Decomposed work unit.

    Contains multiple steps, has a checklist for completion.
    """

    # Metadata
    meta: ContractMeta = field(
        default_factory=lambda: ContractMeta(
            contract_name="Task",
            version="1.0.0",
        )
    )

    # Identity
    task_id: str = ""
    goal_id: str = ""
    name: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING

    # Steps
    steps: List[Step] = field(default_factory=list)
    current_step_index: int = 0

    # Checklist
    checklist: TaskChecklist = field(default_factory=TaskChecklist)

    # Dependencies
    depends_on: List[str] = field(default_factory=list)  # Other task IDs
    blocked_by: List[str] = field(default_factory=list)

    # Timing
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    # Priority
    priority: int = 0  # Higher = more important
    order: int = 0

    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.task_id:
            self.task_id = str(uuid.uuid4())[:8]

    def add_step(self, step: Step) -> None:
        """Add step to task."""
        step.task_id = self.task_id
        step.order = len(self.steps)
        self.steps.append(step)

    def get_current_step(self) -> Optional[Step]:
        """Get current step."""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def advance_step(self) -> Optional[Step]:
        """Move to next step."""
        self.current_step_index += 1
        return self.get_current_step()

    def start(self) -> None:
        """Start task."""
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.utcnow().isoformat()

    def complete(self) -> None:
        """Complete task."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.utcnow().isoformat()

    def fail(self) -> None:
        """Fail task."""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.utcnow().isoformat()

    def get_progress(self) -> Dict[str, Any]:
        """Get task progress."""
        total_steps = len(self.steps)
        completed_steps = sum(
            1 for s in self.steps if s.status == StepStatus.COMPLETED
        )
        failed_steps = sum(1 for s in self.steps if s.status == StepStatus.FAILED)

        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "step_progress": (
                completed_steps / total_steps * 100 if total_steps > 0 else 0
            ),
            "checklist": self.checklist.get_progress(),
            "current_step": self.current_step_index,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "meta": self.meta.to_dict(),
            "task_id": self.task_id,
            "goal_id": self.goal_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "steps": [s.to_dict() for s in self.steps],
            "current_step_index": self.current_step_index,
            "checklist": self.checklist.to_dict(),
            "depends_on": self.depends_on,
            "blocked_by": self.blocked_by,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "priority": self.priority,
            "order": self.order,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        return cls(
            meta=ContractMeta.from_dict(data.get("meta", {})),
            task_id=data.get("task_id", ""),
            goal_id=data.get("goal_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            status=TaskStatus(data.get("status", "pending")),
            steps=[Step.from_dict(s) for s in data.get("steps", [])],
            current_step_index=data.get("current_step_index", 0),
            checklist=TaskChecklist.from_dict(data.get("checklist", {})),
            depends_on=data.get("depends_on", []),
            blocked_by=data.get("blocked_by", []),
            created_at=data.get("created_at", ""),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            priority=data.get("priority", 0),
            order=data.get("order", 0),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Goal:
    """
    User intent - the top level objective.

    A goal contains multiple tasks that achieve it.
    """

    # Metadata
    meta: ContractMeta = field(
        default_factory=lambda: ContractMeta(
            contract_name="Goal",
            version="1.0.0",
        )
    )

    # Identity
    goal_id: str = ""
    name: str = ""
    description: str = ""
    user_intent: str = ""  # Original user request
    status: GoalStatus = GoalStatus.ACTIVE

    # Tasks
    tasks: List[Task] = field(default_factory=list)

    # Success criteria
    success_criteria: List[str] = field(default_factory=list)

    # Timing
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    # Context
    project_id: Optional[str] = None
    parent_goal_id: Optional[str] = None  # For sub-goals

    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.goal_id:
            self.goal_id = str(uuid.uuid4())[:8]

    def add_task(self, task: Task) -> None:
        """Add task to goal."""
        task.goal_id = self.goal_id
        task.order = len(self.tasks)
        self.tasks.append(task)

    def get_active_task(self) -> Optional[Task]:
        """Get currently active task."""
        for task in self.tasks:
            if task.status == TaskStatus.IN_PROGRESS:
                return task
        # Return first pending task
        for task in self.tasks:
            if task.status == TaskStatus.PENDING:
                return task
        return None

    def get_progress(self) -> Dict[str, Any]:
        """Get goal progress."""
        total_tasks = len(self.tasks)
        completed_tasks = sum(
            1 for t in self.tasks if t.status == TaskStatus.COMPLETED
        )
        failed_tasks = sum(1 for t in self.tasks if t.status == TaskStatus.FAILED)

        # Calculate step-level progress
        total_steps = sum(len(t.steps) for t in self.tasks)
        completed_steps = sum(
            sum(1 for s in t.steps if s.status == StepStatus.COMPLETED)
            for t in self.tasks
        )

        return {
            "goal_id": self.goal_id,
            "status": self.status.value,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "task_progress": (
                completed_tasks / total_tasks * 100 if total_tasks > 0 else 0
            ),
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "step_progress": (
                completed_steps / total_steps * 100 if total_steps > 0 else 0
            ),
        }

    def complete(self) -> None:
        """Mark goal as completed."""
        self.status = GoalStatus.COMPLETED
        self.completed_at = datetime.utcnow().isoformat()

    def fail(self) -> None:
        """Mark goal as failed."""
        self.status = GoalStatus.FAILED
        self.completed_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "meta": self.meta.to_dict(),
            "goal_id": self.goal_id,
            "name": self.name,
            "description": self.description,
            "user_intent": self.user_intent,
            "status": self.status.value,
            "tasks": [t.to_dict() for t in self.tasks],
            "success_criteria": self.success_criteria,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "project_id": self.project_id,
            "parent_goal_id": self.parent_goal_id,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Goal":
        return cls(
            meta=ContractMeta.from_dict(data.get("meta", {})),
            goal_id=data.get("goal_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            user_intent=data.get("user_intent", ""),
            status=GoalStatus(data.get("status", "active")),
            tasks=[Task.from_dict(t) for t in data.get("tasks", [])],
            success_criteria=data.get("success_criteria", []),
            created_at=data.get("created_at", ""),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            project_id=data.get("project_id"),
            parent_goal_id=data.get("parent_goal_id"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )
