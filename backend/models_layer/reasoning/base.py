"""
Abstract base class for LLM reasoning providers.

Every LLM back-end (Gemini, OpenAI, local models, …) must implement this
interface so the :class:`ReasoningModelFactory` can treat them uniformly.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import AsyncIterator

logger = logging.getLogger(__name__)


class ReasoningModel(ABC):
    """Contract for LLM-based text generation."""

    # ── Properties ───────────────────────────────────────────────────────

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Short identifier for this provider (e.g. ``gemini``, ``openai``)."""
        ...

    # ── Generation ───────────────────────────────────────────────────────

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """Generate a complete response for *prompt*.

        Parameters
        ----------
        prompt:
            User prompt / instruction.
        system_prompt:
            Optional system-level context.
        temperature:
            Sampling temperature (0 = deterministic, 1 = creative).
        max_tokens:
            Maximum number of tokens to generate.

        Returns
        -------
        str
            The model's full text response.
        """
        ...

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AsyncIterator[str]:
        """Stream tokens one-by-one for *prompt*.

        Yields
        ------
        str
            Individual text chunks / tokens as they arrive.
        """
        ...
        # The ``yield`` below is unreachable but makes the type-checker
        # recognise this method as an async generator.
        yield ""  # pragma: no cover

    # ── Health ───────────────────────────────────────────────────────────

    @abstractmethod
    async def health_check(self) -> bool:
        """Quick connectivity / availability check.

        Returns ``True`` when the provider is reachable and ready.
        """
        ...
