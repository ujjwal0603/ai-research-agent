"""
Central registry for all ML models used by the platform.

Implements the singleton pattern so every part of the application shares
the same model instances.
"""

from __future__ import annotations

import logging

from config.settings import get_settings
from models_layer.embedding_model import EmbeddingModel
from models_layer.classification_model import ClassificationModel
from models_layer.reranking_model import RerankingModel
from models_layer.reasoning.factory import ReasoningModelFactory

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Singleton that owns and exposes all loaded model instances.

    Usage::

        registry = ModelRegistry()
        await registry.initialize()
        emb = registry.get_embedding_model()
    """

    _instance: ModelRegistry | None = None

    def __new__(cls) -> ModelRegistry:  # noqa: D102
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False  # type: ignore[attr-defined]
        return cls._instance

    def __init__(self) -> None:
        # Guard against re-initialising fields on repeated __init__ calls
        # (Python calls __init__ every time even when __new__ returns a
        # cached instance).
        if getattr(self, "_fields_set", False):
            return
        self._embedding_model: EmbeddingModel | None = None
        self._classification_model: ClassificationModel | None = None
        self._reranking_model: RerankingModel | None = None
        self._reasoning_factory: ReasoningModelFactory | None = None
        self._initialized: bool = False
        self._fields_set: bool = True

    # ── Lifecycle ────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Create and load every model according to ``Settings``."""
        if self._initialized:
            logger.debug("ModelRegistry already initialised — skipping.")
            return

        settings = get_settings()
        logger.info("ModelRegistry: initialising all models …")

        # Embedding
        self._embedding_model = EmbeddingModel(
            model_name_or_path=settings.EMBEDDING_MODEL,
        )

        # Classification
        self._classification_model = ClassificationModel()

        # Reranking
        self._reranking_model = RerankingModel(
            model_name_or_path=settings.RERANKING_MODEL,
        )

        # Reasoning (LLM)
        self._reasoning_factory = ReasoningModelFactory()

        self._initialized = True
        logger.info("ModelRegistry: all models initialised successfully.")

    async def shutdown(self) -> None:
        """Unload every model and free resources."""
        logger.info("ModelRegistry: shutting down …")

        if self._embedding_model is not None:
            await self._embedding_model.unload()
        if self._classification_model is not None:
            await self._classification_model.unload()
        if self._reranking_model is not None:
            await self._reranking_model.unload()

        self._initialized = False
        logger.info("ModelRegistry: shutdown complete.")

    # ── Accessors ────────────────────────────────────────────────────────

    def get_embedding_model(self) -> EmbeddingModel:
        """Return the embedding model instance.

        Raises
        ------
        RuntimeError
            If the registry has not been initialised.
        """
        if self._embedding_model is None:
            raise RuntimeError(
                "ModelRegistry not initialised — call `await initialize()` first."
            )
        return self._embedding_model

    def get_classification_model(self) -> ClassificationModel:
        """Return the classification model instance."""
        if self._classification_model is None:
            raise RuntimeError(
                "ModelRegistry not initialised — call `await initialize()` first."
            )
        return self._classification_model

    def get_reranking_model(self) -> RerankingModel:
        """Return the reranking model instance."""
        if self._reranking_model is None:
            raise RuntimeError(
                "ModelRegistry not initialised — call `await initialize()` first."
            )
        return self._reranking_model

    def get_reasoning_factory(self) -> ReasoningModelFactory:
        """Return the reasoning model factory."""
        if self._reasoning_factory is None:
            raise RuntimeError(
                "ModelRegistry not initialised — call `await initialize()` first."
            )
        return self._reasoning_factory

    # ── Health ───────────────────────────────────────────────────────────

    async def health_check(self) -> dict[str, bool | dict[str, bool]]:
        """Run health checks on every registered model.

        Returns
        -------
        dict
            Mapping of model category → health status.
        """
        results: dict[str, bool | dict[str, bool]] = {}

        if self._embedding_model is not None:
            results["embedding"] = await self._embedding_model.health_check()
        else:
            results["embedding"] = False

        if self._classification_model is not None:
            results["classification"] = await self._classification_model.health_check()
        else:
            results["classification"] = False

        if self._reranking_model is not None:
            results["reranking"] = await self._reranking_model.health_check()
        else:
            results["reranking"] = False

        if self._reasoning_factory is not None:
            results["reasoning"] = await self._reasoning_factory.health_check()
        else:
            results["reasoning"] = False

        return results

    # ── Class-level reset (for testing) ──────────────────────────────────

    @classmethod
    def reset(cls) -> None:
        """Destroy the singleton (useful in test fixtures)."""
        cls._instance = None
