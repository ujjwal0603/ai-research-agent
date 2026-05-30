"""
Document repository — async data-access layer for documents.

Encapsulates all document-related database queries behind a clean
interface so service and route layers never touch SQLAlchemy directly.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Document

logger = logging.getLogger(__name__)


class DocumentRepository:
    """Async CRUD operations for :class:`Document` records.

    Every method receives an ``AsyncSession`` so the caller controls
    transaction boundaries (via the ``get_db`` dependency in FastAPI).
    """

    # ── Create ──────────────────────────────────────

    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        filename: str,
        original_name: str,
        page_count: int = 0,
        chunk_count: int = 0,
        file_size_bytes: int = 0,
        content_hash: Optional[str] = None,
        metadata: Optional[dict] = None,
        status: str = "pending",
    ) -> Document:
        """Insert a new document record.

        Args:
            db: Active async session.
            user_id: Owning user UUID.
            filename: Stored filename on disk.
            original_name: Original upload filename.
            page_count: Number of pages extracted.
            chunk_count: Number of text chunks.
            file_size_bytes: File size in bytes.
            content_hash: SHA-256 of file contents (dedup).
            metadata: Arbitrary JSON metadata.
            status: Initial processing status.

        Returns:
            The newly created ``Document`` ORM instance.
        """
        document = Document(
            user_id=user_id,
            filename=filename,
            original_name=original_name,
            page_count=page_count,
            chunk_count=chunk_count,
            file_size_bytes=file_size_bytes,
            content_hash=content_hash,
            metadata_=metadata,
            status=status,
        )
        db.add(document)
        await db.flush()
        await db.refresh(document)
        logger.info("Created document %s for user %s", document.id, user_id)
        return document

    # ── Read by ID ─────────────────────────────────

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        document_id: uuid.UUID,
    ) -> Optional[Document]:
        """Fetch a single document by its primary key.

        Args:
            db: Active async session.
            document_id: Document UUID.

        Returns:
            The ``Document`` if found, else ``None``.
        """
        stmt = select(Document).where(Document.id == document_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ── List by User ───────────────────────────────

    @staticmethod
    async def list_by_user(
        db: AsyncSession,
        user_id: uuid.UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Document]:
        """Return documents owned by a given user (paginated).

        Args:
            db: Active async session.
            user_id: Owner user UUID.
            limit: Maximum number of records.
            offset: Number of records to skip.

        Returns:
            List of ``Document`` instances, ordered newest-first.
        """
        stmt = (
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.uploaded_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ── Delete ─────────────────────────────────────

    @staticmethod
    async def delete(
        db: AsyncSession,
        document_id: uuid.UUID,
    ) -> bool:
        """Delete a document by ID.

        Cascades will remove associated chunks, summaries, and quizzes.

        Args:
            db: Active async session.
            document_id: Document UUID.

        Returns:
            ``True`` if a row was deleted, ``False`` if not found.
        """
        stmt = delete(Document).where(Document.id == document_id)
        result = await db.execute(stmt)
        deleted = result.rowcount > 0
        if deleted:
            logger.info("Deleted document %s", document_id)
        else:
            logger.warning("Document %s not found for deletion", document_id)
        return deleted

    # ── Update Status ──────────────────────────────

    @staticmethod
    async def update_status(
        db: AsyncSession,
        document_id: uuid.UUID,
        status: str,
        *,
        page_count: Optional[int] = None,
        chunk_count: Optional[int] = None,
    ) -> Optional[Document]:
        """Update a document's processing status (and optionally counts).

        Args:
            db: Active async session.
            document_id: Document UUID.
            status: New status string.
            page_count: Updated page count (if available).
            chunk_count: Updated chunk count (if available).

        Returns:
            The updated ``Document``, or ``None`` if not found.
        """
        values: dict = {"status": status}
        if status == "processed":
            values["processed_at"] = datetime.now(timezone.utc)
        if page_count is not None:
            values["page_count"] = page_count
        if chunk_count is not None:
            values["chunk_count"] = chunk_count

        stmt = (
            update(Document)
            .where(Document.id == document_id)
            .values(**values)
            .returning(Document)
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        if row is not None:
            logger.info(
                "Updated document %s status to %r",
                document_id,
                status,
            )
        return row
