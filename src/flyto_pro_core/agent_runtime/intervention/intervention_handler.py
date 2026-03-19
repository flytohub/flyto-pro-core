"""
Intervention Handler - Manages user interventions.

Handles the flow of intervention requests and responses.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Awaitable

from .intervention_types import (
    InterventionPoint,
    InterventionPriority,
    InterventionRequest,
    InterventionResponse,
    InterventionType,
)
from ..contracts.decision_card import DecisionCard

logger = logging.getLogger(__name__)


# Callback type for handling interventions
InterventionCallback = Callable[
    [InterventionRequest],
    Awaitable[InterventionResponse]
]


@dataclass
class InterventionConfig:
    """Configuration for intervention handling."""

    # Auto-approve settings
    auto_approve_low_priority: bool = False
    auto_approve_timeout_ms: int = 30000  # Default timeout
    batch_low_priority: bool = True

    # Queue settings
    max_pending_requests: int = 10
    request_ttl_ms: int = 300000  # 5 minutes

    # Callback settings
    callback_timeout_ms: int = 60000


class InterventionHandler:
    """
    Handles intervention requests during workflow execution.

    Responsibilities:
    - Queue intervention requests
    - Wait for user responses
    - Handle timeouts and auto-approvals
    - Track intervention history
    """

    def __init__(self, config: Optional[InterventionConfig] = None):
        self.config = config or InterventionConfig()
        self._callback: Optional[InterventionCallback] = None
        self._pending_requests: Dict[str, InterventionRequest] = {}
        self._completed_responses: Dict[str, InterventionResponse] = {}
        self._history: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()

    def set_callback(self, callback: InterventionCallback) -> None:
        """Set the callback for handling interventions."""
        self._callback = callback

    async def request_intervention(
        self,
        point: InterventionPoint,
        options: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> InterventionResponse:
        """
        Request user intervention.

        Args:
            point: The intervention point
            options: Available options for user
            context: Additional context

        Returns:
            User's response
        """
        from .intervention_types import InterventionOption

        # Build request
        intervention_options = []
        if options:
            for opt in options:
                intervention_options.append(
                    InterventionOption(
                        option_id=opt.get("id", ""),
                        label=opt.get("label", ""),
                        description=opt.get("description", ""),
                        is_recommended=opt.get("recommended", False),
                        is_dangerous=opt.get("dangerous", False),
                        consequences=opt.get("consequences", []),
                    )
                )

        request = InterventionRequest(
            intervention_point=point,
            options=intervention_options,
            current_state_summary=context or {},
        )

        return await self._handle_request(request)

    async def _handle_request(
        self,
        request: InterventionRequest,
    ) -> InterventionResponse:
        """Handle a single intervention request."""
        start_time = time.time()

        async with self._lock:
            # Check queue limit
            if len(self._pending_requests) >= self.config.max_pending_requests:
                # Remove oldest expired requests
                self._cleanup_expired()

            self._pending_requests[request.request_id] = request

        logger.info(
            f"Intervention requested: {request.request_id} "
            f"({request.intervention_point.point_type.value})"
        )

        try:
            # Check for auto-approve conditions
            if self._should_auto_approve(request):
                response = self._create_auto_response(request, "auto_approve")
            elif self._callback:
                # Call the callback to get user response
                response = await asyncio.wait_for(
                    self._callback(request),
                    timeout=self.config.callback_timeout_ms / 1000,
                )
            else:
                # No callback - use default option
                response = self._create_auto_response(request, "no_callback")

        except asyncio.TimeoutError:
            logger.warning(f"Intervention timeout: {request.request_id}")
            response = self._create_auto_response(request, "timeout")

        except Exception as e:
            logger.error(f"Intervention error: {e}")
            response = self._create_auto_response(request, f"error: {str(e)}")

        # Calculate response time
        response.response_time_ms = int((time.time() - start_time) * 1000)

        # Record history
        self._record_history(request, response)

        async with self._lock:
            if request.request_id in self._pending_requests:
                del self._pending_requests[request.request_id]
            self._completed_responses[request.request_id] = response

        logger.info(
            f"Intervention completed: {request.request_id} "
            f"-> {response.selected_option_id or response.text_input}"
        )

        return response

    def _should_auto_approve(self, request: InterventionRequest) -> bool:
        """Check if request should be auto-approved."""
        # Auto-approve low priority if configured
        if (
            self.config.auto_approve_low_priority
            and request.intervention_point.priority == InterventionPriority.LOW
        ):
            return True

        # Check if expired (past timeout)
        if request.is_expired():
            return True

        return False

    def _create_auto_response(
        self,
        request: InterventionRequest,
        reason: str,
    ) -> InterventionResponse:
        """Create an automatic response."""
        default_option = request.get_default_option()

        return InterventionResponse(
            request_id=request.request_id,
            selected_option_id=default_option.option_id if default_option else None,
            is_auto_response=True,
            auto_response_reason=reason,
        )

    def _record_history(
        self,
        request: InterventionRequest,
        response: InterventionResponse,
    ) -> None:
        """Record intervention in history."""
        self._history.append({
            "request_id": request.request_id,
            "point_type": request.intervention_point.point_type.value,
            "priority": request.intervention_point.priority.value,
            "title": request.intervention_point.title,
            "selected_option": response.selected_option_id,
            "text_input": response.text_input,
            "is_auto": response.is_auto_response,
            "auto_reason": response.auto_response_reason,
            "response_time_ms": response.response_time_ms,
            "timestamp": response.response_at,
        })

    def _cleanup_expired(self) -> None:
        """Remove expired requests from pending queue."""
        now = datetime.utcnow()
        expired = []

        for req_id, req in self._pending_requests.items():
            created = datetime.fromisoformat(req.created_at)
            age_ms = (now - created).total_seconds() * 1000
            if age_ms > self.config.request_ttl_ms:
                expired.append(req_id)

        for req_id in expired:
            del self._pending_requests[req_id]

    async def batch_interventions(
        self,
        requests: List[InterventionRequest],
    ) -> List[InterventionResponse]:
        """
        Handle multiple interventions in batch.

        Low-priority interventions can be batched for efficiency.
        """
        if not requests:
            return []

        # Separate by priority
        critical = [
            r for r in requests
            if r.intervention_point.priority == InterventionPriority.CRITICAL
        ]
        others = [
            r for r in requests
            if r.intervention_point.priority != InterventionPriority.CRITICAL
        ]

        responses = []

        # Handle critical first, one by one
        for req in critical:
            resp = await self._handle_request(req)
            responses.append(resp)

        # Handle others (could batch in UI)
        for req in others:
            resp = await self._handle_request(req)
            responses.append(resp)

        return responses

    def get_pending_count(self) -> int:
        """Get number of pending interventions."""
        return len(self._pending_requests)

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get intervention history."""
        return self._history[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get intervention statistics."""
        if not self._history:
            return {
                "total": 0,
                "auto_approved": 0,
                "user_responded": 0,
                "avg_response_time_ms": 0,
            }

        total = len(self._history)
        auto_approved = sum(1 for h in self._history if h.get("is_auto"))
        user_responded = total - auto_approved
        avg_time = sum(h.get("response_time_ms", 0) for h in self._history) / total

        by_type = {}
        for h in self._history:
            pt = h.get("point_type", "unknown")
            by_type[pt] = by_type.get(pt, 0) + 1

        return {
            "total": total,
            "auto_approved": auto_approved,
            "user_responded": user_responded,
            "avg_response_time_ms": int(avg_time),
            "by_type": by_type,
        }


class ConsoleInterventionHandler:
    """
    Console-based intervention handler for CLI usage.

    Useful for testing and CLI tools.
    """

    def __init__(self):
        self.handler = InterventionHandler()
        self.handler.set_callback(self._console_callback)

    async def _console_callback(
        self,
        request: InterventionRequest,
    ) -> InterventionResponse:
        """Handle intervention via console."""
        print("\n" + "=" * 50)
        print(f"INTERVENTION: {request.intervention_point.title}")
        print("=" * 50)
        print(f"Description: {request.intervention_point.description}")
        print()

        if request.options:
            print("Options:")
            for i, opt in enumerate(request.options):
                prefix = "[RECOMMENDED] " if opt.is_recommended else ""
                danger = " [DANGEROUS]" if opt.is_dangerous else ""
                print(f"  {i + 1}. {prefix}{opt.label}{danger}")
                if opt.description:
                    print(f"     {opt.description}")

        if request.allow_text_input:
            print(f"\n{request.text_input_prompt}")

        print()

        # In a real implementation, this would wait for user input
        # For now, just return the recommended option
        default = request.get_default_option()
        return InterventionResponse(
            request_id=request.request_id,
            selected_option_id=default.option_id if default else None,
            is_auto_response=True,
            auto_response_reason="console_default",
        )

    async def request(
        self,
        point: InterventionPoint,
        options: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> InterventionResponse:
        """Request intervention."""
        return await self.handler.request_intervention(point, options, context)


# Singleton instance
_handler_instance: Optional[InterventionHandler] = None


def get_intervention_handler() -> InterventionHandler:
    """Get the singleton intervention handler."""
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = InterventionHandler()
    return _handler_instance
