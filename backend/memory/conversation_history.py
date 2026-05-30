"""
Conversation history stored as a JSON list in Redis.

Key pattern: ``session:{session_id}:history``
Default TTL: 24 hours (reset on every write).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from memory.shared_memory import SharedMemory

logger = logging.getLogger(__name__)

_HISTORY_TTL = 86_400  # 24 hours


class ConversationHistory:
    """Append-only message log per session, backed by Redis.

    Messages are stored as a JSON list under
    ``session:<session_id>:history``.  The TTL resets on every
    ``add_message`` call so the history stays alive as long as the
    conversation is active.
    """

    def __init__(self, shared_memory: SharedMemory) -> None:
        self._mem = shared_memory

    # ── Helpers ─────────────────────────────────────

    @staticmethod
    def _history_key(session_id: str) -> str:
        return f"session:{session_id}:history"

    # ── Public API ──────────────────────────────────

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sources: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Append a message to the conversation history.

        Args:
            session_id: Session that owns the conversation.
            role: ``"user"`` or ``"assistant"``.
            content: Message text.
            sources: Optional list of source dicts (for assistant messages).
        """
        key = self._history_key(session_id)
        history = await self._load(key)

        message: Dict[str, Any] = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if sources:
            message["sources"] = sources

        history.append(message)
        await self._save(key, history)
        logger.debug(
            "Added %s message to session %s (total=%d)",
            role,
            session_id,
            len(history),
        )

    async def get_history(
        self,
        session_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Return the most recent *limit* messages for *session_id*.

        Returns:
            A list of message dicts ordered from oldest to newest.
            Empty list when the session has no history or Redis is down.
        """
        history = await self._load(self._history_key(session_id))
        return history[-limit:]

    async def clear_history(self, session_id: str) -> None:
        """Remove all messages for *session_id*."""
        await self._mem.delete(self._history_key(session_id))
        logger.info("Cleared history for session %s", session_id)

    # ── Internal ────────────────────────────────────

    async def _load(self, key: str) -> List[Dict[str, Any]]:
        data = await self._mem.get_json(key)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "messages" in data:
            return data["messages"]
        return []

    async def _save(self, key: str, history: List[Dict[str, Any]]) -> None:
        # Store as a plain JSON list
        await self._mem.set_json(key, history, ttl=_HISTORY_TTL)  # type: ignore[arg-type]
