"""
Embedding model provider backed by ``sentence-transformers``.

Uses a highly compressed model and strictly limits PyTorch memory footprint 
to fit within Render's 512MB free tier limit without OOM kills.
"""

from __future__ import annotations

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import TYPE_CHECKING

import numpy as np

from models_layer.base import ModelProvider

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Use a single thread to strictly limit memory overhead
_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="embed")

# Force PyTorch to use minimal threads to save memory
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"


class EmbeddingModel(ModelProvider):
    """Thin async wrapper around a lightweight SentenceTransformer."""

    def __init__(self, model_name_or_path: str = "paraphrase-MiniLM-L3-v2") -> None:
        # Use an ultra-lightweight 61MB model to prevent 512MB RAM OOM kills
        self._model_name = "paraphrase-MiniLM-L3-v2"
        self._model: SentenceTransformer | None = None
        self._dimension: int | None = None
        logger.info("EmbeddingModel created (model=%s, ultra-lightweight)", self._model_name)

    # ── ModelProvider interface ───────────────────────────────────────────

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    async def load(self) -> None:
        """Load ``SentenceTransformer`` weights into memory."""
        if self._model is not None:
            return

        loop = asyncio.get_running_loop()
        logger.info("Loading tiny SentenceTransformer '%s' …", self._model_name)
        self._model = await loop.run_in_executor(
            _EXECUTOR, self._load_model_sync
        )
        self._dimension = self._model.get_sentence_embedding_dimension()  # type: ignore[union-attr]
        logger.info("EmbeddingModel loaded (dimension=%d).", self._dimension)

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
        if self._dimension is None:
            raise RuntimeError("EmbeddingModel not loaded yet.")
        return self._dimension

    async def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed a batch of texts and return L2-normalised vectors."""
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        await self._ensure_loaded()

        # Batch in small chunks of 16 to prevent memory spikes during inference
        loop = asyncio.get_running_loop()
        embeddings: np.ndarray = await loop.run_in_executor(
            _EXECUTOR,
            partial(
                self._model.encode,  # type: ignore[union-attr]
                texts,
                batch_size=16,
                normalize_embeddings=True,
                show_progress_bar=False,
            ),
        )
        logger.debug("Embedded %d text(s).", len(texts))
        return embeddings.astype(np.float32)

    async def embed_query(self, query: str) -> np.ndarray:
        vectors = await self.embed_texts([query])
        return vectors[0]

    # ── Internals ────────────────────────────────────────────────────────

    def _load_model_sync(self) -> SentenceTransformer:
        """Synchronous helper — called inside the executor."""
        import torch
        # Strictly limit PyTorch memory allocation
        torch.set_num_threads(1)
        
        from sentence_transformers import SentenceTransformer
        # Load the model on CPU
        return SentenceTransformer(self._model_name, device='cpu')

    async def _ensure_loaded(self) -> None:
        if not self.is_loaded:
            await self.load()
