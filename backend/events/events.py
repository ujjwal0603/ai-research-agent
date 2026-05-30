"""
Event type definitions for the platform event bus.

Provides typed event dataclasses for document, agent, and chat events
that flow through the in-process pub/sub system.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from config.constants import EventType


@dataclass
class BaseEvent:
    """Base event class for all platform events"""
    event_type: EventType
    payload: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class DocumentEvent(BaseEvent):
    """Events related to document operations"""
    document_id: str = ""
    user_id: str = ""


@dataclass
class AgentEvent(BaseEvent):
    """Events related to agent execution"""
    agent_id: str = ""
    task_id: str = ""


@dataclass
class ChatEvent(BaseEvent):
    """Events related to chat interactions"""
    session_id: str = ""
    user_id: str = ""
