"""
Abstract base class for all model providers in the platform.

Every model — embedding, classification, reranking — inherits from
`ModelProvider` to guarantee a consistent lifecycle interface.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ModelProvider(ABC):
    """Base contract for every ML model managed by the platform.

    Sub-classes must implement ``load``, ``unload``, and ``health_check`` so the
    :class:`ModelRegistry` can manage their lifecycle uniformly.
    """

    # ── Abstract Properties ──────────────────────────────────────────────

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Human-readable model identifier (e.g. ``all-MiniLM-L6-v2``)."""
        ...

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        """Return ``True`` when the model weights are in memory and ready."""
        ...

    # ── Lifecycle ────────────────────────────────────────────────────────

    @abstractmethod
    async def load(self) -> None:
        """Load the model into memory.

        Implementations should be idempotent — calling ``load`` when the
        model is already loaded should be a no-op.
        """
        ...

    @abstractmethod
    async def unload(self) -> None:
        """Release model resources and free memory."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Quick sanity check that the model is operational.

        Returns
        -------
        bool
            ``True`` if the model can serve inference requests.
        """
        ...
