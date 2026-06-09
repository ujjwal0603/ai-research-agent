"""
Alembic environment configuration for async SQLAlchemy.

Reads the DATABASE_URL from the application settings and uses
the same Base metadata as the ORM models to auto-generate migrations.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from config.settings import get_settings
from database.connection import Base

# Import all models so they register with Base.metadata
import database.models  # noqa: F401

# ── Alembic Config ──────────────────────────────────

config = context.config
settings = get_settings()

# Set the sqlalchemy URL from application settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Logging config from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for auto-generation
target_metadata = Base.metadata


# ── Offline mode ────────────────────────────────────

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Generates SQL scripts without connecting to the database.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (async) ────────────────────────────

def do_run_migrations(connection: Connection) -> None:
    """Run migrations within a connection context."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with async support."""
    asyncio.run(run_async_migrations())


# ── Entry point ─────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
