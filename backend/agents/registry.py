"""
Agent registry — singleton catalogue of all registered agents.

Allows the orchestrator to discover agents by ID or capability at runtime.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from agents.base import BaseAgent
from schemas.agents import AgentInfo

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Singleton registry that maps agent IDs to live ``BaseAgent`` instances.

    The orchestrator, dispatcher, and health-check endpoints all query this
    registry to locate the appropriate agent for a given task.

    Usage
    -----
    >>> registry = AgentRegistry()
    >>> registry.register(my_agent)
    >>> agent = registry.get_agent("retrieval_agent")
    """

    _instance: AgentRegistry | None = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __new__(cls) -> AgentRegistry:
        """Ensure only one ``AgentRegistry`` exists."""
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._agents: dict[str, BaseAgent] = {}
            cls._instance = instance
            logger.info("AgentRegistry singleton created.")
        return cls._instance

    # ── Registration ────────────────────────────────────────────────────

    def register(self, agent: BaseAgent) -> None:
        """Register an agent instance.

        Parameters
        ----------
        agent:
            The agent to register.  Its ``agent_id`` is used as the key.

        Raises
        ------
        ValueError
            If an agent with the same ID is already registered.
        """
        if agent.agent_id in self._agents:
            logger.warning(
                "Agent '%s' is already registered — replacing.", agent.agent_id
            )
        self._agents[agent.agent_id] = agent
        logger.info(
            "Registered agent '%s' (%s) with capabilities %s.",
            agent.agent_id,
            agent.agent_name,
            agent.capabilities,
        )

    def deregister(self, agent_id: str) -> None:
        """Remove an agent from the registry.

        Parameters
        ----------
        agent_id:
            Identifier of the agent to remove.

        Raises
        ------
        KeyError
            If no agent with the given ID is registered.
        """
        if agent_id not in self._agents:
            raise KeyError(f"Agent '{agent_id}' is not registered.")
        del self._agents[agent_id]
        logger.info("Deregistered agent '%s'.", agent_id)

    # ── Lookup ──────────────────────────────────────────────────────────

    def get_agent(self, agent_id: str) -> BaseAgent:
        """Retrieve an agent by its ID.

        Raises
        ------
        KeyError
            If no agent with the given ID is registered.
        """
        try:
            return self._agents[agent_id]
        except KeyError:
            available = list(self._agents.keys())
            raise KeyError(
                f"Agent '{agent_id}' not found. "
                f"Available agents: {available}"
            ) from None

    def get_agents_for_capability(self, capability: str) -> list[BaseAgent]:
        """Return all agents that advertise *capability*.

        Parameters
        ----------
        capability:
            Capability key to search for (e.g. ``"hybrid_search"``).

        Returns
        -------
        list[BaseAgent]
            May be empty if no agent supports the capability.
        """
        matching = [
            agent
            for agent in self._agents.values()
            if capability in agent.capabilities
        ]
        logger.debug(
            "Found %d agent(s) for capability '%s'.",
            len(matching),
            capability,
        )
        return matching

    # ── Listing ─────────────────────────────────────────────────────────

    def list_agents(self) -> list[AgentInfo]:
        """Return metadata for every registered agent."""
        return [agent.get_info() for agent in self._agents.values()]

    # ── Health ──────────────────────────────────────────────────────────

    async def health_check_all(self) -> dict[str, Any]:
        """Run ``health_check`` on every registered agent concurrently.

        Returns
        -------
        dict
            ``{"agents": {agent_id: health_dict, ...}, "total": N, "healthy": M}``
        """
        if not self._agents:
            return {"agents": {}, "total": 0, "healthy": 0}

        tasks = {
            agent_id: asyncio.create_task(agent.health_check())
            for agent_id, agent in self._agents.items()
        }

        results: dict[str, dict[str, Any]] = {}
        healthy_count = 0

        for agent_id, task in tasks.items():
            try:
                result = await task
                results[agent_id] = result
                if result.get("status") == "healthy":
                    healthy_count += 1
            except Exception as exc:
                logger.error("Health check failed for '%s': %s", agent_id, exc)
                results[agent_id] = {
                    "agent_id": agent_id,
                    "status": "unhealthy",
                    "error": str(exc),
                }

        logger.info(
            "Health check complete: %d/%d agents healthy.",
            healthy_count,
            len(self._agents),
        )
        return {
            "agents": results,
            "total": len(self._agents),
            "healthy": healthy_count,
        }

    # ── Dunder ──────────────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self._agents)

    def __contains__(self, agent_id: str) -> bool:
        return agent_id in self._agents

    def __repr__(self) -> str:
        return f"<AgentRegistry agents={list(self._agents.keys())}>"
