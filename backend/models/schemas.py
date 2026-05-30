"""
Pydantic request/response models for all API endpoints.

Every endpoint uses typed schemas for input validation
and structured JSON responses.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


# ── Upload ──────────────────────────────────────────

class UploadResponse(BaseModel):
    """Response after successful PDF upload and processing"""
    document_id: str
    filename: str
    page_count: int
    chunk_count: int
    status: str = "processed"
    message: str


# ── Documents ───────────────────────────────────────

class DocumentInfo(BaseModel):
    """Metadata for an uploaded document"""
    document_id: str
    filename: str
    page_count: int
    chunk_count: int
    upload_time: str
    file_size_bytes: int


# ── Chat ────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Request body for the chat endpoint"""
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class SourceChunk(BaseModel):
    """A source chunk used to generate the answer"""
    text: str
    document_name: str
    page_number: Optional[int] = None
    chunk_index: int
    score: float


class ChatResponse(BaseModel):
    """Response from the chat endpoint"""
    answer: str
    sources: List[SourceChunk]
    query: str


# ── Health ──────────────────────────────────────────

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    documents_loaded: int
    total_chunks: int
