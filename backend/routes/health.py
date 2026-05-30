"""Health check endpoint"""

import logging
from fastapi import APIRouter
from models.schemas import HealthResponse
from core import get_faiss_store

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Check API health, document count, and vector count"""
    faiss_store = get_faiss_store()
    docs = faiss_store.list_documents()

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        documents_loaded=len(docs),
        total_chunks=faiss_store.total_vectors,
    )
