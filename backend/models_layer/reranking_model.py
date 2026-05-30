"""
Reranking model provider backed by a ``CrossEncoder`` from *sentence-transformers*.

Lazy-loaded on first call.  Inference is offloaded to a thread-pool executor
so the async event loop stays responsive.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import numpy as np

from models_layer.base import ModelProvider

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="rerank")


class RerankingModel(ModelProvider):
    """Async wrapper around a cross-encoder reranking model.

    Parameters
    ----------
    model_name_or_path:
        HuggingFace model ID.  Defaults to ``cross-encoder/ms-marco-MiniLM-L-6-v2``.
    """

    def __init__(
        self, model_name_or_path: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    ) -> None:
        self._model_name = model_name_or_path
        self._model: CrossEncoder | None = None
        logger.info("RerankingModel created (model=%s, lazy-load)", self._model_name)

    # ── ModelProvider interface ───────────────────────────────────────────

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    async def load(self) -> None:
        """Load the cross-encoder into memory (idempotent)."""
        if self._model is not None:
            logger.debug("RerankingModel already loaded — skipping.")
            return

        loop = asyncio.get_running_loop()
        logger.info("Loading CrossEncoder '%s' …", self._model_name)
        self._model = await loop.run_in_executor(_EXECUTOR, self._load_sync)
        logger.info("RerankingModel loaded.")

    async def unload(self) -> None:
        if self._model is None:
            return
        logger.info("Unloading RerankingModel '%s'.", self._model_name)
        self._model = None

    async def health_check(self) -> bool:
        if not self.is_loaded:
            return False
        try:
            results = await self.rerank("test", ["test document"], top_k=1)
            return len(results) == 1
        except Exception:
            logger.exception("RerankingModel health-check failed.")
            return False

    # ── Public API ───────────────────────────────────────────────────────

    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int = 5,
    ) -> list[tuple[int, float]]:
        """Score ``(query, document)`` pairs and return the top-k indices.

        Parameters
        ----------
        query:
            The search query.
        documents:
            Candidate documents to rerank.
        top_k:
            Maximum number of results to return.

        Returns
        -------
        list[tuple[int, float]]
            ``(original_index, relevance_score)`` sorted descending by score.
        """
        if not documents:
            return []

        await self._ensure_loaded()

        pairs = [[query, doc] for doc in documents]
        loop = asyncio.get_running_loop()

        scores: np.ndarray = await loop.run_in_executor(
            _EXECUTOR,
            self._model.predict,  # type: ignore[union-attr]
            pairs,
        )

        scored_indices = sorted(
            enumerate(scores.tolist()),
            key=lambda x: x[1],
            reverse=True,
        )
        top_results = scored_indices[: top_k]

        logger.debug(
            "Reranked %d documents → returning top %d.",
            len(documents),
            len(top_results),
        )
        return [(idx, float(score)) for idx, score in top_results]

    # ── Internals ────────────────────────────────────────────────────────

    def _load_sync(self) -> CrossEncoder:
        from sentence_transformers import CrossEncoder

        return CrossEncoder(self._model_name)

    async def _ensure_loaded(self) -> None:
        if not self.is_loaded:
            await self.load()
