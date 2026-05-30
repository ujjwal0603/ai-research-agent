from typing import List, Dict
from .models import EmbeddingModel

class EmbeddingProcessor:
    """Process documents and generate embeddings"""

    def __init__(self, embedding_model: EmbeddingModel, chunk_size: int = 500):
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size

    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        words = text.split()
        chunks = []
        chunk_overlap = self.chunk_size // 4

        i = 0
        while i < len(words):
            chunk = " ".join(words[i : i + self.chunk_size])
            chunks.append(chunk)
            i += self.chunk_size - chunk_overlap

        return chunks

    def process_document(self, document_id: str, text: str) -> List[Dict]:
        """Process document into chunks with embeddings"""
        chunks = self.chunk_text(text)
        embeddings = self.embedding_model.embed_batch(chunks)

        processed_chunks = [
            {
                "document_id": document_id,
                "chunk_index": idx,
                "text": chunk,
                "embedding": embedding,
            }
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings))
        ]

        return processed_chunks

    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for search query"""
        return self.embedding_model.embed_text(query)
