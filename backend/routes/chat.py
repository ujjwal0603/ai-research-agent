"""
Chat/RAG endpoint.

RAG Pipeline:
  1. Embed user query using sentence-transformers
  2. Search FAISS for top-K most similar chunks
  3. Build context prompt from retrieved chunks
  4. Generate answer using Gemini API
  5. Return answer with source chunk references
"""

import logging

from fastapi import APIRouter, HTTPException
from models.schemas import ChatRequest, ChatResponse, SourceChunk
from config.settings import get_settings
from core import get_embedding_service, get_faiss_store, get_chat_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])
settings = get_settings()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Ask a question about uploaded documents.

    Uses RAG: retrieves relevant chunks, then generates
    an answer grounded in the retrieved context.
    """
    query = request.query.strip()

    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        # Step 1: Embed the query
        embedding_service = get_embedding_service()
        query_embedding = embedding_service.embed_query(query)

        # Step 2: Search FAISS for relevant chunks
        faiss_store = get_faiss_store()

        if faiss_store.total_vectors == 0:
            raise HTTPException(
                status_code=400,
                detail="No documents have been uploaded yet. Please upload a PDF first.",
            )

        results = faiss_store.search(query_embedding, top_k=request.top_k)

        if not results:
            return ChatResponse(
                answer="I couldn't find any relevant information in the uploaded documents.",
                sources=[],
                query=query,
            )

        # Step 3 & 4: Generate answer using Gemini with retrieved context
        chat_service = get_chat_service()
        answer = chat_service.generate_answer(query, results)

        # Step 5: Format source chunks for the response
        sources = [
            SourceChunk(
                text=r["text"],
                document_name=r.get("document_name", "Unknown"),
                page_number=r.get("page_number"),
                chunk_index=r.get("chunk_index", 0),
                score=round(r.get("score", 0.0), 4),
            )
            for r in results
        ]

        return ChatResponse(
            answer=answer,
            sources=sources,
            query=query,
        )

    except HTTPException:
        raise
    except ValueError as e:
        # Gemini API key not configured
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Chat failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")
