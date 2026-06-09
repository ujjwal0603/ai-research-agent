"""
Task planner for decomposing user queries into agent execution plans.

Takes a classified intent and builds an ordered list of agent steps
with dependency tracking for sequential and parallel execution.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

from config.constants import AgentID, IntentType
from orchestrator.intent_classifier import IntentClassifier

logger = logging.getLogger(__name__)


@dataclass
class PlannedStep:
    """A single step in an execution plan"""
    step_index: int
    agent_id: str
    action: str
    input_data: dict = field(default_factory=dict)
    depends_on: list[int] = field(default_factory=list)


@dataclass
class ExecutionPlan:
    """Complete execution plan for a user query"""
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    intent: IntentType = IntentType.QUESTION
    confidence: float = 0.0
    steps: list[PlannedStep] = field(default_factory=list)
    parallel_groups: list[list[int]] = field(default_factory=list)
    context: dict = field(default_factory=dict)


class TaskPlanner:
    """Decomposes user queries into agent execution plans"""

    def __init__(self, intent_classifier: IntentClassifier) -> None:
        self._intent_classifier = intent_classifier

    async def plan(self, query: str, context: dict | None = None) -> ExecutionPlan:
        """
        Classify intent and build an execution plan.

        Args:
            query: User's natural language query
            context: Optional session context (document_ids, preferences, etc.)

        Returns:
            ExecutionPlan with ordered steps
        """
        ctx = context or {}
        intent, confidence = await self._intent_classifier.classify(query)

        plan = ExecutionPlan(intent=intent, confidence=confidence, context=ctx)

        # Build steps based on intent
        builder = self._plan_builders.get(intent, self._plan_question)
        builder(self, plan, query, ctx)

        logger.info(
            f"Plan created: intent={intent.value}, steps={len(plan.steps)}, "
            f"confidence={confidence:.2f}"
        )
        return plan

    # ── Plan builders per intent ────────────────────

    def _plan_question(self, plan: ExecutionPlan, query: str, ctx: dict) -> None:
        """QUESTION: Retrieve → Rerank → Generate answer"""
        document_ids = ctx.get("document_ids")
        search_strategy = ctx.get("search_strategy", "hybrid")
        # Ensure we have a plain string, not an Enum object
        if hasattr(search_strategy, "value"):
            search_strategy = search_strategy.value
        top_k = ctx.get("top_k", 5)

        plan.steps = [
            PlannedStep(
                step_index=0,
                agent_id=AgentID.RETRIEVAL,
                action=f"{search_strategy}_search",
                input_data={
                    "query": query,
                    "top_k": top_k * 2,  # Over-retrieve for reranking
                    "filters": {"document_ids": document_ids} if document_ids else {},
                },
            ),
            PlannedStep(
                step_index=1,
                agent_id=AgentID.RETRIEVAL,
                action="rerank",
                input_data={"query": query, "top_k": top_k},
                depends_on=[0],
            ),
        ]

    def _plan_summarize(self, plan: ExecutionPlan, query: str, ctx: dict) -> None:
        """SUMMARIZE: Retrieve → Summarize (Phase 1: just retrieve + reasoning)"""
        document_ids = ctx.get("document_ids")

        plan.steps = [
            PlannedStep(
                step_index=0,
                agent_id=AgentID.RETRIEVAL,
                action="hybrid_search",
                input_data={
                    "query": query,
                    "top_k": 15,
                    "filters": {"document_ids": document_ids} if document_ids else {},
                },
            ),
        ]

    def _plan_quiz(self, plan: ExecutionPlan, query: str, ctx: dict) -> None:
        """QUIZ: Retrieve → Generate quiz (Phase 1: retrieve + reasoning)"""
        document_ids = ctx.get("document_ids")

        plan.steps = [
            PlannedStep(
                step_index=0,
                agent_id=AgentID.RETRIEVAL,
                action="hybrid_search",
                input_data={
                    "query": query,
                    "top_k": 10,
                    "filters": {"document_ids": document_ids} if document_ids else {},
                },
            ),
        ]

    def _plan_recommend(self, plan: ExecutionPlan, query: str, ctx: dict) -> None:
        """RECOMMEND: Retrieve similar (Phase 1: dense search)"""
        plan.steps = [
            PlannedStep(
                step_index=0,
                agent_id=AgentID.RETRIEVAL,
                action="dense_search",
                input_data={"query": query, "top_k": 10},
            ),
        ]

    def _plan_learn(self, plan: ExecutionPlan, query: str, ctx: dict) -> None:
        """LEARN: Retrieve → Build learning path (Phase 1: retrieve + reasoning)"""
        document_ids = ctx.get("document_ids")

        plan.steps = [
            PlannedStep(
                step_index=0,
                agent_id=AgentID.RETRIEVAL,
                action="hybrid_search",
                input_data={
                    "query": query,
                    "top_k": 20,
                    "filters": {"document_ids": document_ids} if document_ids else {},
                },
            ),
        ]

    _plan_builders = {
        IntentType.QUESTION: _plan_question,
        IntentType.SUMMARIZE: _plan_summarize,
        IntentType.QUIZ: _plan_quiz,
        IntentType.RECOMMEND: _plan_recommend,
        IntentType.LEARN: _plan_learn,
    }
