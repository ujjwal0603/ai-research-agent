"""
Common / shared Pydantic schemas used across multiple modules.

Includes generic pagination, standard error and status envelopes,
and the agent-trace models that record orchestrator execution steps.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ── Generic Paginated Response ──────────────────────


class PaginatedResponse(BaseModel, Generic[T]):
    """Envelope for list endpoints that support pagination.

    Attributes:
        items: The page of results.
        total: Total number of items matching the query.
        page: Current page number (1-indexed).
        page_size: Maximum items per page.
        total_pages: Computed total pages.
    """

    items: List[T]
    total: int = Field(..., ge=0, description="Total matching items")
    page: int = Field(..., ge=1, description="Current page (1-indexed)")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total pages available")


# ── Error Response ──────────────────────────────────


class ErrorResponse(BaseModel):
    """Standard error payload returned for 4xx / 5xx responses.

    Attributes:
        code: Machine-readable error code (e.g. ``DOCUMENT_NOT_FOUND``).
        message: Human-readable description.
        trace_id: Correlation ID for distributed tracing / log lookup.
    """

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error description")
    trace_id: Optional[str] = Field(
        default=None,
        description="Trace / correlation ID for debugging",
    )


# ── Status Response ─────────────────────────────────


class StatusResponse(BaseModel):
    """Simple OK / acknowledged response.

    Attributes:
        status: Short status string (e.g. ``ok``, ``deleted``).
        message: Optional descriptive message.
    """

    status: str = Field(..., description="Status indicator")
    message: str = Field(default="", description="Descriptive message")


# ── Agent Trace ─────────────────────────────────────


class AgentTraceStep(BaseModel):
    """A single step recorded during multi-agent orchestration.

    Attributes:
        agent_id: Identifier of the agent that executed the step.
        action: Short label for what the agent did (e.g. ``retrieve``, ``rerank``).
        latency_ms: Wall-clock time the step took in milliseconds.
        status: Outcome — ``success``, ``failure``, or ``skipped``.
        timestamp: When the step started (UTC).
    """

    agent_id: str = Field(..., description="Agent identifier")
    action: str = Field(..., description="Action label")
    latency_ms: int = Field(..., ge=0, description="Step latency in ms")
    status: str = Field(
        ...,
        description="Step outcome (success / failure / skipped)",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Step start time (UTC)",
    )


class AgentTrace(BaseModel):
    """Ordered list of execution steps across the agent pipeline.

    Attached to responses so the frontend can render a latency waterfall.

    Attributes:
        steps: Ordered list of trace steps.
        total_latency_ms: Aggregated wall-clock latency across all steps.
    """

    steps: List[AgentTraceStep] = Field(
        default_factory=list,
        description="Ordered execution steps",
    )
    total_latency_ms: int = Field(
        default=0,
        ge=0,
        description="Total pipeline latency in ms",
    )
