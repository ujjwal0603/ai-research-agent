"""
OpenAI reasoning provider.

Uses the ``openai.AsyncOpenAI`` client for chat completion,
supporting both full and streaming responses.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

from models_layer.reasoning.base import ReasoningModel

logger = logging.getLogger(__name__)


class OpenAIProvider(ReasoningModel):
    """LLM provider backed by OpenAI chat completions.

    Parameters
    ----------
    api_key:
        OpenAI API key.
    model_name:
        Model to use.  Defaults to ``gpt-4o-mini``.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-4o-mini",
    ) -> None:
        import openai  # type: ignore[import-untyped]

        self._api_key = api_key
        self._model_name = model_name
        self._client = openai.AsyncOpenAI(api_key=self._api_key)
        logger.info("OpenAIProvider initialised (model=%s).", self._model_name)

    # ── ReasoningModel interface ─────────────────────────────────────────

    @property
    def provider_name(self) -> str:
        return "openai"

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """Generate a full chat completion."""
        messages = self._build_messages(prompt, system_prompt)

        try:
            response = await self._client.chat.completions.create(
                model=self._model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            text = response.choices[0].message.content or ""
            logger.debug(
                "OpenAIProvider.generate completed (%d chars).", len(text)
            )
            return text
        except Exception as exc:
            logger.error("OpenAIProvider.generate failed: %s", exc)
            raise

    async def generate_stream(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AsyncIterator[str]:
        """Stream tokens from OpenAI's chat completion API."""
        messages = self._build_messages(prompt, system_prompt)

        try:
            stream = await self._client.chat.completions.create(
                model=self._model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
        except Exception as exc:
            logger.error("OpenAIProvider.generate_stream failed: %s", exc)
            raise

    async def health_check(self) -> bool:
        """Send a small request to verify the API key works."""
        try:
            response = await self._client.chat.completions.create(
                model=self._model_name,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return bool(response.choices[0].message.content)
        except Exception:
            logger.warning("OpenAIProvider health-check failed.", exc_info=True)
            return False

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _build_messages(
        prompt: str,
        system_prompt: str | None,
    ) -> list[dict[str, str]]:
        """Assemble the ``messages`` list for the chat API."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages
