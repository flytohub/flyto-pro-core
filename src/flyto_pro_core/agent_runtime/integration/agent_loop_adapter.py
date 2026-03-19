"""
Agent Loop Adapter - Integrates agent_runtime with AgentLoop.

This adapter wraps the existing AgentLoop to add:
- ObservationPacket collection
- DeterministicVerifier in CHECK phase
- ProjectState persistence
- EMS integration
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ..contracts import (
    PlanContract,
    CapabilityToken,
    CapabilityGuard,
    StopPolicy,
    StopPolicyChecker,
)
from ..observation import (
    ObservationPacket,
    ObservationCollector,
    get_observation_collector,
)
from ..verification import (
    DeterministicVerifier,
    VerificationReport,
    get_evidence_pipeline,
)
from ..project import (
    Goal,
    Task,
    Step,
    StepStatus,
    ProjectStateManager,
)
from ..ems import (
    EMSStore,
    compute_error_signature,
)
from ..ui import (
    ProgressTracker,
    get_progress_tracker,
)

logger = logging.getLogger(__name__)


@dataclass
class RuntimeContext:
    """
    Context for agent runtime execution.

    Holds all the components needed for deterministic execution.
    """

    # Identity
    session_id: str = ""
    project_path: str = ""

    # Components
    plan: Optional[PlanContract] = None
    capability_token: Optional[CapabilityToken] = None
    stop_policy: Optional[StopPolicy] = None

    # Managers
    observation_collector: Optional[ObservationCollector] = None
    verifier: Optional[DeterministicVerifier] = None
    state_manager: Optional[ProjectStateManager] = None
    ems_store: Optional[EMSStore] = None
    progress_tracker: Optional[ProgressTracker] = None

    # Guards
    capability_guard: Optional[CapabilityGuard] = None
    stop_checker: Optional[StopPolicyChecker] = None

    # Current execution
    current_goal: Optional[Goal] = None
    current_task: Optional[Task] = None
    current_step: Optional[Step] = None

    # Results
    observations: List[ObservationPacket] = field(default_factory=list)
    verifications: List[VerificationReport] = field(default_factory=list)

    def __post_init__(self):
        if not self.session_id:
            import uuid
            self.session_id = str(uuid.uuid4())[:12]


class AgentLoopAdapter:
    """
    Adapts the new agent_runtime to the existing AgentLoop.

    Usage:
        adapter = AgentLoopAdapter(project_path="/path/to/project")

        # Before executing a step
        allowed, reason = adapter.before_step(module_id, params)
        if not allowed:
            handle_blocked(reason)

        # After step execution
        adapter.after_step(step_id, result, success)

        # In CHECK phase
        verification = adapter.verify_step(step_id)
        if not verification.passed:
            handle_failure(verification)
    """

    def __init__(
        self,
        project_path: str = "",
        capability_token: Optional[CapabilityToken] = None,
        stop_policy: Optional[StopPolicy] = None,
    ):
        self.context = RuntimeContext(project_path=project_path)

        # Initialize components
        self.context.observation_collector = get_observation_collector()
        self.context.verifier = DeterministicVerifier()
        self.context.progress_tracker = get_progress_tracker()

        # Set up capability guard
        if capability_token:
            self.context.capability_token = capability_token
            self.context.capability_guard = CapabilityGuard(capability_token)

        # Set up stop policy
        if stop_policy:
            self.context.stop_policy = stop_policy
            self.context.stop_checker = StopPolicyChecker(stop_policy)

        # Initialize project state if path provided
        if project_path:
            self.context.state_manager = ProjectStateManager(project_path)
            self.context.ems_store = EMSStore(
                storage_path=f"{project_path}/.flyto/ems",
                project_id=self.context.session_id,
            )

    def set_plan(self, plan: PlanContract) -> None:
        """Set the current plan for execution."""
        self.context.plan = plan
        logger.info(f"Plan set: {plan.plan_id}")

    def start_goal(self, goal: Goal) -> None:
        """Start tracking a goal."""
        self.context.current_goal = goal
        self.context.progress_tracker.start_goal(
            goal.goal_id,
            goal.name,
            len(goal.tasks),
        )
        logger.info(f"Goal started: {goal.goal_id}")

    def start_task(self, task: Task) -> None:
        """Start tracking a task."""
        self.context.current_task = task
        task.start()
        self.context.progress_tracker.start_task(
            task.task_id,
            task.name,
            len(task.steps),
            task.goal_id,
        )
        logger.info(f"Task started: {task.task_id}")

    def before_step(
        self,
        module_id: str,
        params: Dict[str, Any],
    ) -> tuple[bool, str]:
        """
        Check before executing a step.

        Returns:
            Tuple of (allowed, reason)
        """
        # Check capability
        if self.context.capability_guard:
            allowed, reason = self.context.capability_guard.can_execute(
                module_id, params
            )
            if not allowed:
                logger.warning(f"Step blocked by capability: {reason}")
                return False, reason

        # Check stop policy
        if self.context.stop_checker:
            should_stop, reason, message = self.context.stop_checker.should_stop()
            if should_stop:
                logger.warning(f"Step blocked by stop policy: {message}")
                return False, message

        # Start step tracking
        step = Step(
            module_id=module_id,
            params=params,
            task_id=self.context.current_task.task_id if self.context.current_task else "",
        )
        step.start()
        self.context.current_step = step

        # Record in collector
        self.context.observation_collector.record_step_start(
            step.step_id, module_id
        )

        # Update progress
        self.context.progress_tracker.step_started(
            step.step_id,
            module_id,
            f"Executing {module_id}",
        )

        logger.debug(f"Step started: {step.step_id} ({module_id})")
        return True, "Allowed"

    def after_step(
        self,
        result: Dict[str, Any],
        success: bool,
        error: Optional[str] = None,
    ) -> Step:
        """
        Record step completion.

        Returns:
            The completed Step
        """
        step = self.context.current_step
        if not step:
            logger.warning("after_step called without current step")
            step = Step()

        if success:
            step.complete(result)
        else:
            step.fail(error or "Unknown error")

        # Record in collector
        self.context.observation_collector.record_step_end(
            step.step_id,
            "completed" if success else "failed",
            error,
        )

        # Record usage if guard exists
        if self.context.capability_guard:
            cost = result.get("cost", 0.0) if success else 0.0
            self.context.capability_guard.record_usage(cost)

        # Record iteration if stop checker exists
        if self.context.stop_checker:
            self.context.stop_checker.record_iteration()
            if not success:
                self.context.stop_checker.record_failure(error or "Unknown error")
            else:
                self.context.stop_checker.record_success()

        # Update progress
        self.context.progress_tracker.step_completed(
            step.step_id,
            success,
            step.error if not success else "Step completed",
            step.duration_ms,
        )

        # Add to task if exists
        if self.context.current_task:
            self.context.current_task.add_step(step)

        logger.debug(
            f"Step completed: {step.step_id} "
            f"({'success' if success else 'failed'})"
        )
        return step

    def collect_observation(self, **kwargs) -> ObservationPacket:
        """
        Collect current observation.

        Returns:
            ObservationPacket with current world state
        """
        collector = self.context.observation_collector

        # Build observation
        observation = collector.build_packet(
            browser=kwargs.get("browser"),
            database=kwargs.get("database"),
            filesystem=kwargs.get("filesystem"),
            include_runtime=True,
            include_network=True,
        )

        self.context.observations.append(observation)
        logger.debug(f"Observation collected: {observation.observation_id}")
        return observation

    def verify_step(
        self,
        observation: Optional[ObservationPacket] = None,
    ) -> VerificationReport:
        """
        Verify current step against plan assertions.

        Returns:
            VerificationReport with pass/fail details
        """
        if not self.context.plan:
            logger.warning("No plan set for verification")
            return VerificationReport()

        # Use provided or latest observation
        obs = observation or (
            self.context.observations[-1]
            if self.context.observations
            else self.collect_observation()
        )

        # Get assertions from plan
        assertions = self.context.plan.assertions

        # Run verification
        report = self.context.verifier.verify(obs, assertions)

        # Link to step
        if self.context.current_step:
            self.context.current_step.verification_id = report.verification_id
            self.context.current_step.verification_passed = report.passed

        self.context.verifications.append(report)

        logger.info(
            f"Verification: {report.verification_id} "
            f"{'PASSED' if report.passed else 'FAILED'} "
            f"(confidence: {report.confidence:.2f})"
        )

        # Check EMS for fixes if failed
        if not report.passed and self.context.ems_store:
            self._check_ems_for_fix(report)

        return report

    def _check_ems_for_fix(self, report: VerificationReport) -> None:
        """Check EMS for applicable fix patterns."""
        if not report.failure_analysis:
            return

        sig = compute_error_signature(
            error_type=report.failure_analysis.failure_type,
            error_message=report.failure_analysis.root_cause,
            module_id=self.context.current_step.module_id if self.context.current_step else "",
        )

        result = self.context.ems_store.find_pattern(sig)

        if result.found:
            logger.info(
                f"EMS fix found: {result.pattern.name} "
                f"(similarity: {result.similarity_score:.2f})"
            )
            report.failure_analysis.ems_match = result.pattern.pattern_id
            report.failure_analysis.suggested_fix = result.pattern.description

    def complete_task(self, success: bool = True) -> None:
        """Mark current task as completed."""
        if not self.context.current_task:
            return

        if success:
            self.context.current_task.complete()
        else:
            self.context.current_task.fail()

        self.context.progress_tracker.complete_task(
            self.context.current_task.task_id,
            success,
        )

        logger.info(
            f"Task completed: {self.context.current_task.task_id} "
            f"({'success' if success else 'failed'})"
        )

    def complete_goal(self, success: bool = True) -> None:
        """Mark current goal as completed."""
        if not self.context.current_goal:
            return

        if success:
            self.context.current_goal.complete()
        else:
            self.context.current_goal.fail()

        self.context.progress_tracker.complete_goal(
            self.context.current_goal.goal_id,
            success,
        )

        logger.info(
            f"Goal completed: {self.context.current_goal.goal_id} "
            f"({'success' if success else 'failed'})"
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get execution summary."""
        return {
            "session_id": self.context.session_id,
            "observations": len(self.context.observations),
            "verifications": len(self.context.verifications),
            "passed": sum(1 for v in self.context.verifications if v.passed),
            "failed": sum(1 for v in self.context.verifications if not v.passed),
            "current_goal": (
                self.context.current_goal.goal_id
                if self.context.current_goal else None
            ),
            "current_task": (
                self.context.current_task.task_id
                if self.context.current_task else None
            ),
        }

    def save_state(self) -> bool:
        """Save current state to .flyto/."""
        if not self.context.state_manager:
            return False

        state = self.context.state_manager.get_or_init()

        # Update with current progress
        if self.context.current_goal:
            # Find or add goal
            found = False
            for g in state.active_goals:
                if g.goal_id == self.context.current_goal.goal_id:
                    found = True
                    break
            if not found:
                state.add_goal(self.context.current_goal)

        return self.context.state_manager.save()
