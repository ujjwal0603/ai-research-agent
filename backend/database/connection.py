"""
Async SQLAlchemy engine, session factory, and database lifecycle helpers.

Provides:
- ``engine``:  Async engine bound to the configured DATABASE_URL.
- ``async_session_maker``:  Factory for scoped async sessions.
- ``get_db()``:  FastAPI dependency that yields a session per request.
- ``Base``:  Declarative base for ORM models.
- ``init_db()``:  Creates all tables (for development / first-run).
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# ── Engine ──────────────────────────────────────────

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

_engine_kwargs: dict = {"echo": settings.DEBUG}

if _is_sqlite:
    # SQLite doesn't support pool_size, pool_pre_ping, etc.
    from sqlalchemy.pool import StaticPool

    _engine_kwargs.update({
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    })
else:
    _engine_kwargs.update({
        "pool_size": 20,
        "max_overflow": 10,
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    })

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

# ── Session Factory ─────────────────────────────────

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# ── Declarative Base ───────────────────────────────


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


# ── FastAPI Dependency ──────────────────────────────


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for a single request.

    Usage in FastAPI routes::

        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...

    The session is automatically closed when the request finishes.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Table Creation ──────────────────────────────────


async def init_db() -> None:
    """Create all tables defined by ORM models.

    Intended for development and first-run bootstrapping.
    Production deployments should use Alembic migrations instead.
    """
    # Import models so they register with ``Base.metadata``
    import database.models  # noqa: F401

    logger.info("Creating database tables …")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully.")
