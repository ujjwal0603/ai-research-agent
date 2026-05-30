"""
SQLAlchemy ORM models for the AI Research Agent Platform V2.

All models use:
- UUID primary keys
- ``Mapped`` / ``mapped_column`` type-annotated style
- Timezone-aware UTC timestamps
- Proper foreign keys, indexes, and cascade rules
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base

logger = logging.getLogger(__name__)


# ── Helpers ─────────────────────────────────────────


def _utcnow() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def _new_uuid() -> uuid.UUID:
    """Generate a new UUID4."""
    return uuid.uuid4()


# ── User ────────────────────────────────────────────


class User(Base):
    """Registered platform user."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=_new_uuid,
    )
    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Relationships ──
    documents: Mapped[List[Document]] = relationship(
        "Document",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    sessions: Mapped[List[Session]] = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    learning_paths: Mapped[List[LearningPath]] = relationship(
        "LearningPath",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id!s} email={self.email!r}>"


# ── Document ────────────────────────────────────────


class Document(Base):
    """An uploaded document (PDF) with processing metadata."""

    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_user_uploaded", "user_id", "uploaded_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=_new_uuid,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    original_name: Mapped[str] = mapped_column(String(512), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content_hash: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
        default=None,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
        index=True,
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Relationships ──
    user: Mapped[User] = relationship("User", back_populates="documents")
    chunks: Mapped[List[Chunk]] = relationship(
        "Chunk",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Chunk.chunk_index",
    )
    summaries: Mapped[List[Summary]] = relationship(
        "Summary",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    quizzes: Mapped[List[Quiz]] = relationship(
        "Quiz",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id!s} filename={self.filename!r}>"


# ── Chunk ───────────────────────────────────────────


class Chunk(Base):
    """A text chunk extracted from a document."""

    __tablename__ = "chunks"
    __table_args__ = (
        Index("ix_chunks_document_index", "document_id", "chunk_index"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=_new_uuid,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    char_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
        default=None,
    )
    embedding_id: Mapped[Optional[str]] = mapped_column(
        String(256),
        nullable=True,
    )

    # ── Relationships ──
    document: Mapped[Document] = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        return (
            f"<Chunk id={self.id!s} "
            f"doc={self.document_id!s} idx={self.chunk_index}>"
        )


# ── Session ─────────────────────────────────────────


class Session(Base):
    """A chat / conversation session."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=_new_uuid,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    context: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    # ── Relationships ──
    user: Mapped[User] = relationship("User", back_populates="sessions")
    messages: Mapped[List[Message]] = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:
        return f"<Session id={self.id!s} user={self.user_id!s}>"


# ── Message ─────────────────────────────────────────


class Message(Base):
    """A single message within a chat session."""

    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_session_created", "session_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=_new_uuid,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=None,
    )
    agent_trace: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )

    # ── Relationships ──
    session: Mapped[Session] = relationship("Session", back_populates="messages")

    def __repr__(self) -> str:
        return (
            f"<Message id={self.id!s} "
            f"session={self.session_id!s} role={self.role!r}>"
        )


# ── Summary ─────────────────────────────────────────


class Summary(Base):
    """A generated summary for a document."""

    __tablename__ = "summaries"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=_new_uuid,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    summary_type: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )

    # ── Relationships ──
    document: Mapped[Document] = relationship("Document", back_populates="summaries")

    def __repr__(self) -> str:
        return (
            f"<Summary id={self.id!s} "
            f"doc={self.document_id!s} type={self.summary_type!r}>"
        )


# ── Quiz ────────────────────────────────────────────


class Quiz(Base):
    """A generated quiz for a document."""

    __tablename__ = "quizzes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=_new_uuid,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    quiz_type: Mapped[str] = mapped_column(String(32), nullable=False)
    questions: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=None,
    )
    difficulty: Mapped[str] = mapped_column(
        String(32),
        default="medium",
        nullable=False,
    )
    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )

    # ── Relationships ──
    document: Mapped[Document] = relationship("Document", back_populates="quizzes")

    def __repr__(self) -> str:
        return (
            f"<Quiz id={self.id!s} "
            f"doc={self.document_id!s} type={self.quiz_type!r}>"
        )


# ── Learning Path ──────────────────────────────────


class LearningPath(Base):
    """A personalised learning path for a user."""

    __tablename__ = "learning_paths"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=_new_uuid,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    concept_graph: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=None,
    )
    milestones: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=None,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="active",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    # ── Relationships ──
    user: Mapped[User] = relationship("User", back_populates="learning_paths")

    def __repr__(self) -> str:
        return f"<LearningPath id={self.id!s} title={self.title!r}>"


# ── Agent Log ──────────────────────────────────────


class AgentLog(Base):
    """Audit log entry for agent task execution."""

    __tablename__ = "agent_logs"
    __table_args__ = (
        Index("ix_agent_logs_trace", "trace_id"),
        Index("ix_agent_logs_agent_created", "agent_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=_new_uuid,
    )
    trace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    input_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=None,
    )
    output_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=None,
    )
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<AgentLog id={self.id!s} "
            f"agent={self.agent_id!r} action={self.action!r}>"
        )
