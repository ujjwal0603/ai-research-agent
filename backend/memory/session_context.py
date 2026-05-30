"""
Session context manager — stores per-session state in Redis.

Key pattern: ``session:{session_id}:context``
Default TTL: 24 hours.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from memory.shared_memory import SharedMemory

logger = logging.getLogger(__name__)

_SESSION_TTL = 86_400  # 24 hours


class SessionManager:
    """Create, read, update, and delete session contexts in Redis.

    Each session is a JSON dict stored under
    ``session:<session_id>:context`` with a 24-hour TTL that resets
    on every update so active sessions stay alive.
    """

    def __init__(self, shared_memory: SharedMemory) -> None:
        self._mem = shared_memory

    # ── Helpers ─────────────────────────────────────

    @staticmethod
    def _context_key(session_id: str) -> str:
        return f"session:{session_id}:context"

    # ── Public API ──────────────────────────────────

    async def create_session(
        self,
        user_id: str,
        title: Optional[str] = None,
    ) -> str:
        """Create a new session and return its UUID.

        Args:
            user_id: Owner of the session.
            title: Optional human-readable session title.

        Returns:
            The generated session id (UUID4 hex).
        """
        session_id = uuid.uuid4().hex
        context: Dict[str, Any] = {
            "session_id": session_id,
            "user_id": user_id,
            "title": title or f"Session {session_id[:8]}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {},
        }
        await self._mem.set_json(
            self._context_key(session_id),
            context,
            ttl=_SESSION_TTL,
        )
        logger.info("Created session %s for user %s", session_id, user_id)
        return session_id

    async def get_context(self, session_id: str) -> Dict[str, Any]:
        """Retrieve the session context dict.

        Returns an empty dict (not ``None``) when the session doesn't
        exist or Redis is unavailable.
        """
        data = await self._mem.get_json(self._context_key(session_id))
        return data or {}

    async def update_context(
        self,
        session_id: str,
        updates: Dict[str, Any],
    ) -> None:
        """Merge *updates* into the existing session context.

        Resets the TTL so active sessions are kept alive.
        """
        context = await self.get_context(session_id)
        context.update(updates)
        context["updated_at"] = datetime.now(timezone.utc).isoformat()
        await self._mem.set_json(
            self._context_key(session_id),
            context,
            ttl=_SESSION_TTL,
        )
        logger.debug("Updated session context %s", session_id)

    async def delete_session(self, session_id: str) -> None:
        """Remove a session's context from Redis."""
        await self._mem.delete(self._context_key(session_id))
        logger.info("Deleted session %s", session_id)
