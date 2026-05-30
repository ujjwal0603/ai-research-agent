from typing import List, Dict
from .vector_store import VectorStore

class QueryEngine:
    """Execute search queries against vector store"""

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict]:
        """Search for relevant documents"""
        results = self.vector_store.search(query_embedding, top_k)
        return results

    def rerank_results(self, results: List[Dict], scores: List[float]) -> List[Dict]:
        """Optional: Rerank results based on additional scoring"""
        ranked = sorted(
            zip(results, scores), key=lambda x: x[1], reverse=True
        )
        return [result for result, _ in ranked]

    def format_results(self, results: List[Dict]) -> List[Dict]:
        """Format raw vector store results for API response"""
        formatted = [
            {
                "document_id": r.get("document_id"),
                "file_name": r.get("file_name"),
                "score": r.get("score", 0.0),
                "content_preview": r.get("text", "")[:200],
            }
            for r in results
        ]
        return formatted
