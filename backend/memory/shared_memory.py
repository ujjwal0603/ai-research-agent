"""
Redis-backed shared memory with graceful degradation.

If Redis is unavailable the class logs a warning and returns ``None``
for reads / silently discards writes so the rest of the application
can continue in a degraded mode.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import redis.asyncio as aioredis

from config.settings import get_settings

logger = logging.getLogger(__name__)


class SharedMemory:
    """Async Redis wrapper with JSON helpers and graceful fallback.

    Usage::

        mem = SharedMemory()
        await mem.set("key", "value", ttl=300)
        val = await mem.get("key")
        await mem.close()
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._redis_url: str = settings.REDIS_URL
        self._client: Optional[aioredis.Redis] = None
        self._available: bool = False

    # ── Connection management ───────────────────────

    async def _ensure_connection(self) -> Optional[aioredis.Redis]:
        """Lazily create (or reconnect) the Redis client."""
        if self._client is not None and self._available:
            return self._client
        try:
            self._client = aioredis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            await self._client.ping()
            self._available = True
            logger.info("Connected to Redis at %s", self._redis_url)
            return self._client
        except Exception as exc:
            logger.warning("Redis unavailable (%s) — running in degraded mode", exc)
            self._available = False
            return None

    # ── Primitive operations ────────────────────────

    async def get(self, key: str) -> Optional[str]:
        """Get a string value by key. Returns ``None`` if Redis is down."""
        client = await self._ensure_connection()
        if client is None:
            return None
        try:
            return await client.get(key)
        except Exception as exc:
            logger.warning("Redis GET failed for key=%s: %s", key, exc)
            self._available = False
            return None

    async def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None,
    ) -> None:
        """Set a string value, optionally with a TTL in seconds."""
        client = await self._ensure_connection()
        if client is None:
            return
        try:
            if ttl is not None:
                await client.setex(key, ttl, value)
            else:
                await client.set(key, value)
        except Exception as exc:
            logger.warning("Redis SET failed for key=%s: %s", key, exc)
            self._available = False

    async def delete(self, key: str) -> None:
        """Delete a key."""
        client = await self._ensure_connection()
        if client is None:
            return
        try:
            await client.delete(key)
        except Exception as exc:
            logger.warning("Redis DELETE failed for key=%s: %s", key, exc)
            self._available = False

    async def exists(self, key: str) -> bool:
        """Check whether a key exists."""
        client = await self._ensure_connection()
        if client is None:
            return False
        try:
            return bool(await client.exists(key))
        except Exception as exc:
            logger.warning("Redis EXISTS failed for key=%s: %s", key, exc)
            self._available = False
            return False

    # ── JSON helpers ────────────────────────────────

    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Deserialise a JSON value stored under *key*."""
        raw = await self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Corrupt JSON at key=%s", key)
            return None

    async def set_json(
        self,
        key: str,
        value: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> None:
        """Serialise *value* to JSON and store it."""
        await self.set(key, json.dumps(value, default=str), ttl=ttl)

    # ── Health / lifecycle ──────────────────────────

    async def health_check(self) -> bool:
        """Return ``True`` if Redis responds to PING."""
        client = await self._ensure_connection()
        if client is None:
            return False
        try:
            return await client.ping()
        except Exception:
            self._available = False
            return False

    async def close(self) -> None:
        """Gracefully close the Redis connection."""
        if self._client is not None:
            try:
                await self._client.close()
                logger.info("Redis connection closed")
            except Exception as exc:
                logger.warning("Error closing Redis: %s", exc)
            finally:
                self._client = None
                self._available = False
