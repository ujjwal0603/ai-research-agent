"""
Google Gemini reasoning provider.

Uses the ``google.generativeai`` SDK for both synchronous and streaming
content generation.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

from models_layer.reasoning.base import ReasoningModel

logger = logging.getLogger(__name__)


class GeminiProvider(ReasoningModel):
    """LLM provider backed by Google Gemini.

    Parameters
    ----------
    api_key:
        Google AI / Gemini API key.
    model_name:
        Gemini model variant.  Defaults to ``gemini-2.0-flash``.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.0-flash",
    ) -> None:
        import google.generativeai as genai  # type: ignore[import-untyped]

        self._api_key = api_key
        self._model_name = model_name

        genai.configure(api_key=self._api_key)
        self._genai = genai
        self._model = genai.GenerativeModel(self._model_name)

        logger.info("GeminiProvider initialised (model=%s).", self._model_name)

    # ── ReasoningModel interface ─────────────────────────────────────────

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """Generate a full response via Gemini ``generate_content_async``."""
        contents = self._build_contents(prompt, system_prompt)
        generation_config = self._genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        try:
            response = await self._model.generate_content_async(
                contents,
                generation_config=generation_config,
            )
            text = response.text
            logger.debug(
                "GeminiProvider.generate completed (%d chars).", len(text)
            )
            return text
        except Exception as exc:
            logger.error("GeminiProvider.generate failed: %s", exc)
            raise

    async def generate_stream(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AsyncIterator[str]:
        """Stream tokens from Gemini."""
        contents = self._build_contents(prompt, system_prompt)
        generation_config = self._genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        try:
            response = await self._model.generate_content_async(
                contents,
                generation_config=generation_config,
                stream=True,
            )
            async for chunk in response:  # type: ignore[union-attr]
                if chunk.text:
                    yield chunk.text
        except Exception as exc:
            logger.error("GeminiProvider.generate_stream failed: %s", exc)
            raise

    async def health_check(self) -> bool:
        """Send a tiny request to verify connectivity."""
        try:
            response = await self._model.generate_content_async(
                "ping",
                generation_config=self._genai.GenerationConfig(
                    max_output_tokens=5,
                ),
            )
            return bool(response.text)
        except Exception:
            logger.warning("GeminiProvider health-check failed.", exc_info=True)
            return False

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _build_contents(
        prompt: str, system_prompt: str | None
    ) -> str | list[str]:
        """Build the ``contents`` argument for ``generate_content_async``.

        If a system prompt is provided it is prepended to the user prompt.
        Gemini models accept a plain string or list.
        """
        if system_prompt:
            return f"{system_prompt}\n\n{prompt}"
        return prompt
