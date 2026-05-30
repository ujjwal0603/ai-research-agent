"""
Embedding generation service using sentence-transformers.

Uses the all-MiniLM-L6-v2 model (384-dimensional embeddings)
for fast, high-quality text embeddings. Embeddings are L2-normalized
for cosine similarity search.
"""

from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generate text embeddings using sentence-transformers"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Load the embedding model.

        Args:
            model_name: HuggingFace model name for sentence-transformers
        """
        logger.info(f"Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.model_name = model_name
        logger.info(f"Embedding model loaded — dimension={self.dimension}")

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            numpy array of shape (n_texts, dimension), L2-normalized
        """
        if not texts:
            return np.array([], dtype=np.float32).reshape(0, self.dimension)

        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 100,
            normalize_embeddings=True,
        )

        logger.debug(f"Generated {len(embeddings)} embeddings")
        return embeddings.astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """
        Generate embedding for a single search query.

        Returns:
            numpy array of shape (1, dimension), L2-normalized
        """
        embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return embedding.astype(np.float32)
