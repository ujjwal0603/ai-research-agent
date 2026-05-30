"""
In-process event bus for pub/sub communication.

Phase 1 implementation uses asyncio-based in-process pub/sub.
Will migrate to Redis Streams in Phase 4 for distributed events.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Callable

from events.events import BaseEvent

logger = logging.getLogger(__name__)


class EventBus:
    """Simple in-process async pub/sub event bus"""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable]] = defaultdict(list)
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """
        Register a handler for an event type.

        Args:
            event_type: The event type string (e.g., "document.uploaded")
            handler: Async callable that takes a BaseEvent
        """
        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed handler to '{event_type}'")

    async def publish(self, event: BaseEvent) -> None:
        """
        Publish an event to all subscribed handlers.

        Handlers are called concurrently. Failures in individual
        handlers are logged but do not block other handlers.
        """
        event_type = event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type)
        handlers = self._handlers.get(event_type, [])

        if not handlers:
            logger.debug(f"No handlers for event '{event_type}'")
            return

        logger.info(
            f"Publishing '{event_type}' to {len(handlers)} handler(s)"
        )

        async with self._lock:
            tasks = []
            for handler in handlers:
                tasks.append(self._safe_call(handler, event, event_type))
            await asyncio.gather(*tasks)

    async def _safe_call(
        self, handler: Callable, event: BaseEvent, event_type: str
    ) -> None:
        """Call a handler with error catching"""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception as exc:
            logger.exception(
                f"Handler error for '{event_type}': {exc}"
            )

    def unsubscribe_all(self, event_type: str) -> None:
        """Remove all handlers for an event type"""
        self._handlers.pop(event_type, None)

    def clear(self) -> None:
        """Remove all handlers"""
        self._handlers.clear()
