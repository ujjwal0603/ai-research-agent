"""
Workflow engine for executing agent plans with dependency resolution.

Handles sequential chains, parallel fan-outs, and step dependencies,
ensuring each step receives outputs from its prerequisites.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from schemas.agents import AgentResult

if TYPE_CHECKING:
    from orchestrator.dispatcher import AgentDispatcher
    from orchestrator.aggregator import ResponseAggregator
    from orchestrator.planner import ExecutionPlan

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Executes agent plans respecting step dependencies"""

    def __init__(
        self,
        dispatcher: AgentDispatcher,
        aggregator: ResponseAggregator,
    ) -> None:
        self._dispatcher = dispatcher
        self._aggregator = aggregator

    async def execute_plan(
        self, plan: ExecutionPlan, context: dict | None = None
    ) -> dict:
        """
        Execute an entire plan, respecting step dependencies.

        Steps without dependencies run in parallel groups.
        Steps with dependencies wait for their prerequisites.

        Args:
            plan: The execution plan to run
            context: Additional context to pass to agents

        Returns:
            Dict with all agent results and the aggregated response
        """
        ctx = context or {}
        ctx["plan_id"] = plan.plan_id
        ctx["intent"] = plan.intent.value

        results: dict[int, AgentResult] = {}
        all_results: list[AgentResult] = []
        start = time.perf_counter()

        # Group steps by dependency level
        execution_order = self._topological_sort(plan.steps)

        for level_indices in execution_order:
            level_steps = [plan.steps[i] for i in level_indices]

            # Inject previous results into context
            level_ctx = {**ctx}
            for step in level_steps:
                if step.depends_on:
                    prev_outputs = []
                    for dep_idx in step.depends_on:
                        if dep_idx in results:
                            prev_outputs.append(results[dep_idx].output_data)
                    level_ctx["previous_results"] = prev_outputs

            if len(level_steps) == 1:
                # Sequential execution
                result = await self._dispatcher.dispatch(
                    level_steps[0], level_ctx, plan.plan_id
                )
                results[level_steps[0].step_index] = result
                all_results.append(result)
            else:
                # Parallel execution
                parallel_results = await self._dispatcher.dispatch_parallel(
                    level_steps, level_ctx, plan.plan_id
                )
                for step, result in zip(level_steps, parallel_results):
                    results[step.step_index] = result
                    all_results.append(result)

        total_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            f"Plan {plan.plan_id} completed: {len(all_results)} steps, "
            f"{total_ms}ms total"
        )

        return {
            "results": all_results,
            "total_latency_ms": total_ms,
            "plan_id": plan.plan_id,
            "intent": plan.intent.value,
        }

    def _topological_sort(self, steps: list) -> list[list[int]]:
        """
        Sort steps into execution levels based on dependencies.

        Returns a list of lists, where each inner list contains
        step indices that can be executed in parallel.
        """
        if not steps:
            return []

        levels: list[list[int]] = []
        completed: set[int] = set()
        remaining = {s.step_index for s in steps}

        while remaining:
            # Find steps whose dependencies are all completed
            ready = []
            for step in steps:
                if step.step_index in remaining:
                    deps = set(step.depends_on)
                    if deps.issubset(completed):
                        ready.append(step.step_index)

            if not ready:
                # Circular dependency or missing steps — force execute remaining
                logger.warning("Unresolvable dependencies, forcing execution")
                ready = list(remaining)

            levels.append(ready)
            completed.update(ready)
            remaining -= set(ready)

        return levels
