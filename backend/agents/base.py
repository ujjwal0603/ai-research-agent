"""
Abstract base class for all agents in the multi-agent framework.

Every specialised agent (retrieval, summarization, quiz, etc.) inherits from
``BaseAgent`` and implements ``execute`` and ``validate_input``.  The base class
provides common helpers for health-checks, capability reporting, and
result construction.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from schemas.agents import AgentInfo, AgentResult, AgentTask

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for every agent in the platform.

    Sub-classes MUST implement:
    - ``execute`` — run the task and return a result.
    - ``validate_input`` — verify the incoming task is well-formed.

    Attributes
    ----------
    agent_id : str
        Globally unique identifier for this agent instance.
    agent_name : str
        Human-readable label.
    capabilities : list[str]
        Actions / skills this agent can perform.
    required_models : list[str]
        Model types that must be available for this agent to function.
    """

    # ── Abstract Properties (override in sub-classes) ────────────────────

    @property
    @abstractmethod
    def agent_id(self) -> str:
        """Globally unique identifier for this agent."""
        ...

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Human-readable name."""
        ...

    @property
    @abstractmethod
    def capabilities(self) -> list[str]:
        """List of action keys this agent can handle."""
        ...

    @property
    @abstractmethod
    def required_models(self) -> list[str]:
        """Model types that must be present for this agent to work."""
        ...

    # ── Abstract Methods ────────────────────────────────────────────────

    @abstractmethod
    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute a task and return the result.

        Parameters
        ----------
        task:
            The dispatchable unit of work.

        Returns
        -------
        AgentResult
            Output containing success flag, data, and optional error info.
        """
        ...

    @abstractmethod
    async def validate_input(self, task: AgentTask) -> bool:
        """Validate that the task payload is well-formed.

        Returns
        -------
        bool
            ``True`` if the task can be executed, ``False`` otherwise.
        """
        ...

    # ── Concrete Methods ────────────────────────────────────────────────

    async def health_check(self) -> dict[str, Any]:
        """Run a lightweight self-diagnostic.

        Returns
        -------
        dict
            ``{"agent_id": ..., "name": ..., "status": "healthy" | "unhealthy"}``.
        """
        try:
            # Sub-classes can override to add richer checks.
            return {
                "agent_id": self.agent_id,
                "name": self.agent_name,
                "status": "healthy",
                "capabilities": self.capabilities,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            logger.error("Health check failed for %s: %s", self.agent_id, exc)
            return {
                "agent_id": self.agent_id,
                "name": self.agent_name,
                "status": "unhealthy",
                "error": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def get_capabilities(self) -> list[str]:
        """Return the list of capabilities this agent supports."""
        return list(self.capabilities)

    def get_info(self) -> AgentInfo:
        """Return serialisable metadata about this agent."""
        return AgentInfo(
            agent_id=self.agent_id,
            name=self.agent_name,
            description=f"Agent with capabilities: {', '.join(self.capabilities)}",
            supported_intents=self.capabilities,
            status="active",
        )

    # ── Helper: build a result ──────────────────────────────────────────

    @staticmethod
    def _create_result(
        task: AgentTask,
        *,
        status: str,
        output_data: dict[str, Any],
        error: str | None = None,
        latency_ms: int = 0,
    ) -> AgentResult:
        """Construct an ``AgentResult`` from common parameters.

        Parameters
        ----------
        task:
            The original task (used for ``task_id`` and ``agent_id``).
        status:
            ``"success"`` or ``"failure"``.
        output_data:
            Payload to include in the result ``data`` field.
        error:
            Optional error message.
        latency_ms:
            Wall-clock execution time in milliseconds.
        """
        return AgentResult(
            task_id=task.task_id,
            agent_id=task.agent_id,
            success=(status == "success"),
            data=output_data,
            error=error,
            latency_ms=latency_ms,
        )
