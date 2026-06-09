"""
Search strategy executor — encapsulates dense, sparse, and hybrid retrieval.

Each strategy method follows the same contract: accept a query and retrieval
parameters, return a list of scored chunk dicts.
"""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

import numpy as np

from config.constants import DEFAULT_TOP_K, QDRANT_COLLECTION_CHUNKS

if TYPE_CHECKING:
    from models_layer.embedding_model import EmbeddingModel
    from models_layer.reranking_model import RerankingModel

logger = logging.getLogger(__name__)


class SearchStrategyExecutor:
    """Unified executor for dense, sparse, and hybrid search strategies.

    Parameters
    ----------
    qdrant_store:
        Qdrant vector store adapter (must expose ``search`` / ``search_with_filter``).
    hybrid_engine:
        Hybrid search engine that combines dense + sparse results.
    embedding_model:
        Model for query embedding.
    reranking_model:
        Cross-encoder model for result reranking.
    """

    def __init__(
        self,
        qdrant_store: Any,
        hybrid_engine: Any,
        embedding_model: EmbeddingModel,
        reranking_model: RerankingModel | None = None,
    ) -> None:
        self._qdrant = qdrant_store
        self._hybrid = hybrid_engine
        self._embedding_model = embedding_model
        self._reranking_model = reranking_model

    # ── Dense Search ────────────────────────────────────────────────────

    async def execute_dense(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        filters: dict[str, Any] | None = None,
    ) -> list[dict]:
        """Embed *query* and perform a nearest-neighbour search in Qdrant.

        Parameters
        ----------
        query:
            Natural language query.
        top_k:
            Maximum number of results.
        filters:
            Optional Qdrant payload filters (e.g. ``{"document_id": "abc"}``).

        Returns
        -------
        list[dict]
            Scored chunk dicts from the vector store.
        """
        logger.info("Dense search: query='%s…' top_k=%d", query[:60], top_k)

        query_embedding = await self._embedding_model.embed_query(query)

        if filters:
            results = await self._search_with_filter(
                query_embedding, top_k, filters
            )
        else:
            results = await self._search(query_embedding, top_k)

        logger.info("Dense search returned %d results.", len(results))
        return results

    # ── Sparse Search (BM25-style) ──────────────────────────────────────

    async def execute_sparse(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        document_id: str | None = None,
    ) -> list[dict]:
        """Keyword-based (BM25) search using the hybrid engine.

        Parameters
        ----------
        query:
            Natural language query.
        top_k:
            Maximum number of results.
        document_id:
            Optional scope to a single document.

        Returns
        -------
        list[dict]
            Scored chunk dicts.
        """
        logger.info("Sparse search: query='%s…' top_k=%d", query[:60], top_k)

        if self._hybrid is None:
            logger.warning(
                "Hybrid engine not available — falling back to dense search."
            )
            return await self.execute_dense(query, top_k)

        try:
            results = await self._hybrid.sparse_search(
                query=query, top_k=top_k, document_id=document_id
            )
        except AttributeError:
            # Hybrid engine might not have sparse_search yet.
            logger.warning(
                "Hybrid engine missing sparse_search — falling back to dense."
            )
            return await self.execute_dense(query, top_k)

        logger.info("Sparse search returned %d results.", len(results))
        return results

    # ── Hybrid Search ───────────────────────────────────────────────────

    async def execute_hybrid(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        filters: dict[str, Any] | None = None,
        alpha: float = 0.5,
    ) -> list[dict]:
        """Combined dense + sparse search with score fusion."""
        logger.info(
            "Hybrid search: query='%s…' top_k=%d alpha=%.2f",
            query[:60], top_k, alpha,
        )

        if self._hybrid is None:
            logger.warning(
                "Hybrid engine not available — falling back to dense search."
            )
            return await self.execute_dense(query, top_k, filters)

        try:
            results = await self._hybrid.hybrid_search(
                query=query,
                top_k=top_k,
                alpha=alpha,
                filters=filters,
            )
        except Exception as exc:
            logger.warning(
                "Hybrid search failed (%s) — falling back to dense.", exc
            )
            return await self.execute_dense(query, top_k, filters)

        logger.info("Hybrid search returned %d results.", len(results))
        return results

    # ── Reranking ───────────────────────────────────────────────────────

    async def rerank_results(
        self,
        query: str,
        results: list[dict],
        top_k: int = DEFAULT_TOP_K,
    ) -> list[dict]:
        """Rerank *results* using the cross-encoder model."""
        if self._reranking_model is None:
            logger.warning("No reranking model — returning results as-is.")
            return results[:top_k]

        if not results:
            return []

        from agents.retrieval.reranker import Reranker

        reranker = Reranker(self._reranking_model)
        return await reranker.rerank(query, results, top_k)

    # ── Internal Qdrant helpers ─────────────────────────────────────────

    async def _search(
        self, query_embedding: np.ndarray, top_k: int
    ) -> list[dict]:
        """Perform a plain vector search (no filters)."""
        try:
            return await self._qdrant.search(
                query_vector=query_embedding,
                collection=QDRANT_COLLECTION_CHUNKS,
                top_k=top_k,
            )
        except Exception as exc:
            logger.error("Qdrant search failed: %s", exc)
            return []

    async def _search_with_filter(
        self,
        query_embedding: np.ndarray,
        top_k: int,
        filters: dict[str, Any],
    ) -> list[dict]:
        """Perform a vector search with payload filters."""
        try:
            return await self._qdrant.search(
                query_vector=query_embedding,
                collection=QDRANT_COLLECTION_CHUNKS,
                top_k=top_k,
                filters=filters,
            )
        except Exception as exc:
            logger.error("Qdrant filtered search failed: %s", exc)
            return []
