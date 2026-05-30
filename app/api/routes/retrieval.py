from fastapi import APIRouter, HTTPException, Depends
from app.models import QueryRequest, QueryResponse
from app.services import RetrievalService
from app.utils import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/search", tags=["search"])

# Placeholder dependency - replace with actual service initialization
def get_retrieval_service() -> RetrievalService:
    # This would be initialized with QueryEngine and EmbeddingProcessor
    pass

@router.post("/query", response_model=QueryResponse)
async def search_documents(
    request: QueryRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
):
    """Search documents by query"""
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        logger.info(f"Processing search query: {request.query}")
        result = retrieval_service.search(request.query, request.top_k)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Search processing failed")

@router.post("/batch-query")
async def batch_search(queries: list[str]):
    """Search multiple queries at once"""
    # Placeholder: Implement batch search
    return {
        "total_queries": len(queries),
        "status": "processing",
    }

@router.get("/stats/{document_id}")
async def get_search_stats(document_id: str):
    """Get retrieval statistics for document"""
    # Placeholder: Implement stats retrieval
    return {
        "document_id": document_id,
        "times_retrieved": 0,
        "last_queried": None,
    }
