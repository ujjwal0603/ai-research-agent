"""
Factory for reasoning (LLM) providers with automatic fallback.

The factory reads available API keys from settings and builds an ordered
list of providers.  ``generate`` / ``generate_stream`` will try each
provider in turn until one succeeds, implementing a simple retry-fallback
strategy.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

from config.settings import get_settings
from models_layer.reasoning.base import ReasoningModel
from models_layer.reasoning.gemini_provider import GeminiProvider
from models_layer.reasoning.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)


# ── Custom Exceptions ───────────────────────────────────────────────────────


class ProviderError(Exception):
    """A single LLM provider failed."""

    def __init__(self, provider_name: str, original: Exception) -> None:
        self.provider_name = provider_name
        self.original = original
        super().__init__(
            f"Provider '{provider_name}' failed: {original}"
        )


class AllProvidersFailedError(Exception):
    """Every configured provider failed to produce a response."""

    def __init__(self, errors: list[ProviderError]) -> None:
        self.errors = errors
        details = "; ".join(str(e) for e in errors)
        super().__init__(f"All providers failed — {details}")


# ── Factory ─────────────────────────────────────────────────────────────────


class ReasoningModelFactory:
    """Manages multiple LLM providers with ordered fallback.

    On construction the factory inspects ``Settings`` for available API keys
    and instantiates the corresponding providers.  Gemini is preferred over
    OpenAI by default.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._providers: dict[str, ReasoningModel] = {}
        self._ordered: list[ReasoningModel] = []

        # Gemini — preferred
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your_gemini_api_key_here":
            provider = GeminiProvider(
                api_key=settings.GEMINI_API_KEY,
                model_name=settings.GEMINI_MODEL,
            )
            self._providers["gemini"] = provider
            self._ordered.append(provider)
            logger.info("Registered reasoning provider: gemini (%s)", settings.GEMINI_MODEL)

        # OpenAI — fallback
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your_openai_api_key_here":
            provider = OpenAIProvider(
                api_key=settings.OPENAI_API_KEY,
                model_name=settings.OPENAI_MODEL,
            )
            self._providers["openai"] = provider
            self._ordered.append(provider)
            logger.info("Registered reasoning provider: openai (%s)", settings.OPENAI_MODEL)

        if not self._ordered:
            logger.warning(
                "No LLM API keys configured — reasoning will be unavailable."
            )

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def providers(self) -> list[ReasoningModel]:
        """Ordered list of available providers."""
        return list(self._ordered)

    @property
    def available_provider_names(self) -> list[str]:
        return list(self._providers.keys())

    # ── Lookup ───────────────────────────────────────────────────────────

    def get_provider(self, name: str) -> ReasoningModel:
        """Return a specific provider by name.

        Raises
        ------
        KeyError
            If the requested provider is not registered.
        """
        if name not in self._providers:
            raise KeyError(
                f"Provider '{name}' is not registered. "
                f"Available: {self.available_provider_names}"
            )
        return self._providers[name]

    # ── Generation (with fallback) ───────────────────────────────────────

    async def generate(
        self,
        prompt: str,
        *,
        provider: str = "auto",
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """Generate a response, falling back across providers on failure.

        Parameters
        ----------
        prompt:
            User prompt text.
        provider:
            ``"auto"`` (try all in order), ``"gemini"``, or ``"openai"``.
        """
        targets = self._resolve_targets(provider)
        errors: list[ProviderError] = []

        for target in targets:
            try:
                return await target.generate(
                    prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as exc:
                err = ProviderError(target.provider_name, exc)
                errors.append(err)
                logger.warning(
                    "Provider '%s' failed, trying next: %s",
                    target.provider_name, exc,
                )

        raise AllProvidersFailedError(errors)

    async def generate_stream(
        self,
        prompt: str,
        *,
        provider: str = "auto",
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AsyncIterator[str]:
        """Stream tokens with automatic provider fallback.

        If the first provider fails *before* yielding any tokens the next
        one is tried.  Once tokens have started flowing, errors propagate
        immediately (partial retry is not attempted).
        """
        targets = self._resolve_targets(provider)
        errors: list[ProviderError] = []

        for target in targets:
            try:
                started = False
                async for token in target.generate_stream(
                    prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ):
                    started = True
                    yield token
                # If we got here, stream completed successfully.
                return
            except Exception as exc:
                if started:
                    # Already yielded tokens — do NOT silently retry.
                    raise
                err = ProviderError(target.provider_name, exc)
                errors.append(err)
                logger.warning(
                    "Streaming from '%s' failed pre-yield, trying next: %s",
                    target.provider_name, exc,
                )

        raise AllProvidersFailedError(errors)

    # ── Health ───────────────────────────────────────────────────────────

    async def health_check(self) -> dict[str, bool]:
        """Check every registered provider's health."""
        results: dict[str, bool] = {}
        for name, prov in self._providers.items():
            results[name] = await prov.health_check()
        return results

    # ── Internal ─────────────────────────────────────────────────────────

    def _resolve_targets(self, provider: str) -> list[ReasoningModel]:
        """Return the providers to try, based on the *provider* arg."""
        if provider == "auto":
            if not self._ordered:
                raise AllProvidersFailedError([])
            return list(self._ordered)

        return [self.get_provider(provider)]
