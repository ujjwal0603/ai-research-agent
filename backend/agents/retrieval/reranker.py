"""
Reranker helper — wraps the ``RerankingModel`` for chunk-level reranking.

Extracts text from chunk dicts, delegates scoring to the cross-encoder model,
and returns the chunks sorted by relevance.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models_layer.reranking_model import RerankingModel

logger = logging.getLogger(__name__)


class Reranker:
    """Rerank a list of chunk dicts using a cross-encoder model.

    Parameters
    ----------
    reranking_model:
        A loaded ``RerankingModel`` instance that provides ``rerank(query, docs, top_k)``.
    """

    def __init__(self, reranking_model: RerankingModel) -> None:
        self._model = reranking_model

    async def rerank(
        self,
        query: str,
        chunks: list[dict],
        top_k: int = 5,
    ) -> list[dict]:
        """Rerank *chunks* by relevance to *query* and return the top-k.

        Parameters
        ----------
        query:
            The user's search query.
        chunks:
            List of chunk dicts — each must contain a ``"text"`` key.
        top_k:
            Maximum number of chunks to return.

        Returns
        -------
        list[dict]
            Subset of *chunks* sorted descending by cross-encoder score.
            Each dict is augmented with a ``"rerank_score"`` key.
        """
        if not chunks:
            logger.debug("Reranker received empty chunk list — returning [].")
            return []

        # Extract text for cross-encoder scoring.
        documents = [chunk.get("text", "") for chunk in chunks]

        if not any(documents):
            logger.warning("All chunks have empty text — skipping reranking.")
            return chunks[:top_k]

        try:
            scored: list[tuple[int, float]] = await self._model.rerank(
                query, documents, top_k=top_k
            )
        except Exception as exc:
            logger.error("Reranking failed: %s — returning original order.", exc)
            return chunks[:top_k]

        # Rebuild chunk list in reranked order.
        reranked: list[dict] = []
        for original_idx, score in scored:
            if 0 <= original_idx < len(chunks):
                chunk = chunks[original_idx].copy()
                chunk["rerank_score"] = round(float(score), 6)
                reranked.append(chunk)

        logger.info(
            "Reranked %d chunks → returning top %d.",
            len(chunks),
            len(reranked),
        )
        return reranked
