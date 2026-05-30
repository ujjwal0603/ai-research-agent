"""
Abstract base class for all vector store implementations.

Concrete stores (Qdrant, FAISS, Pinecone, …) must implement this interface
so the rest of the platform stays store-agnostic.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import numpy as np

logger = logging.getLogger(__name__)


class VectorStore(ABC):
    """Minimal contract every vector store must satisfy."""

    # ── Lifecycle ────────────────────────────────────────────────────────

    @abstractmethod
    async def initialize(self) -> None:
        """Set up the connection and create collections / indices if needed."""
        ...

    # ── CRUD ─────────────────────────────────────────────────────────────

    @abstractmethod
    async def add_vectors(
        self,
        vectors: np.ndarray,
        payloads: list[dict],
        collection: str,
    ) -> list[str]:
        """Insert or update vectors with metadata payloads.

        Parameters
        ----------
        vectors:
            Numpy array of shape ``(n, dim)``.
        payloads:
            One metadata dict per vector.
        collection:
            Target collection / index name.

        Returns
        -------
        list[str]
            The point / vector IDs that were upserted.
        """
        ...

    @abstractmethod
    async def search(
        self,
        query_vector: np.ndarray,
        collection: str,
        top_k: int,
        filters: dict | None = None,
    ) -> list[dict]:
        """Search for the nearest neighbours of *query_vector*.

        Parameters
        ----------
        query_vector:
            1-D array of shape ``(dim,)``.
        collection:
            Collection to query.
        top_k:
            Maximum results to return.
        filters:
            Optional key-value filters applied server-side.

        Returns
        -------
        list[dict]
            Each dict contains at least ``id``, ``score``, and ``payload``.
        """
        ...

    @abstractmethod
    async def delete_by_filter(
        self,
        collection: str,
        filter_key: str,
        filter_value: str,
    ) -> int:
        """Delete all points matching the filter.

        Returns
        -------
        int
            Number of points deleted (or an estimate if the store doesn't
            report exact counts).
        """
        ...

    @abstractmethod
    async def get_collection_info(self, collection: str) -> dict:
        """Return metadata about the collection (point count, status, …)."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return ``True`` when the vector store is reachable and operational."""
        ...
