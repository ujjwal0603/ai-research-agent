"""
Centralized service registry with lazy initialization.

All services are created on first access and cached for reuse.
This avoids loading heavy models (sentence-transformers) at import time
and ensures singleton instances throughout the application.

Usage in routes:
    from core import get_embedding_service, get_faiss_store
    
    embedding_service = get_embedding_service()
    faiss_store = get_faiss_store()
"""

from config.settings import get_settings

_services: dict = {}


def get_pdf_service():
    """Get PDF extraction service"""
    if "pdf" not in _services:
        from services.pdf_service import PDFService
        _services["pdf"] = PDFService()
    return _services["pdf"]


def get_chunking_service():
    """Get text chunking service"""
    if "chunking" not in _services:
        from services.chunking_service import ChunkingService
        settings = get_settings()
        _services["chunking"] = ChunkingService(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )
    return _services["chunking"]


def get_embedding_service():
    """Get embedding service (loads sentence-transformers model on first call)"""
    if "embedding" not in _services:
        from services.embedding_service import EmbeddingService
        settings = get_settings()
        _services["embedding"] = EmbeddingService(settings.EMBEDDING_MODEL)
    return _services["embedding"]


def get_faiss_store():
    """Get FAISS vector store (loads/creates index on first call)"""
    if "faiss" not in _services:
        from vectorstore.faiss_store import FAISSStore
        settings = get_settings()
        emb = get_embedding_service()
        _services["faiss"] = FAISSStore(
            dimension=emb.dimension,
            index_path=settings.FAISS_INDEX_PATH,
        )
    return _services["faiss"]


def get_chat_service():
    """Get chat/RAG service (Gemini API)"""
    if "chat" not in _services:
        from services.chat_service import ChatService
        settings = get_settings()
        _services["chat"] = ChatService(
            api_key=settings.GEMINI_API_KEY,
            model_name=settings.GEMINI_MODEL,
        )
    return _services["chat"]
