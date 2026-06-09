"""
Main Orchestrator — the brain of the multi-agent platform.

Coordinates the full pipeline: intent classification → planning →
agent execution → LLM reasoning → response aggregation.
Supports both synchronous and SSE streaming responses.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import AsyncIterator, TYPE_CHECKING

from config.constants import IntentType, SSE_EVENT_START, SSE_EVENT_TOKEN, SSE_EVENT_SOURCES, SSE_EVENT_DONE, SSE_EVENT_ERROR

if TYPE_CHECKING:
    from orchestrator.planner import TaskPlanner
    from orchestrator.workflow import WorkflowEngine
    from models_layer.reasoning.factory import ReasoningModelFactory

logger = logging.getLogger(__name__)


# ── RAG Prompt Template ────────────────────────────

RAG_SYSTEM_PROMPT = """You are an expert AI research assistant. Answer the user's question based ONLY on the provided context from research documents.

Rules:
1. Use only the information in the provided context to answer.
2. If the context doesn't contain enough information, say so clearly.
3. Cite specific sources using [Source N] notation where N is the chunk index.
4. Be precise, comprehensive, and well-structured in your response.
5. Use markdown formatting for clarity."""

RAG_USER_PROMPT_TEMPLATE = """## Context (Retrieved from research documents)

{context}

## User Question

{query}

## Instructions

Answer the question using ONLY the context above. Cite sources with [Source N] notation."""

SUMMARY_SYSTEM_PROMPT = """You are an expert summarization assistant. Generate a comprehensive summary of the provided research content.

Rules:
1. Cover all key findings and arguments.
2. Structure with clear sections when appropriate.
3. Cite source chunks using [Source N] notation.
4. Be thorough yet concise."""


class Orchestrator:
    """
    Main orchestrator — coordinates multi-agent query processing.

    Pipeline: Classify Intent → Plan Steps → Execute Agents → Generate Answer → Aggregate Response
    """

    def __init__(
        self,
        planner: TaskPlanner,
        workflow_engine: WorkflowEngine,
        reasoning_factory: ReasoningModelFactory,
    ) -> None:
        self._planner = planner
        self._workflow = workflow_engine
        self._reasoning = reasoning_factory

    async def process_query(
        self, query: str, context: dict | None = None
    ) -> dict:
        """
        Process a user query through the full multi-agent pipeline.

        Returns a complete response dict compatible with ChatResponse schema.
        """
        ctx = context or {}
        trace_id = str(uuid.uuid4())
        start = time.perf_counter()

        logger.info(f"[{trace_id}] Processing query: {query[:100]}...")

        # 1. Plan
        plan = await self._planner.plan(query, ctx)

        # 2. Execute agent steps
        workflow_result = await self._workflow.execute_plan(plan, ctx)
        agent_results = workflow_result["results"]

        # 3. Build context from retrieved chunks
        chunks_text = []
        sources = []
        for result in agent_results:
            if result.status == "success" and "chunks" in result.output_data:
                for chunk in result.output_data["chunks"]:
                    chunks_text.append(chunk.get("text", ""))
                    sources.append(chunk)

        # 4. Generate final answer via LLM
        answer = ""
        if chunks_text:
            rag_context = self._build_rag_context(chunks_text)
            system_prompt = self._get_system_prompt(plan.intent)
            user_prompt = RAG_USER_PROMPT_TEMPLATE.format(
                context=rag_context, query=query
            )
            provider = ctx.get("provider", "auto")
            answer = await self._reasoning.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                provider=provider,
            )
        else:
            answer = "I couldn't find relevant information in the uploaded documents to answer your question. Please try rephrasing or ensure the relevant documents are uploaded."

        total_ms = int((time.perf_counter() - start) * 1000)
        logger.info(f"[{trace_id}] Query processed in {total_ms}ms")

        return {
            "answer": answer,
            "sources": sources,
            "citations": [],
            "agent_trace": {
                "trace_id": trace_id,
                "steps": [
                    {
                        "agent_id": r.agent_id,
                        "action": r.output_data.get("action", "unknown"),
                        "latency_ms": r.latency_ms,
                        "status": r.status,
                    }
                    for r in agent_results
                ],
                "total_latency_ms": total_ms,
                "intent": plan.intent.value,
            },
            "session_id": ctx.get("session_id", ""),
            "confidence": plan.confidence,
        }

    async def process_query_stream(
        self, query: str, context: dict | None = None
    ) -> AsyncIterator[dict]:
        """
        Process a query and yield SSE events as the response is generated.

        Yields dicts with 'event' and 'data' keys for SSE formatting.
        """
        ctx = context or {}
        trace_id = str(uuid.uuid4())
        session_id = ctx.get("session_id", str(uuid.uuid4()))

        # Emit start event
        yield {
            "event": SSE_EVENT_START,
            "data": json.dumps({"session_id": session_id, "trace_id": trace_id}),
        }

        try:
            # 1. Plan
            plan = await self._planner.plan(query, ctx)

            # 2. Execute agent steps (retrieval)
            workflow_result = await self._workflow.execute_plan(plan, ctx)
            agent_results = workflow_result["results"]

            # 3. Collect chunks
            chunks_text = []
            sources = []
            for result in agent_results:
                if result.status == "success" and "chunks" in result.output_data:
                    for raw_chunk in result.output_data["chunks"]:
                        # Lift payload fields to the top level for consistency
                        payload = raw_chunk.get("payload", {})
                        chunk = {**payload, **raw_chunk}
                        
                        text = chunk.get("text", "")
                        if text:
                            chunks_text.append(text)
                            sources.append(chunk)

            # 4. Stream LLM response
            full_answer = ""
            if chunks_text:
                rag_context = self._build_rag_context(chunks_text)
                system_prompt = self._get_system_prompt(plan.intent)
                user_prompt = RAG_USER_PROMPT_TEMPLATE.format(
                    context=rag_context, query=query
                )
                provider = ctx.get("provider", "auto")

                async for token in self._reasoning.generate_stream(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    provider=provider,
                ):
                    full_answer += token
                    yield {"event": SSE_EVENT_TOKEN, "data": json.dumps({"token": token})}
            else:
                full_answer = "I couldn't find relevant information to answer your question."
                yield {
                    "event": SSE_EVENT_TOKEN,
                    "data": json.dumps({"token": full_answer}),
                }

            # Emit sources
            yield {
                "event": SSE_EVENT_SOURCES,
                "data": json.dumps({"sources": sources[:10]}),  # Limit to top 10
            }

            # Emit done
            yield {
                "event": SSE_EVENT_DONE,
                "data": json.dumps({
                    "answer": full_answer,
                    "trace_id": trace_id,
                    "intent": plan.intent.value,
                    "steps": len(agent_results),
                }),
            }

        except Exception as exc:
            logger.exception(f"[{trace_id}] Streaming error: {exc}")
            yield {
                "event": SSE_EVENT_ERROR,
                "data": json.dumps({"error": str(exc)}),
            }

    # ── Helpers ─────────────────────────────────────

    def _build_rag_context(self, chunks: list[str]) -> str:
        """Format retrieved chunks into a numbered context block"""
        sections = []
        for i, text in enumerate(chunks):
            sections.append(f"[Source {i + 1}]\n{text}")
        return "\n\n---\n\n".join(sections)

    def _get_system_prompt(self, intent: IntentType) -> str:
        """Select system prompt based on intent type"""
        if intent == IntentType.SUMMARIZE:
            return SUMMARY_SYSTEM_PROMPT
        return RAG_SYSTEM_PROMPT
