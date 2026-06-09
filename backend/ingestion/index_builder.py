"""
Index builder for creating and managing Qdrant vector indexes.

Embeds document chunks using the embedding model and upserts
them into Qdrant collections. Also builds document centroids
for the recommendation system.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from config.constants import QDRANT_COLLECTION_CHUNKS, QDRANT_COLLECTION_CENTROIDS

if TYPE_CHECKING:
    from models_layer.embedding_model import EmbeddingModel
    from vectorstore.qdrant_store import QdrantStore

logger = logging.getLogger(__name__)


class IndexBuilder:
    """Builds and manages Qdrant vector indexes from document chunks"""

    def __init__(
        self,
        embedding_model: EmbeddingModel,
        qdrant_store: QdrantStore,
    ) -> None:
        self._embedding = embedding_model
        self._qdrant = qdrant_store

    async def build_index(
        self, document_id: str, chunks: list[dict]
    ) -> int:
        """
        Embed all chunks and store them in Qdrant.

        Args:
            document_id: UUID of the document
            chunks: List of enriched chunk dicts with 'text' field

        Returns:
            Number of chunks indexed
        """
        if not chunks:
            logger.warning(f"No chunks to index for document {document_id}")
            return 0

        texts = [c["text"] for c in chunks]

        logger.info(f"Embedding {len(texts)} chunks for document {document_id}...")
        if texts:
            logger.info(f"Sample chunk text from {document_id}: {repr(texts[0][:200])}")
        
        embeddings = await self._embedding.embed_texts(texts)

        # Build payloads for Qdrant
        payloads = []
        for chunk in chunks:
            payloads.append({
                "document_id": chunk.get("document_id", document_id),
                "chunk_index": chunk.get("chunk_index", 0),
                "page_number": chunk.get("page_number", 0),
                "text": chunk["text"],
                "char_count": chunk.get("char_count", len(chunk["text"])),
                "filename": chunk.get("filename", ""),
                "user_id": chunk.get("user_id", ""),
            })

        # Upsert to Qdrant
        vector_ids = await self._qdrant.add_vectors(
            vectors=embeddings,
            payloads=payloads,
            collection=QDRANT_COLLECTION_CHUNKS,
        )

        logger.info(
            f"Indexed {len(vector_ids)} chunks for document {document_id}"
        )

        # Build centroid for recommendation system
        await self.build_centroid(document_id, embeddings, chunks)

        return len(vector_ids)

    async def delete_index(self, document_id: str) -> int:
        """
        Delete all vectors for a document from Qdrant.

        Returns:
            Number of points deleted (approximate)
        """
        deleted = await self._qdrant.delete_by_filter(
            collection=QDRANT_COLLECTION_CHUNKS,
            filter_key="document_id",
            filter_value=document_id,
        )

        # Also delete centroid
        await self._qdrant.delete_by_filter(
            collection=QDRANT_COLLECTION_CENTROIDS,
            filter_key="document_id",
            filter_value=document_id,
        )

        logger.info(f"Deleted index for document {document_id}: ~{deleted} points")
        return deleted

    async def build_centroid(
        self,
        document_id: str,
        chunk_embeddings: np.ndarray,
        chunks: list[dict] | None = None,
    ) -> None:
        """
        Compute the centroid embedding for a document and store it.

        The centroid is the mean of all chunk embeddings, used for
        document-level similarity in the recommendation system.
        """
        if chunk_embeddings.size == 0:
            return

        centroid = np.mean(chunk_embeddings, axis=0, keepdims=True)

        # Normalize
        norm = np.linalg.norm(centroid)
        if norm > 0:
            centroid = centroid / norm

        filename = ""
        user_id = ""
        if chunks:
            filename = chunks[0].get("filename", "")
            user_id = chunks[0].get("user_id", "")

        payload = [{
            "document_id": document_id,
            "filename": filename,
            "user_id": user_id,
            "chunk_count": len(chunk_embeddings),
        }]

        await self._qdrant.add_vectors(
            vectors=centroid,
            payloads=payload,
            collection=QDRANT_COLLECTION_CENTROIDS,
        )

        logger.info(f"Built centroid for document {document_id}")
