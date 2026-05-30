from typing import List
from app.models import QueryResponse, SearchResult
from app.retrieval import QueryEngine
from app.embeddings import EmbeddingProcessor
from app.utils import setup_logger

logger = setup_logger(__name__)

class RetrievalService:
    """Handle document retrieval and search operations"""

    def __init__(self, query_engine: QueryEngine, embedding_processor: EmbeddingProcessor):
        self.query_engine = query_engine
        self.embedding_processor = embedding_processor

    def search(self, query: str, top_k: int = 5) -> QueryResponse:
        """Execute search query"""
        try:
            # Generate embedding for query
            query_embedding = self.embedding_processor.embed_query(query)
            logger.debug(f"Generated query embedding for: {query}")

            # Search vector store
            raw_results = self.query_engine.search(query_embedding, top_k)
            logger.info(f"Found {len(raw_results)} results for query: {query}")

            # Format results
            formatted_results = self.query_engine.format_results(raw_results)

            return QueryResponse(
                query=query,
                results=formatted_results,
                total_results=len(formatted_results),
            )

        except Exception as e:
            logger.error(f"Search failed for query '{query}': {str(e)}")
            return QueryResponse(query=query, results=[], total_results=0)

    def batch_search(self, queries: List[str], top_k: int = 5) -> List[QueryResponse]:
        """Execute multiple search queries"""
        return [self.search(query, top_k) for query in queries]

    def get_document_stats(self, document_id: str) -> dict:
        """Get statistics for a document"""
        # Placeholder: Implement based on your needs
        return {"document_id": document_id, "chunks": 0, "indexed_at": None}
