"""
In-memory sliding-window rate limiter (Phase 1).

Uses a dictionary keyed by user-id with a deque of request timestamps.
In Phase 2 this should be replaced by a Redis-backed implementation.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import Depends, HTTPException, status

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory sliding-window rate limiter.

    Tracks request timestamps per user-id.  When the number of requests
    inside the current window exceeds *max_requests*, subsequent calls
    are rejected with HTTP 429.
    """

    def __init__(self) -> None:
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)

    async def check_rate_limit(
        self,
        user_id: str,
        max_requests: int = 60,
        window_seconds: int = 60,
    ) -> bool:
        """Return ``True`` if the request is allowed, ``False`` if rate-limited.

        Side-effect: records the current timestamp for *user_id*.
        """
        now = time.monotonic()
        window = self._requests[user_id]

        # Evict timestamps outside the current window
        while window and window[0] <= now - window_seconds:
            window.popleft()

        if len(window) >= max_requests:
            logger.warning(
                "Rate limit exceeded for user %s (%d/%d in %ds)",
                user_id,
                len(window),
                max_requests,
                window_seconds,
            )
            return False

        window.append(now)
        return True

    def get_rate_limit_dependency(
        self,
        max_requests: int = 60,
        window_seconds: int = 60,
    ):
        """Return a FastAPI ``Depends``-compatible callable.

        Usage::

            limiter = RateLimiter()
            rate_dep = limiter.get_rate_limit_dependency(max_requests=30)

            @router.get("/some-endpoint", dependencies=[Depends(rate_dep)])
            async def some_endpoint(): ...
        """
        rate_limiter = self  # capture in closure

        async def _dependency(
            current_user: dict = Depends(_get_current_user_stub),
        ) -> None:
            user_id = current_user.get("user_id", "anonymous")
            allowed = await rate_limiter.check_rate_limit(
                user_id,
                max_requests=max_requests,
                window_seconds=window_seconds,
            )
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later.",
                )

        return _dependency


# ---------------------------------------------------------------------------
# Lazy import of get_current_user to avoid circular dependency at module load
# ---------------------------------------------------------------------------

def _get_current_user_stub():
    """Deferred import wrapper so rate_limit.py doesn't import auth at top."""
    from api.middleware.auth import get_current_user
    return get_current_user
