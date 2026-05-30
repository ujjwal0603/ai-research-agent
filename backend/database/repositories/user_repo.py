"""
User repository — async data-access layer for user accounts.

Encapsulates all user-related database queries behind a clean
interface so service and route layers never touch SQLAlchemy directly.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User

logger = logging.getLogger(__name__)


class UserRepository:
    """Async CRUD operations for :class:`User` records.

    Every method receives an ``AsyncSession`` so the caller controls
    transaction boundaries (via the ``get_db`` dependency in FastAPI).
    """

    # ── Create ──────────────────────────────────────

    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        email: str,
        name: str,
        password_hash: str,
    ) -> User:
        """Insert a new user record.

        Args:
            db: Active async session.
            email: User email (must be unique).
            name: Display name.
            password_hash: Bcrypt-hashed password.

        Returns:
            The newly created ``User`` ORM instance.
        """
        user = User(
            email=email,
            name=name,
            password_hash=password_hash,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        logger.info("Created user %s (%s)", user.id, email)
        return user

    # ── Read by Email ──────────────────────────────

    @staticmethod
    async def get_by_email(
        db: AsyncSession,
        email: str,
    ) -> Optional[User]:
        """Look up a user by their email address.

        Args:
            db: Active async session.
            email: Email to search for (case-sensitive).

        Returns:
            The ``User`` if found, else ``None``.
        """
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ── Read by ID ─────────────────────────────────

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> Optional[User]:
        """Fetch a single user by their primary key.

        Args:
            db: Active async session.
            user_id: User UUID.

        Returns:
            The ``User`` if found, else ``None``.
        """
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ── Update Last Login ──────────────────────────

    @staticmethod
    async def update_last_login(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> None:
        """Set the ``last_login`` timestamp to now (UTC).

        Args:
            db: Active async session.
            user_id: User UUID.
        """
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(last_login=datetime.now(timezone.utc))
        )
        await db.execute(stmt)
        logger.debug("Updated last_login for user %s", user_id)
