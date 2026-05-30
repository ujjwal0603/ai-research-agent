"""
Qdrant-backed vector store implementation.

Uses ``qdrant_client.AsyncQdrantClient`` for all operations.  Three
collections are managed automatically:

- ``document_chunks``   — individual chunk embeddings
- ``document_centroids`` — per-document mean vectors
- ``concept_embeddings`` — knowledge-graph concept vectors
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Sequence

import numpy as np
from qdrant_client import AsyncQdrantClient, models as qmodels

from config.constants import (
    DEFAULT_EMBEDDING_DIMENSION,
    QDRANT_COLLECTION_CHUNKS,
    QDRANT_COLLECTION_CENTROIDS,
    QDRANT_COLLECTION_CONCEPTS,
)
from config.settings import get_settings
from vectorstore.base import VectorStore

logger = logging.getLogger(__name__)

# All managed collection names.
_COLLECTIONS: list[str] = [
    QDRANT_COLLECTION_CHUNKS,
    QDRANT_COLLECTION_CENTROIDS,
    QDRANT_COLLECTION_CONCEPTS,
]


class QdrantStore(VectorStore):
    """Production vector store backed by Qdrant.

    The client is created eagerly in ``__init__`` but collections are only
    guaranteed to exist after ``initialize()`` has been awaited.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._host = settings.QDRANT_HOST
        self._port = settings.QDRANT_PORT
        self._grpc_port = settings.QDRANT_GRPC_PORT
        self._api_key = settings.QDRANT_API_KEY or None
        self._dimension = settings.EMBEDDING_DIMENSION or DEFAULT_EMBEDDING_DIMENSION
        self._in_memory = getattr(settings, "QDRANT_IN_MEMORY", False)

        if self._in_memory:
            # In-memory mode — no Docker/server needed for local dev
            self._client = AsyncQdrantClient(location=":memory:")
            logger.info("QdrantStore created (in-memory mode, dim=%d).", self._dimension)
        else:
            self._client = AsyncQdrantClient(
                host=self._host,
                port=self._port,
                grpc_port=self._grpc_port,
                api_key=self._api_key,
                prefer_grpc=False,
            )
            logger.info(
                "QdrantStore created (host=%s, port=%d, dim=%d).",
                self._host, self._port, self._dimension,
            )

    # ── Lifecycle ────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Ensure all required collections exist.

        Existing collections are left untouched; missing ones are created
        with cosine distance and the configured embedding dimension.
        """
        existing: set[str] = set()
        try:
            collections_response = await self._client.get_collections()
            existing = {c.name for c in collections_response.collections}
        except Exception:
            logger.exception("Failed to list existing Qdrant collections.")
            raise

        for name in _COLLECTIONS:
            if name in existing:
                logger.info("Collection '%s' already exists — skipping.", name)
                continue

            logger.info("Creating Qdrant collection '%s' …", name)
            await self._client.create_collection(
                collection_name=name,
                vectors_config=qmodels.VectorParams(
                    size=self._dimension,
                    distance=qmodels.Distance.COSINE,
                ),
            )
            logger.info("Collection '%s' created.", name)

        logger.info("QdrantStore initialised (%d collections).", len(_COLLECTIONS))

    # ── CRUD ─────────────────────────────────────────────────────────────

    async def add_vectors(
        self,
        vectors: np.ndarray,
        payloads: list[dict],
        collection: str,
    ) -> list[str]:
        """Batch-upsert vectors with metadata into *collection*.

        Each point receives a new UUID as its ID.
        """
        if vectors.ndim != 2 or vectors.shape[0] != len(payloads):
            raise ValueError(
                f"Shape mismatch: vectors {vectors.shape} vs "
                f"{len(payloads)} payloads."
            )

        point_ids: list[str] = []
        points: list[qmodels.PointStruct] = []

        for vec, payload in zip(vectors, payloads):
            pid = str(uuid.uuid4())
            point_ids.append(pid)
            points.append(
                qmodels.PointStruct(
                    id=pid,
                    vector=vec.tolist(),
                    payload=payload,
                )
            )

        # Qdrant supports large batches; chunk at 256 to be safe with memory.
        batch_size = 256
        for start in range(0, len(points), batch_size):
            batch = points[start : start + batch_size]
            await self._client.upsert(
                collection_name=collection,
                points=batch,
            )

        logger.info(
            "Upserted %d vectors into '%s'.", len(points), collection,
        )
        return point_ids

    async def search(
        self,
        query_vector: np.ndarray,
        collection: str,
        top_k: int,
        filters: dict | None = None,
    ) -> list[dict]:
        """Find the top-k nearest neighbours in *collection*."""
        query_filter = self._build_filter(filters) if filters else None

        results = await self._client.query_points(
            collection_name=collection,
            query=query_vector.tolist(),
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )

        output: list[dict] = []
        for point in results.points:
            output.append(
                {
                    "id": str(point.id),
                    "score": point.score,
                    "payload": point.payload or {},
                }
            )
        return output

    async def delete_by_filter(
        self,
        collection: str,
        filter_key: str,
        filter_value: str,
    ) -> int:
        """Delete all points where ``payload[filter_key] == filter_value``."""
        # Count before delete so we can report how many were removed.
        pre_count = await self._count_with_filter(collection, filter_key, filter_value)

        await self._client.delete(
            collection_name=collection,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key=filter_key,
                            match=qmodels.MatchValue(value=filter_value),
                        )
                    ]
                )
            ),
        )
        logger.info(
            "Deleted ~%d points from '%s' where %s='%s'.",
            pre_count, collection, filter_key, filter_value,
        )
        return pre_count

    # ── Info / Health ────────────────────────────────────────────────────

    async def get_collection_info(self, collection: str) -> dict:
        """Return point count, vector size, and status."""
        try:
            info = await self._client.get_collection(collection_name=collection)
            return {
                "name": collection,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "status": str(info.status),
            }
        except Exception:
            logger.exception("Failed to get info for collection '%s'.", collection)
            return {"name": collection, "error": "unavailable"}

    async def health_check(self) -> bool:
        """Verify Qdrant is reachable."""
        try:
            await self._client.get_collections()
            return True
        except Exception:
            logger.warning("Qdrant health-check failed.", exc_info=True)
            return False

    # ── Extra helpers ────────────────────────────────────────────────────

    async def list_documents(self, collection: str) -> list[str]:
        """Scroll through *collection* and return unique ``document_id`` values."""
        document_ids: set[str] = set()
        offset: str | int | None = None

        while True:
            records, next_offset = await self._client.scroll(
                collection_name=collection,
                scroll_filter=None,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for point in records:
                payload = point.payload or {}
                doc_id = payload.get("document_id")
                if doc_id is not None:
                    document_ids.add(str(doc_id))

            if next_offset is None:
                break
            offset = next_offset

        logger.debug(
            "Found %d unique document_id(s) in '%s'.",
            len(document_ids), collection,
        )
        return sorted(document_ids)

    # ── Internal ─────────────────────────────────────────────────────────

    @staticmethod
    def _build_filter(filters: dict) -> qmodels.Filter:
        """Translate a flat ``{key: value}`` dict into a Qdrant ``Filter``."""
        conditions: list[qmodels.FieldCondition] = []
        for key, value in filters.items():
            conditions.append(
                qmodels.FieldCondition(
                    key=key,
                    match=qmodels.MatchValue(value=value),
                )
            )
        return qmodels.Filter(must=conditions)

    async def _count_with_filter(
        self, collection: str, key: str, value: str
    ) -> int:
        """Count points matching a single filter condition."""
        try:
            result = await self._client.count(
                collection_name=collection,
                count_filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key=key,
                            match=qmodels.MatchValue(value=value),
                        )
                    ]
                ),
                exact=False,
            )
            return result.count
        except Exception:
            return 0
