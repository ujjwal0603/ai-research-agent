"""
Events package — in-process event bus for decoupled communication.

Supports pub/sub patterns for document, agent, and chat events.
"""

from __future__ import annotations

from events.events import BaseEvent, DocumentEvent, AgentEvent, ChatEvent
from events.bus import EventBus

__all__ = [
    "BaseEvent",
    "DocumentEvent",
    "AgentEvent",
    "ChatEvent",
    "EventBus",
]
