"""
Database package for the AI Research Agent Platform V2.

Re-exports core database utilities so consumers can do:
    from database import get_db, init_db, Base
"""

from __future__ import annotations

from database.connection import Base, async_session_maker, get_db, init_db

__all__ = [
    "Base",
    "async_session_maker",
    "get_db",
    "init_db",
]
