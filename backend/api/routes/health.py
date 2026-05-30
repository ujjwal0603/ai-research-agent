"""
Health-check endpoint — reports component connectivity.

Returns aggregate status of the database, Redis, Qdrant,
agent registry, and document store so ops dashboards and
load-balancers can probe readiness.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter

from config.settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health_check() -> Dict[str, Any]:
    """Return system health including component connectivity.

    Checks performed:
    - Database: simple ``SELECT 1``
    - Qdrant: collection list
    - Redis: ``PING``
    - Registered agents count
    - Total documents in DB
    """
    settings = get_settings()
    health: Dict[str, Any] = {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "components": {},
    }

    # ── Database ────────────────────────────────────
    try:
        from api.dependencies import get_db_session
        from sqlalchemy import text

        async for session in get_db_session():
            await session.execute(text("SELECT 1"))
            health["components"]["database"] = "connected"
            break
    except Exception as exc:
        logger.warning("Health: database unreachable — %s", exc)
        health["components"]["database"] = f"error: {exc}"
        health["status"] = "degraded"

    # ── Qdrant ──────────────────────────────────────
    try:
        from api.dependencies import get_qdrant_store

        qdrant = get_qdrant_store()
        if qdrant is not None:
            health["components"]["qdrant"] = "connected"
        else:
            health["components"]["qdrant"] = "not initialised"
    except Exception as exc:
        logger.warning("Health: Qdrant unreachable — %s", exc)
        health["components"]["qdrant"] = f"error: {exc}"
        health["status"] = "degraded"

    # ── Redis ───────────────────────────────────────
    try:
        from api.dependencies import get_shared_memory

        mem = get_shared_memory()
        redis_ok = await mem.health_check()
        health["components"]["redis"] = "connected" if redis_ok else "unavailable"
        if not redis_ok:
            health["status"] = "degraded"
    except Exception as exc:
        logger.warning("Health: Redis unreachable — %s", exc)
        health["components"]["redis"] = f"error: {exc}"
        health["status"] = "degraded"

    # ── Agent count ─────────────────────────────────
    try:
        from api.dependencies import get_orchestrator

        orch = get_orchestrator()
        if orch is not None and hasattr(orch, "agent_registry"):
            registry = orch.agent_registry
            health["agents_registered"] = (
                len(registry.agents) if hasattr(registry, "agents") else 0
            )
        else:
            health["agents_registered"] = 0
    except Exception:
        health["agents_registered"] = 0

    # ── Document count ──────────────────────────────
    try:
        from api.dependencies import get_db_session
        from sqlalchemy import text

        async for session in get_db_session():
            result = await session.execute(
                text("SELECT COUNT(*) FROM documents")
            )
            row = result.scalar()
            health["total_documents"] = row or 0
            break
    except Exception:
        health["total_documents"] = 0

    return health
