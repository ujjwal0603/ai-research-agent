"""
Chat request/response schemas with streaming and multi-agent trace support.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from config.constants import SearchStrategy, LLMProvider


class SourceChunk(BaseModel):
    """A source chunk used to ground an answer."""

    text: str
    document_name: str
    page_number: Optional[int] = None
    chunk_index: int = 0
    score: float = 0.0
    document_id: Optional[str] = None


class Citation(BaseModel):
    """Inline citation referencing a source chunk."""

    source_index: int = Field(..., description="Index into the sources list")
    text: str = Field(..., description="Cited excerpt")
    document_name: str = Field(default="", description="Originating document")


class ChatRequest(BaseModel):
    """Request body for the V2 chat endpoint."""

    query: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = Field(default=None, description="Session UUID for context")
    top_k: int = Field(default=5, ge=1, le=20)
    search_strategy: str = Field(default=SearchStrategy.HYBRID, description="dense|sparse|hybrid")
    document_ids: Optional[List[str]] = Field(default=None, description="Scope to specific docs")
    provider: str = Field(default=LLMProvider.AUTO, description="LLM provider override")
    stream: bool = Field(default=False, description="Enable SSE streaming")


class ChatResponse(BaseModel):
    """Non-streaming chat response."""

    answer: str
    sources: List[SourceChunk] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    query: str
    session_id: Optional[str] = None
    trace: Optional[Dict[str, Any]] = None


class SSEEvent(BaseModel):
    """Individual SSE event payload."""

    event: str = Field(..., description="Event type (start|token|sources|done|error)")
    data: Any = Field(..., description="Event payload")
