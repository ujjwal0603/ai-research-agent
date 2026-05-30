"""
Embedding model provider backed by ``sentence-transformers``.

The heavy ``SentenceTransformer`` instance is lazily loaded on first use
or explicit ``load()`` call.  All inference runs in a thread-pool executor
so the event loop is never blocked.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import TYPE_CHECKING

import numpy as np

from models_layer.base import ModelProvider

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Shared thread pool for all CPU-bound model work inside this module.
_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="embed")


class EmbeddingModel(ModelProvider):
    """Thin async wrapper around ``SentenceTransformer``.

    Parameters
    ----------
    model_name_or_path:
        HuggingFace model ID or local path.  Defaults to ``all-MiniLM-L6-v2``.
    """

    def __init__(self, model_name_or_path: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name_or_path
        self._model: SentenceTransformer | None = None
        self._dimension: int | None = None
        logger.info("EmbeddingModel created (model=%s, lazy-load)", self._model_name)

    # ── ModelProvider interface ───────────────────────────────────────────

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    async def load(self) -> None:
        """Load ``SentenceTransformer`` weights into memory (idempotent)."""
        if self._model is not None:
            logger.debug("EmbeddingModel already loaded — skipping.")
            return

        loop = asyncio.get_running_loop()
        logger.info("Loading SentenceTransformer model '%s' …", self._model_name)
        self._model = await loop.run_in_executor(
            _EXECUTOR, self._load_model_sync
        )
        self._dimension = self._model.get_sentence_embedding_dimension()  # type: ignore[union-attr]
        logger.info(
            "EmbeddingModel loaded (dimension=%d).", self._dimension
        )

    async def unload(self) -> None:
        """Release the model from memory."""
        if self._model is None:
            return
        logger.info("Unloading EmbeddingModel '%s'.", self._model_name)
        self._model = None
        self._dimension = None

    async def health_check(self) -> bool:
        """Verify the model can produce an embedding."""
        if not self.is_loaded:
            return False
        try:
            vec = await self.embed_query("health")
            return vec.shape[0] == self.dimension
        except Exception:
            logger.exception("EmbeddingModel health-check failed.")
            return False

    # ── Public API ───────────────────────────────────────────────────────

    @property
    def dimension(self) -> int:
        """Dimensionality of the embedding vectors.

        Raises
        ------
        RuntimeError
            If accessed before the model is loaded.
        """
        if self._dimension is None:
            raise RuntimeError(
                "EmbeddingModel not loaded yet — call `await load()` first."
            )
        return self._dimension

    async def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed a batch of texts and return L2-normalised vectors.

        Parameters
        ----------
        texts:
            List of strings to embed.

        Returns
        -------
        np.ndarray
            Shape ``(len(texts), dimension)`` with unit-norm rows.
        """
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        await self._ensure_loaded()

        loop = asyncio.get_running_loop()
        embeddings: np.ndarray = await loop.run_in_executor(
            _EXECUTOR,
            partial(
                self._model.encode,  # type: ignore[union-attr]
                texts,
                normalize_embeddings=True,
                show_progress_bar=False,
            ),
        )
        logger.debug("Embedded %d text(s).", len(texts))
        return embeddings.astype(np.float32)

    async def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query string.

        Returns
        -------
        np.ndarray
            1-D vector of shape ``(dimension,)`` with unit norm.
        """
        vectors = await self.embed_texts([query])
        return vectors[0]

    # ── Internals ────────────────────────────────────────────────────────

    def _load_model_sync(self) -> SentenceTransformer:
        """Synchronous helper — called inside the executor."""
        from sentence_transformers import SentenceTransformer  # heavy import

        return SentenceTransformer(self._model_name)

    async def _ensure_loaded(self) -> None:
        """Lazily load the model on first inference call."""
        if not self.is_loaded:
            await self.load()
