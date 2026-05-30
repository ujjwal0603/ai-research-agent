from typing import List, Dict
from app.embeddings import EmbeddingProcessor
from app.retrieval import VectorStore
from app.utils import setup_logger

logger = setup_logger(__name__)

class EmbeddingsService:
    """Handle embedding generation and management"""

    def __init__(self, embedding_processor: EmbeddingProcessor, vector_store: VectorStore):
        self.embedding_processor = embedding_processor
        self.vector_store = vector_store

    def embed_and_store(self, document_id: str, text: str) -> List[str]:
        """Process document and store embeddings"""
        try:
            # Process document into chunks with embeddings
            processed_chunks = self.embedding_processor.process_document(
                document_id, text
            )
            logger.debug(f"Created {len(processed_chunks)} chunks for {document_id}")

            # Store in vector store
            vector_ids = self.vector_store.add_vectors(processed_chunks)
            logger.info(f"Stored {len(vector_ids)} vectors for document {document_id}")

            return vector_ids

        except Exception as e:
            logger.error(f"Embedding storage failed for {document_id}: {str(e)}")
            raise

    def delete_embeddings(self, vector_ids: List[str]) -> bool:
        """Delete embeddings for a document"""
        try:
            success = self.vector_store.delete_vectors(vector_ids)
            logger.info(f"Deleted {len(vector_ids)} vectors")
            return success
        except Exception as e:
            logger.error(f"Deletion failed: {str(e)}")
            raise

    def get_embedding_stats(self) -> Dict:
        """Get embedding statistics"""
        return {
            "model": self.embedding_processor.embedding_model.model_name,
            "dimension": self.embedding_processor.embedding_model.dimension,
            "chunk_size": self.embedding_processor.chunk_size,
        }
