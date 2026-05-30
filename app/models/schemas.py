from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class DocumentBase(BaseModel):
    """Base model for documents"""
    title: str
    description: Optional[str] = None
    file_name: str

class DocumentCreate(DocumentBase):
    """Model for creating documents"""
    pass

class Document(DocumentBase):
    """Full document model with metadata"""
    id: str
    file_size: int
    upload_date: datetime
    vector_ids: List[str] = []

    class Config:
        from_attributes = True

class UploadResponse(BaseModel):
    """Response after file upload"""
    document_id: str
    file_name: str
    status: str = "uploaded"
    chunks_created: int
    message: str

class QueryRequest(BaseModel):
    """Model for search/retrieval queries"""
    query: str
    top_k: int = Field(default=5, ge=1, le=100)
    filters: Optional[dict] = None

class SearchResult(BaseModel):
    """Individual search result"""
    document_id: str
    file_name: str
    score: float
    content_preview: str

class QueryResponse(BaseModel):
    """Response for query/retrieval"""
    query: str
    results: List[SearchResult]
    total_results: int

class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    version: str
    environment: str
