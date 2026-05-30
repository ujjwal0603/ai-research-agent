"""
Agents package — multi-agent framework for the AI Research Agent Platform V2.

Provides the base agent abstraction, agent registry, and specialised agent
implementations (retrieval, summarization, etc.).
"""

from __future__ import annotations

from agents.base import BaseAgent
from agents.registry import AgentRegistry

__all__ = [
    "BaseAgent",
    "AgentRegistry",
]
