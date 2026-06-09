"""
Embedding model provider using the Gemini REST API via httpx.

Completely bypasses the google-generativeai SDK's gRPC layer
(which returns 404 errors on certain platforms) and instead
calls Google's REST endpoint directly over plain HTTPS.

Uses zero local RAM — no PyTorch, no sentence-transformers.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
import numpy as np

from config.settings import get_settings
from models_layer.base import ModelProvider

logger = logging.getLogger(__name__)

# Gemini REST API base
_GEMINI_API_BASE = "https://generativelanguage.googleapis.com"


class EmbeddingModel(ModelProvider):
    """Async embedding model backed by Gemini REST API (no gRPC)."""

    def __init__(self, model_name_or_path: str = "text-embedding-004") -> None:
        settings = get_settings()
        self._api_key = settings.GEMINI_API_KEY
        self._model_name = "text-embedding-004"
        self._dimension: int = 768
        self._loaded: bool = False
        self._client: httpx.AsyncClient | None = None
        logger.info("EmbeddingModel created (Gemini REST API, zero local RAM)")

    # ── ModelProvider interface ───────────────────────────────────────────

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    async def load(self) -> None:
        if self._loaded:
            return
        # Create a persistent HTTP client for connection pooling
        self._client = httpx.AsyncClient(timeout=120.0)
        self._loaded = True
        logger.info("EmbeddingModel loaded (Gemini REST, dim=%d).", self._dimension)

    async def unload(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        self._loaded = False

    async def health_check(self) -> bool:
        try:
            vec = await self.embed_query("health check")
            return vec.shape[0] == self._dimension
        except Exception:
            logger.exception("EmbeddingModel health-check failed.")
            return False

    # ── Public API ───────────────────────────────────────────────────────

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed a batch of texts via Gemini REST API."""
        if not texts:
            return np.empty((0, self._dimension), dtype=np.float32)

        await self._ensure_loaded()

        all_embeddings: list[list[float]] = []
        batch_size = 50  # Conservative batch size for REST API

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_embeddings = await self._embed_batch_rest(batch)
            all_embeddings.extend(batch_embeddings)

            # Small delay between batches to avoid rate limiting
            if i + batch_size < len(texts):
                await asyncio.sleep(0.3)

        arr = np.array(all_embeddings, dtype=np.float32)

        # L2 normalise
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1
        arr = arr / norms

        logger.debug("Embedded %d text(s) via Gemini REST API.", len(texts))
        return arr

    async def embed_query(self, query: str) -> np.ndarray:
        vectors = await self.embed_texts([query])
        return vectors[0]

    # ── REST API calls ───────────────────────────────────────────────────

    async def _embed_batch_rest(self, texts: list[str]) -> list[list[float]]:
        """Call Gemini batchEmbedContents REST endpoint directly."""
        assert self._client is not None

        # Build batch request payload
        requests_payload: list[dict[str, Any]] = []
        for text in texts:
            # Truncate very long texts to avoid API errors (max ~10k tokens)
            truncated = text[:8000] if len(text) > 8000 else text
            requests_payload.append({
                "model": f"models/{self._model_name}",
                "content": {"parts": [{"text": truncated}]},
                "taskType": "RETRIEVAL_DOCUMENT",
            })

        # Try multiple API versions in order
        api_versions = ["v1beta", "v1"]
        last_error = None

        for api_version in api_versions:
            url = (
                f"{_GEMINI_API_BASE}/{api_version}/"
                f"models/{self._model_name}:batchEmbedContents"
                f"?key={self._api_key}"
            )

            try:
                response = await self._client.post(
                    url,
                    json={"requests": requests_payload},
                )

                if response.status_code == 200:
                    data = response.json()
                    embeddings = [emb["values"] for emb in data["embeddings"]]
                    return embeddings

                last_error = f"HTTP {response.status_code}: {response.text[:500]}"
                logger.warning(
                    "Gemini REST %s failed: %s — trying next version",
                    api_version, last_error,
                )

            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "Gemini REST %s error: %s — trying next version",
                    api_version, exc,
                )

        # If batch endpoint fails on all versions, try single embedContent
        logger.warning("Batch endpoint failed, falling back to single embedContent calls")
        return await self._embed_single_fallback(texts)

    async def _embed_single_fallback(self, texts: list[str]) -> list[list[float]]:
        """Fallback: embed one text at a time via embedContent endpoint."""
        assert self._client is not None
        embeddings: list[list[float]] = []

        for text in texts:
            truncated = text[:8000] if len(text) > 8000 else text

            for api_version in ["v1beta", "v1"]:
                url = (
                    f"{_GEMINI_API_BASE}/{api_version}/"
                    f"models/{self._model_name}:embedContent"
                    f"?key={self._api_key}"
                )

                try:
                    response = await self._client.post(
                        url,
                        json={
                            "model": f"models/{self._model_name}",
                            "content": {"parts": [{"text": truncated}]},
                            "taskType": "RETRIEVAL_DOCUMENT",
                        },
                    )

                    if response.status_code == 200:
                        data = response.json()
                        embeddings.append(data["embedding"]["values"])
                        break
                    else:
                        logger.warning("embedContent %s: HTTP %d", api_version, response.status_code)

                except Exception as exc:
                    logger.warning("embedContent %s error: %s", api_version, exc)

            else:
                # All API versions failed for this text — raise
                raise RuntimeError(
                    f"Gemini embedding API failed for all API versions. "
                    f"Check your GEMINI_API_KEY and network connectivity."
                )

            # Rate limit protection
            await asyncio.sleep(0.1)

        return embeddings

    # ── Internals ────────────────────────────────────────────────────────

    async def _ensure_loaded(self) -> None:
        if not self.is_loaded:
            await self.load()
