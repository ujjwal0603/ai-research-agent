"""
Document schemas for upload responses, listings, and detail views.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from config.constants import DocumentStatus


class UploadResponse(BaseModel):
    """Response after successful PDF upload and processing."""

    document_id: str = Field(..., description="Unique document UUID")
    filename: str = Field(..., description="Original filename")
    page_count: int = Field(..., ge=0, description="Number of pages")
    chunk_count: int = Field(..., ge=0, description="Number of indexed chunks")
    status: str = Field(default=DocumentStatus.PROCESSED, description="Processing status")
    message: str = Field(..., description="Human-readable summary")


class DocumentInfo(BaseModel):
    """Compact document metadata for list endpoints."""

    document_id: str
    filename: str
    page_count: int = 0
    chunk_count: int = 0
    upload_time: Optional[str] = None
    file_size_bytes: int = 0
    status: str = DocumentStatus.PROCESSED
    user_id: Optional[str] = None


class DocumentDetail(BaseModel):
    """Extended document metadata including processing info."""

    document_id: str
    filename: str
    page_count: int = 0
    chunk_count: int = 0
    upload_time: Optional[str] = None
    file_size_bytes: int = 0
    status: str = DocumentStatus.PROCESSED
    user_id: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    processed_at: Optional[datetime] = None
