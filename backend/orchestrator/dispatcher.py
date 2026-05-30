"""
Agent dispatcher for executing planned steps via the agent registry.

Handles both sequential and parallel dispatch patterns, with
error handling and latency tracking.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import TYPE_CHECKING

from config.constants import Priority
from schemas.agents import AgentTask, AgentResult

if TYPE_CHECKING:
    from agents.registry import AgentRegistry
    from orchestrator.planner import PlannedStep

logger = logging.getLogger(__name__)


class AgentDispatcher:
    """Dispatches tasks to agents via the registry"""

    def __init__(self, registry: AgentRegistry) -> None:
        self._registry = registry

    async def dispatch(
        self, step: PlannedStep, context: dict, trace_id: str | None = None
    ) -> AgentResult:
        """
        Dispatch a single planned step to the appropriate agent.

        Args:
            step: The planned step to execute
            context: Execution context (may include prior step results)
            trace_id: Request-level trace ID for logging

        Returns:
            AgentResult from the agent execution
        """
        trace_id = trace_id or str(uuid.uuid4())

        try:
            agent = self._registry.get_agent(step.agent_id)
        except KeyError:
            logger.error(f"Agent not found: {step.agent_id}")
            return AgentResult(
                task_id=str(uuid.uuid4()),
                agent_id=step.agent_id,
                status="failure",
                output_data={},
                error=f"Agent '{step.agent_id}' not registered",
                latency_ms=0,
            )

        # Merge step input with context from previous steps
        input_data = {**step.input_data}
        if "previous_results" in context:
            input_data["previous_results"] = context["previous_results"]

        task = AgentTask(
            task_id=str(uuid.uuid4()),
            agent_id=step.agent_id,
            action=step.action,
            input_data=input_data,
            context=context,
            priority=Priority.NORMAL,
        )

        logger.info(
            f"[{trace_id}] Dispatching: agent={step.agent_id}, "
            f"action={step.action}"
        )

        start = time.perf_counter()
        try:
            result = await agent.execute(task)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logger.info(
                f"[{trace_id}] Completed: agent={step.agent_id}, "
                f"status={result.status}, latency={elapsed_ms}ms"
            )
            return result

        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logger.exception(
                f"[{trace_id}] Agent failed: {step.agent_id} — {exc}"
            )
            return AgentResult(
                task_id=task.task_id,
                agent_id=step.agent_id,
                status="failure",
                output_data={},
                error=str(exc),
                latency_ms=elapsed_ms,
            )

    async def dispatch_parallel(
        self,
        steps: list[PlannedStep],
        context: dict,
        trace_id: str | None = None,
    ) -> list[AgentResult]:
        """
        Dispatch multiple steps in parallel using asyncio.gather.

        Args:
            steps: List of steps to execute concurrently
            context: Shared execution context
            trace_id: Request-level trace ID

        Returns:
            List of AgentResults in the same order as input steps
        """
        trace_id = trace_id or str(uuid.uuid4())
        logger.info(
            f"[{trace_id}] Parallel dispatch: {len(steps)} steps"
        )

        tasks = [
            self.dispatch(step, context, trace_id) for step in steps
        ]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return list(results)
