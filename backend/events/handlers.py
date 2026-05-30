"""
Event handler registry with default logging handlers.

Registers built-in handlers for all event types to provide
observability out of the box.
"""

from __future__ import annotations

import logging

from config.constants import EventType
from events.bus import EventBus
from events.events import BaseEvent

logger = logging.getLogger(__name__)


async def _log_event(event: BaseEvent) -> None:
    """Default handler that logs all events"""
    event_type = event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type)
    logger.info(
        f"Event: {event_type} | trace={event.trace_id} | "
        f"payload_keys={list(event.payload.keys())}"
    )


class EventHandlerRegistry:
    """Registers default handlers for all event types"""

    @staticmethod
    def register_default_handlers(bus: EventBus) -> None:
        """Register logging handlers for all defined event types"""
        for event_type in EventType:
            bus.subscribe(event_type.value, _log_event)

        logger.info(
            f"Registered default handlers for {len(EventType)} event types"
        )
