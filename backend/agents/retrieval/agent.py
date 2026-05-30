"""
Retrieval agent — executes search actions (dense, sparse, hybrid, rerank).

The retrieval agent is the primary information retrieval component of the
multi-agent pipeline.  It delegates actual search to a
``SearchStrategyExecutor`` instance.
"""

from __future__ import annotations

import logging
import time
from typing import Any, TYPE_CHECKING

from agents.base import BaseAgent
from agents.retrieval.strategies import SearchStrategyExecutor
from config.constants import DEFAULT_TOP_K, SearchStrategy
from schemas.agents import AgentResult, AgentTask

if TYPE_CHECKING:
    from models_layer.embedding_model import EmbeddingModel
    from models_layer.model_registry import ModelRegistry
    from models_layer.reranking_model import RerankingModel

logger = logging.getLogger(__name__)


class RetrievalAgent(BaseAgent):
    """Agent responsible for all search / retrieval operations.

    Capabilities
    -------------
    - ``dense_search`` — nearest-neighbour vector search.
    - ``sparse_search`` — BM25-style keyword search.
    - ``hybrid_search`` — fused dense + sparse search.
    - ``rerank`` — cross-encoder reranking of an existing result set.

    Parameters
    ----------
    qdrant_store:
        Vector store adapter (FAISS or Qdrant).
    hybrid_engine:
        Hybrid search engine (may be ``None`` in early phases).
    model_registry:
        Central model registry to obtain embedding / reranking models.
    """

    # ── BaseAgent properties ────────────────────────────────────────────

    @property
    def agent_id(self) -> str:
        return "retrieval_agent"

    @property
    def agent_name(self) -> str:
        return "Retrieval Agent"

    @property
    def capabilities(self) -> list[str]:
        return ["dense_search", "sparse_search", "hybrid_search", "rerank"]

    @property
    def required_models(self) -> list[str]:
        return ["embedding", "reranking"]

    # ── Initialisation ──────────────────────────────────────────────────

    def __init__(
        self,
        qdrant_store: Any,
        hybrid_engine: Any | None = None,
        model_registry: ModelRegistry | None = None,
    ) -> None:
        self._qdrant_store = qdrant_store
        self._hybrid_engine = hybrid_engine
        self._model_registry = model_registry
        self._strategy: SearchStrategyExecutor | None = None
        logger.info("RetrievalAgent created.")

    # ── Lazy strategy initialisation ────────────────────────────────────

    async def _get_strategy(self) -> SearchStrategyExecutor:
        """Build (or return cached) ``SearchStrategyExecutor``."""
        if self._strategy is not None:
            return self._strategy

        embedding_model = await self._resolve_embedding_model()
        reranking_model = await self._resolve_reranking_model()

        self._strategy = SearchStrategyExecutor(
            qdrant_store=self._qdrant_store,
            hybrid_engine=self._hybrid_engine,
            embedding_model=embedding_model,
            reranking_model=reranking_model,
        )
        return self._strategy

    async def _resolve_embedding_model(self) -> EmbeddingModel:
        """Get the embedding model from the registry or create a default."""
        if self._model_registry is not None:
            try:
                model = self._model_registry.get_model("embedding")
                if not model.is_loaded:
                    await model.load()
                return model  # type: ignore[return-value]
            except (KeyError, AttributeError):
                logger.warning("Embedding model not in registry — creating default.")

        from models_layer.embedding_model import EmbeddingModel

        model = EmbeddingModel()
        await model.load()
        return model

    async def _resolve_reranking_model(self) -> RerankingModel | None:
        """Get the reranking model from the registry, or ``None``."""
        if self._model_registry is not None:
            try:
                model = self._model_registry.get_model("reranking")
                if not model.is_loaded:
                    await model.load()
                return model  # type: ignore[return-value]
            except (KeyError, AttributeError):
                logger.warning("Reranking model not in registry — reranking disabled.")

        return None

    # ── BaseAgent interface ─────────────────────────────────────────────

    async def validate_input(self, task: AgentTask) -> bool:
        """Validate that the task payload contains the required fields."""
        action = task.payload.get("action")
        if action not in self.capabilities:
            logger.warning(
                "Invalid action '%s' for RetrievalAgent. Valid: %s",
                action,
                self.capabilities,
            )
            return False

        if action == "rerank":
            # Rerank requires 'chunks' in payload.
            if not task.payload.get("chunks"):
                logger.warning("Rerank action requires 'chunks' in payload.")
                return False
        else:
            # All search actions require 'query'.
            if not task.payload.get("query"):
                logger.warning("Search action requires 'query' in payload.")
                return False

        return True

    async def execute(self, task: AgentTask) -> AgentResult:
        """Dispatch to the appropriate search strategy.

        The task ``payload`` must contain:
        - ``action``: one of ``dense_search``, ``sparse_search``,
          ``hybrid_search``, ``rerank``.
        - ``query``: the search query (not needed for ``rerank``).
        - ``top_k`` (optional): number of results.
        - ``filters`` (optional): payload filter dict.
        - ``search_strategy`` (optional): override strategy hint.
        - ``alpha`` (optional): hybrid fusion weight.
        - ``chunks`` (required for ``rerank``): list of chunk dicts.
        """
        start = time.perf_counter()

        # Validate
        if not await self.validate_input(task):
            latency = int((time.perf_counter() - start) * 1000)
            return self._create_result(
                task,
                status="failure",
                output_data={},
                error="Invalid input for RetrievalAgent.",
                latency_ms=latency,
            )

        action: str = task.payload["action"]
        query: str = task.payload.get("query", "")
        top_k: int = task.payload.get("top_k", DEFAULT_TOP_K)
        filters: dict | None = task.payload.get("filters")
        alpha: float = task.payload.get("alpha", 0.5)

        try:
            strategy = await self._get_strategy()

            if action == "dense_search":
                chunks = await strategy.execute_dense(query, top_k, filters)
            elif action == "sparse_search":
                document_id = (filters or {}).get("document_id")
                chunks = await strategy.execute_sparse(query, top_k, document_id)
            elif action == "hybrid_search":
                chunks = await strategy.execute_hybrid(query, top_k, filters, alpha)
            elif action == "rerank":
                input_chunks = task.payload.get("chunks", [])
                chunks = await strategy.rerank_results(query, input_chunks, top_k)
            else:
                chunks = []

            latency = int((time.perf_counter() - start) * 1000)
            logger.info(
                "RetrievalAgent.%s completed: %d chunks in %d ms.",
                action, len(chunks), latency,
            )
            return self._create_result(
                task,
                status="success",
                output_data={
                    "chunks": chunks,
                    "chunk_count": len(chunks),
                    "action": action,
                    "query": query,
                },
                latency_ms=latency,
            )

        except Exception as exc:
            latency = int((time.perf_counter() - start) * 1000)
            logger.error(
                "RetrievalAgent.%s failed after %d ms: %s",
                action, latency, exc,
            )
            return self._create_result(
                task,
                status="failure",
                output_data={"action": action, "query": query},
                error=str(exc),
                latency_ms=latency,
            )

    # ── Health check override ───────────────────────────────────────────

    async def health_check(self) -> dict[str, Any]:
        """Check that models and store are reachable."""
        base = await super().health_check()
        try:
            strategy = await self._get_strategy()
            base["embedding_model_loaded"] = (
                strategy._embedding_model.is_loaded
            )
            base["reranking_model_loaded"] = (
                strategy._reranking_model is not None
                and strategy._reranking_model.is_loaded
            )
        except Exception as exc:
            base["status"] = "unhealthy"
            base["error"] = str(exc)
        return base
