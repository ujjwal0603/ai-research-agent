"""
Response aggregator for merging agent results into user-facing responses.

Combines outputs from multiple agents into unified response objects
and builds agent trace information for debugging.
"""

from __future__ import annotations

import logging
import uuid

from schemas.agents import AgentResult
from schemas.common import AgentTrace, AgentTraceStep

logger = logging.getLogger(__name__)


class ResponseAggregator:
    """Merges agent results into unified responses"""

    async def aggregate_chat(
        self, results: list[AgentResult], query: str, answer: str = ""
    ) -> dict:
        """
        Aggregate results for a chat response.

        Combines retrieval results with the LLM-generated answer.
        """
        trace = self._build_trace(results)
        sources = []
        chunks_text = []

        for result in results:
            if result.status == "success" and "chunks" in result.output_data:
                for chunk in result.output_data["chunks"]:
                    sources.append(chunk)
                    chunks_text.append(chunk.get("text", ""))

        return {
            "answer": answer,
            "sources": sources,
            "citations": [],  # Citation agent not yet implemented in Phase 1
            "agent_trace": trace,
            "session_id": "",
            "confidence": self._compute_confidence(results),
            "chunks_text": chunks_text,
        }

    async def aggregate_summary(self, results: list[AgentResult]) -> dict:
        """Aggregate results for a summary response"""
        trace = self._build_trace(results)
        summary_text = ""
        sources = []

        for result in results:
            if result.status == "success":
                if "summary" in result.output_data:
                    summary_text = result.output_data["summary"]
                if "chunks" in result.output_data:
                    sources = result.output_data["chunks"]

        return {
            "summary_id": str(uuid.uuid4()),
            "summary": summary_text,
            "sections": None,
            "citations": [],
            "word_count": len(summary_text.split()),
            "document_coverage": 0.0,
            "agent_trace": trace,
        }

    async def aggregate_quiz(self, results: list[AgentResult]) -> dict:
        """Aggregate results for a quiz response"""
        trace = self._build_trace(results)
        questions = []

        for result in results:
            if result.status == "success" and "questions" in result.output_data:
                questions = result.output_data["questions"]

        return {
            "quiz_id": str(uuid.uuid4()),
            "questions": questions,
            "agent_trace": trace,
        }

    def _build_trace(self, results: list[AgentResult]) -> dict:
        """Build an AgentTrace from a list of AgentResults"""
        steps = []
        total_latency = 0

        for result in results:
            steps.append(
                AgentTraceStep(
                    agent_id=result.agent_id,
                    action=result.output_data.get("action", "unknown"),
                    latency_ms=result.latency_ms,
                    status=result.status,
                    detail=result.error,
                ).model_dump()
            )
            total_latency += result.latency_ms

        trace = AgentTrace(
            trace_id=str(uuid.uuid4()),
            steps=steps,
            total_latency_ms=total_latency,
        )
        return trace.model_dump()

    def _compute_confidence(self, results: list[AgentResult]) -> float:
        """Compute overall confidence from agent results"""
        successes = sum(1 for r in results if r.status == "success")
        if not results:
            return 0.0
        return round(successes / len(results), 2)
