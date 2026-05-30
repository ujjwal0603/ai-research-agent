"""
Multi-agent orchestration Pydantic schemas.

Covers inter-agent message passing, task assignment,
result reporting, and agent introspection / health.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from config.constants import Priority

logger = logging.getLogger(__name__)


# ── Agent Status ───────────────────────────────────


class AgentStatus(str, Enum):
    """Runtime status of a registered agent."""

    READY = "ready"
    BUSY = "busy"
    ERROR = "error"


class TaskStatus(str, Enum):
    """Outcome status for a completed agent task."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


# ── Agent Message ──────────────────────────────────


class AgentMessage(BaseModel):
    """Envelope for communication between agents in the pipeline.

    Attributes:
        message_id: Unique message identifier.
        source_agent: ID of the sending agent.
        target_agent: ID of the receiving agent.
        intent: High-level intent label for routing.
        payload: Arbitrary data payload.
        priority: Message priority.
        timestamp: When the message was created (UTC).
        trace_id: Distributed tracing correlation ID.
        parent_message_id: ID of the message this is replying to.
    """

    message_id: str = Field(..., description="Unique message ID")
    source_agent: str = Field(..., description="Sending agent ID")
    target_agent: str = Field(..., description="Receiving agent ID")
    intent: str = Field(..., description="Intent label for routing")
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary data payload",
    )
    priority: Priority = Field(
        default=Priority.NORMAL,
        description="Message priority",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp (UTC)",
    )
    trace_id: str = Field(..., description="Distributed trace / correlation ID")
    parent_message_id: Optional[str] = Field(
        default=None,
        description="Parent message ID (for replies)",
    )


# ── Agent Task ─────────────────────────────────────


class AgentTask(BaseModel):
    """A discrete unit of work dispatched to an agent.

    Attributes:
        task_id: Unique task identifier.
        agent_id: Agent assigned to execute this task.
        action: Action label (e.g. ``retrieve``, ``summarize``).
        input_data: Input data for the task.
        context: Additional context / metadata.
        priority: Task priority.
    """

    task_id: str = Field(..., description="Unique task ID")
    agent_id: str = Field(..., description="Assigned agent ID")
    action: str = Field(..., description="Action label")
    input_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Task input data",
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context / metadata",
    )
    priority: Priority = Field(
        default=Priority.NORMAL,
        description="Task priority",
    )


# ── Agent Result ───────────────────────────────────


class AgentResult(BaseModel):
    """Result reported by an agent after task execution.

    Attributes:
        task_id: The task that was executed.
        agent_id: Agent that produced this result.
        status: Outcome status.
        output_data: Result data.
        error: Error message on failure.
        latency_ms: Execution time in milliseconds.
    """

    task_id: str = Field(..., description="Executed task ID")
    agent_id: str = Field(..., description="Producing agent ID")
    status: TaskStatus = Field(..., description="Outcome status")
    output_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Result data",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message (on failure)",
    )
    latency_ms: int = Field(
        ...,
        ge=0,
        description="Execution time in milliseconds",
    )


# ── Agent Info ─────────────────────────────────────


class AgentInfo(BaseModel):
    """Introspection / health information for a registered agent.

    Attributes:
        agent_id: Agent identifier.
        agent_name: Human-readable agent name.
        capabilities: List of capability tags.
        status: Current runtime status.
        health: Arbitrary health / metrics dict.
    """

    agent_id: str = Field(..., description="Agent identifier")
    agent_name: str = Field(..., description="Human-readable name")
    capabilities: List[str] = Field(
        default_factory=list,
        description="Capability tags",
    )
    status: AgentStatus = Field(
        default=AgentStatus.READY,
        description="Current runtime status",
    )
    health: Dict[str, Any] = Field(
        default_factory=dict,
        description="Health / metrics data",
    )
