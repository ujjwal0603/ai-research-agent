"""
Repository package for the AI Research Agent Platform V2.

Re-exports repository classes for convenient imports:
    from database.repositories import DocumentRepository, UserRepository
"""

from __future__ import annotations

from database.repositories.document_repo import DocumentRepository
from database.repositories.user_repo import UserRepository

__all__ = [
    "DocumentRepository",
    "UserRepository",
]
