"""
Embedding model provider backed by Google Gemini API.

This avoids heavy local model loading which causes Out of Memory (OOM) 
kills on Render's 512MB free tier.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import numpy as np
import google.generativeai as genai
from config.settings import get_settings

from models_layer.base import ModelProvider

logger = logging.getLogger(__name__)


class EmbeddingModel(ModelProvider):
    """Async wrapper around Google Gemini Embeddings API."""

    def __init__(self, model_name_or_path: str = "models/embedding-001") -> None:
        self._model_name = "models/embedding-001"
        self._dimension: int = 768
        self._loaded: bool = False
        logger.info("EmbeddingModel created (Gemini API, no local RAM used)")

    # ── ModelProvider interface ───────────────────────────────────────────

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    async def load(self) -> None:
        """Initialize the Gemini client (idempotent)."""
        if self._loaded:
            return

        settings = get_settings()
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY is missing! Embeddings will fail.")
            
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._loaded = True
        logger.info("EmbeddingModel loaded (Gemini API configured).")

    async def unload(self) -> None:
        """Release."""
        self._loaded = False

    async def health_check(self) -> bool:
        """Verify the API can produce an embedding."""
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
        return self._dimension

    async def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed a batch of texts and return L2-normalised vectors."""
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        await self._ensure_loaded()
        
        try:
            # The API allows batching.
            result = genai.embed_content(
                model=self._model_name,
                content=texts,
                task_type="retrieval_document"
            )
            embeddings = result['embedding']
            
            arr = np.array(embeddings, dtype=np.float32)
            # L2 Normalize
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            norms[norms == 0] = 1
            arr = arr / norms
            logger.debug("Embedded %d text(s) via Gemini API.", len(texts))
            return arr
            
        except Exception as exc:
            logger.error("Gemini API Error: %s", exc)
            raise

    async def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query string."""
        await self._ensure_loaded()
        try:
            result = genai.embed_content(
                model=self._model_name,
                content=query,
                task_type="retrieval_query"
            )
            arr = np.array(result['embedding'], dtype=np.float32)
            norm = np.linalg.norm(arr)
            if norm > 0:
                arr = arr / norm
            return arr
        except Exception as exc:
            logger.error("Gemini API Error: %s", exc)
            raise

    # ── Internals ────────────────────────────────────────────────────────

    async def _ensure_loaded(self) -> None:
        if not self.is_loaded:
            await self.load()
