"""
Hybrid search engine combining dense (Qdrant) and sparse (BM25) retrieval.

Results from both sources are fused using **Reciprocal Rank Fusion (RRF)**.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict

import numpy as np
from rank_bm25 import BM25Okapi  # type: ignore[import-untyped]

from models_layer.embedding_model import EmbeddingModel
from vectorstore.qdrant_store import QdrantStore

logger = logging.getLogger(__name__)

# RRF constant (standard default from the original RRF paper).
_RRF_K = 60


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokeniser for BM25."""
    return re.findall(r"\w+", text.lower())


class HybridSearchEngine:
    """Combines dense vector search with sparse BM25 via RRF.

    Parameters
    ----------
    qdrant_store:
        Initialised :class:`QdrantStore` instance.
    embedding_model:
        Loaded :class:`EmbeddingModel` for query embedding.
    """

    def __init__(
        self,
        qdrant_store: QdrantStore,
        embedding_model: EmbeddingModel,
    ) -> None:
        self._qdrant = qdrant_store
        self._embedder = embedding_model

        # BM25 indices keyed by document_id.
        self._bm25_indices: dict[str, BM25Okapi] = {}
        # Raw chunk data keyed by document_id for BM25 result look-ups.
        self._chunk_store: dict[str, list[dict]] = {}

        logger.info("HybridSearchEngine created.")

    # ── BM25 Index Management ────────────────────────────────────────────

    async def build_bm25_index(
        self,
        document_id: str,
        chunks: list[dict],
    ) -> None:
        """Build (or rebuild) the in-memory BM25 index for a document.

        Parameters
        ----------
        document_id:
            Unique document identifier.
        chunks:
            List of chunk dicts — each **must** contain a ``"text"`` key.
        """
        if not chunks:
            logger.warning(
                "No chunks provided for document '%s' — BM25 index skipped.",
                document_id,
            )
            return

        tokenised = [_tokenize(chunk.get("text", "")) for chunk in chunks]
        self._bm25_indices[document_id] = BM25Okapi(tokenised)
        self._chunk_store[document_id] = chunks

        logger.info(
            "BM25 index built for document '%s' (%d chunks).",
            document_id, len(chunks),
        )

    def has_bm25_index(self, document_id: str) -> bool:
        """Check whether a BM25 index exists for the given document."""
        return document_id in self._bm25_indices

    # ── Search Methods ───────────────────────────────────────────────────

    async def dense_search(
        self,
        query: str,
        top_k: int,
        filters: dict | None = None,
        collection: str = "document_chunks",
    ) -> list[dict]:
        """Embed *query* and search Qdrant.

        Returns a list of dicts with keys ``id``, ``score``, ``payload``.
        """
        if not query.strip():
            return []

        query_vector = await self._embedder.embed_query(query)
        results = await self._qdrant.search(
            query_vector=query_vector,
            collection=collection,
            top_k=top_k,
            filters=filters,
        )
        logger.debug("Dense search returned %d results.", len(results))
        return results

    async def sparse_search(
        self,
        query: str,
        document_id: str,
        top_k: int,
    ) -> list[dict]:
        """BM25 keyword search within a single document.

        Returns a list of dicts with keys ``chunk_index``, ``score``,
        ``text``, and ``payload`` (the original chunk dict).
        """
        if not query.strip():
            return []

        bm25 = self._bm25_indices.get(document_id)
        chunks = self._chunk_store.get(document_id, [])

        if bm25 is None or not chunks:
            logger.warning(
                "No BM25 index for document '%s' — returning empty.", document_id,
            )
            return []

        tokens = _tokenize(query)
        scores: np.ndarray = bm25.get_scores(tokens)

        # Rank and take top-k non-zero results.
        ranked_indices = np.argsort(scores)[::-1][:top_k]
        results: list[dict] = []
        for idx in ranked_indices:
            score = float(scores[idx])
            if score <= 0:
                break
            chunk = chunks[idx]
            results.append(
                {
                    "chunk_index": int(idx),
                    "score": score,
                    "text": chunk.get("text", ""),
                    "payload": chunk,
                }
            )

        logger.debug(
            "BM25 search (doc=%s) returned %d results.",
            document_id, len(results),
        )
        return results

    async def hybrid_search(
        self,
        query: str,
        top_k: int,
        filters: dict | None = None,
        alpha: float = 0.7,
        collection: str = "document_chunks",
    ) -> list[dict]:
        """Reciprocal Rank Fusion of dense + sparse results.

        Parameters
        ----------
        query:
            User search query.
        top_k:
            Final number of results to return.
        filters:
            Optional Qdrant payload filters.  If a ``document_id`` filter
            is present *and* a BM25 index exists for that document, sparse
            search is included.  Otherwise only dense results are returned.
        alpha:
            Weight factor (unused in pure RRF, retained for future weighted
            blending).  Default ``0.7`` favours dense retrieval.
        collection:
            Qdrant collection to query.

        Returns
        -------
        list[dict]
            Fused results sorted by RRF score descending.
        """
        # --- Dense arm ---
        fetch_k = top_k * 3  # over-fetch for better fusion
        dense_results = await self.dense_search(
            query, top_k=fetch_k, filters=filters, collection=collection,
        )

        # --- Sparse arm (only when a document_id filter is available) ---
        sparse_results: list[dict] = []
        document_id = (filters or {}).get("document_id")
        if document_id and self.has_bm25_index(document_id):
            sparse_results = await self.sparse_search(
                query, document_id=document_id, top_k=fetch_k,
            )

        # If we have no sparse results, just return dense.
        if not sparse_results:
            return dense_results[:top_k]

        # --- RRF Fusion ---
        return self._rrf_fuse(dense_results, sparse_results, top_k)

    # ── Internals ────────────────────────────────────────────────────────

    @staticmethod
    def _rrf_fuse(
        dense: list[dict],
        sparse: list[dict],
        top_k: int,
    ) -> list[dict]:
        """Merge two ranked lists using Reciprocal Rank Fusion.

        Score formula::

            rrf_score(d) = Σ  1 / (k + rank_i(d))

        where *k* = 60 and the sum is over every list that contains *d*.
        """
        # Map each result to a unique key so we can merge.
        rrf_scores: dict[str, float] = defaultdict(float)
        result_map: dict[str, dict] = {}

        # Dense results keyed by Qdrant point ID.
        for rank, res in enumerate(dense, start=1):
            key = res["id"]
            rrf_scores[key] += 1.0 / (_RRF_K + rank)
            result_map[key] = res

        # Sparse results keyed by (document_id, chunk_index).
        for rank, res in enumerate(sparse, start=1):
            payload = res.get("payload", {})
            # Try to match with the dense key via chunk_id stored in payload.
            key = payload.get("chunk_id") or f"bm25_{res.get('chunk_index', rank)}"
            rrf_scores[key] += 1.0 / (_RRF_K + rank)
            if key not in result_map:
                result_map[key] = {
                    "id": key,
                    "score": 0.0,
                    "payload": payload,
                    "text": res.get("text", ""),
                }

        # Sort by fused score.
        sorted_keys = sorted(rrf_scores, key=rrf_scores.get, reverse=True)  # type: ignore[arg-type]

        fused: list[dict] = []
        for key in sorted_keys[:top_k]:
            entry = result_map[key].copy()
            entry["rrf_score"] = rrf_scores[key]
            fused.append(entry)

        logger.debug(
            "RRF fusion: %d dense + %d sparse → %d results.",
            len(dense), len(sparse), len(fused),
        )
        return fused
