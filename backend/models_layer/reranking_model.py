"""
Reranking model provider.

This is a lightweight mock that bypasses the memory-heavy CrossEncoder 
to prevent Out of Memory (OOM) kills on Render's free tier. 
It just returns the original vector search scores.
"""

from __future__ import annotations

import logging

from models_layer.base import ModelProvider

logger = logging.getLogger(__name__)


class RerankingModel(ModelProvider):
    """Zero-RAM passthrough reranker."""

    def __init__(
        self, model_name_or_path: str = "passthrough-reranker"
    ) -> None:
        self._model_name = "passthrough-reranker"
        self._loaded: bool = False
        logger.info("RerankingModel created (passthrough, no RAM used)")

    # ── ModelProvider interface ───────────────────────────────────────────

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    async def load(self) -> None:
        self._loaded = True
        logger.info("RerankingModel loaded (passthrough).")

    async def unload(self) -> None:
        self._loaded = False

    async def health_check(self) -> bool:
        return True

    # ── Public API ───────────────────────────────────────────────────────

    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int = 5,
    ) -> list[tuple[int, float]]:
        """Simply return the original indices as-is without cross-encoding."""
        if not documents:
            return []

        await self._ensure_loaded()

        # Just return them in the original order with dummy scores
        results = [(i, 1.0 - (i * 0.01)) for i in range(len(documents))]
        return results[:top_k]

    # ── Internals ────────────────────────────────────────────────────────

    async def _ensure_loaded(self) -> None:
        if not self.is_loaded:
            await self.load()
