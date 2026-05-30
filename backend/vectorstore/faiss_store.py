"""
FAISS vector store with persistent storage.

Uses IndexFlatIP (Inner Product) with L2-normalized vectors
for cosine similarity search. Persists both the FAISS index
and document/chunk metadata to disk as JSON.

Features:
- Add documents with chunks and embeddings
- Cosine similarity search
- Document listing and deletion
- Thread-safe operations
- Automatic persistence to disk
"""

import faiss
import numpy as np
import json
import os
import threading
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FAISSStore:
    """FAISS-based vector store with metadata persistence"""

    def __init__(self, dimension: int = 384, index_path: str = "data/faiss"):
        """
        Initialize or load the FAISS store.

        Args:
            dimension: Embedding vector dimension (384 for all-MiniLM-L6-v2)
            index_path: Directory path for persisting index and metadata
        """
        self.dimension = dimension
        self.index_path = index_path
        self._lock = threading.Lock()

        # Data structures
        self.index: Optional[faiss.IndexFlatIP] = None
        self.chunk_metadata: List[Dict] = []
        self.documents: Dict[str, Dict] = {}

        os.makedirs(index_path, exist_ok=True)
        self._load()

        logger.info(
            f"FAISSStore ready: {self.total_vectors} vectors, "
            f"{len(self.documents)} documents"
        )

    @property
    def total_vectors(self) -> int:
        """Total number of vectors in the index"""
        return self.index.ntotal if self.index else 0

    def add_document(
        self,
        document_id: str,
        filename: str,
        chunks: List[Dict],
        embeddings: np.ndarray,
        page_count: int = 0,
        file_size_bytes: int = 0,
    ) -> int:
        """
        Add a document's chunks and embeddings to the store.

        Args:
            document_id: Unique document identifier
            filename: Original filename
            chunks: List of chunk dicts (must have 'text' key)
            embeddings: numpy array of shape (n_chunks, dimension)
            page_count: Number of pages in the PDF
            file_size_bytes: File size in bytes

        Returns:
            Number of vectors added
        """
        with self._lock:
            if embeddings.shape[0] != len(chunks):
                raise ValueError(
                    f"Mismatch: {embeddings.shape[0]} embeddings vs {len(chunks)} chunks"
                )

            embeddings = embeddings.astype(np.float32)

            # Add vectors to FAISS index
            self.index.add(embeddings)

            # Store chunk-level metadata
            for chunk in chunks:
                self.chunk_metadata.append({
                    "document_id": document_id,
                    "document_name": filename,
                    "chunk_index": chunk.get("chunk_index", 0),
                    "text": chunk["text"],
                    "page_number": chunk.get("page_number"),
                    "char_count": chunk.get("char_count", len(chunk["text"])),
                })

            # Store document-level metadata
            self.documents[document_id] = {
                "document_id": document_id,
                "filename": filename,
                "page_count": page_count,
                "chunk_count": len(chunks),
                "upload_time": datetime.utcnow().isoformat(),
                "file_size_bytes": file_size_bytes,
            }

            self._save()
            logger.info(f"Added {len(chunks)} vectors for: {filename}")
            return len(chunks)

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict]:
        """
        Search for the most similar chunks using cosine similarity.

        Args:
            query_embedding: Query vector of shape (1, dimension)
            top_k: Number of results to return

        Returns:
            List of chunk metadata dicts with similarity scores
        """
        with self._lock:
            if self.total_vectors == 0:
                return []

            query_embedding = query_embedding.astype(np.float32)
            if query_embedding.ndim == 1:
                query_embedding = query_embedding.reshape(1, -1)

            k = min(top_k, self.total_vectors)
            scores, indices = self.index.search(query_embedding, k)

            results = []
            for score, idx in zip(scores[0], indices[0]):
                if 0 <= idx < len(self.chunk_metadata):
                    result = self.chunk_metadata[idx].copy()
                    result["score"] = float(score)
                    results.append(result)

            return results

    def list_documents(self) -> List[Dict]:
        """List all uploaded documents with metadata"""
        return list(self.documents.values())

    def get_document(self, document_id: str) -> Optional[Dict]:
        """Get document metadata by ID"""
        return self.documents.get(document_id)

    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document and rebuild the FAISS index without it.

        FAISS doesn't support efficient single-vector deletion,
        so we reconstruct the index with remaining vectors.
        """
        with self._lock:
            if document_id not in self.documents:
                return False

            # Find indices of vectors to keep
            keep_indices = []
            new_metadata = []

            for i, meta in enumerate(self.chunk_metadata):
                if meta["document_id"] != document_id:
                    keep_indices.append(i)
                    new_metadata.append(meta)

            # Rebuild index with kept vectors
            if keep_indices:
                kept_vectors = np.array(
                    [self.index.reconstruct(i) for i in keep_indices],
                    dtype=np.float32,
                )
                self.index = faiss.IndexFlatIP(self.dimension)
                self.index.add(kept_vectors)
            else:
                self.index = faiss.IndexFlatIP(self.dimension)

            self.chunk_metadata = new_metadata
            del self.documents[document_id]

            self._save()
            logger.info(f"Deleted document: {document_id}")
            return True

    def _save(self):
        """Persist FAISS index and metadata to disk"""
        try:
            faiss.write_index(
                self.index,
                os.path.join(self.index_path, "index.faiss"),
            )

            with open(os.path.join(self.index_path, "chunk_metadata.json"), "w") as f:
                json.dump(self.chunk_metadata, f, indent=2)

            with open(os.path.join(self.index_path, "documents.json"), "w") as f:
                json.dump(self.documents, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save FAISS store: {e}")
            raise

    def _load(self):
        """Load FAISS index and metadata from disk, or create fresh"""
        index_file = os.path.join(self.index_path, "index.faiss")
        chunk_file = os.path.join(self.index_path, "chunk_metadata.json")
        docs_file = os.path.join(self.index_path, "documents.json")

        if os.path.exists(index_file) and os.path.exists(chunk_file):
            try:
                self.index = faiss.read_index(index_file)

                with open(chunk_file, "r") as f:
                    self.chunk_metadata = json.load(f)

                if os.path.exists(docs_file):
                    with open(docs_file, "r") as f:
                        self.documents = json.load(f)

                logger.info(f"Loaded existing FAISS store: {self.total_vectors} vectors")
                return
            except Exception as e:
                logger.warning(f"Failed to load FAISS store, creating new: {e}")

        # Create fresh index
        self.index = faiss.IndexFlatIP(self.dimension)
        self.chunk_metadata = []
        self.documents = {}
        logger.info("Created new FAISS index")
