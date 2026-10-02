"""HTTP LLM provider abstraction (OpenAI-compatible chat completions)."""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class LLMProviderError(Exception):
    """Base class for provider failures."""


class LLMProviderTimeout(LLMProviderError):
    """The upstream LLM did not respond in time."""


class LLMProviderUnavailable(LLMProviderError):
    """The LLM provider is misconfigured or unreachable."""


class LLMProviderMalformedResponse(LLMProviderError):
    """The provider returned an unexpected payload."""


@runtime_checkable
class LLMProvider(Protocol):
    async def generate(
        self,
        *,
        system_message: str,
        user_message: str,
        timeout_seconds: float,
        max_output_tokens: int,
    ) -> str:
        """Return the assistant message content as plain text."""
        ...


class OpenAICompatibleProvider:
    """Chat completions client for OpenAI-compatible HTTP APIs."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        base = settings.llm_base_url.rstrip("/")
        self._url = f"{base}/chat/completions"
        self._model = settings.llm_model
        self._api_key = settings.llm_api_key

    async def generate(
        self,
        *,
        system_message: str,
        user_message: str,
        timeout_seconds: float,
        max_output_tokens: int,
    ) -> str:
        if not self._api_key.strip():
            raise LLMProviderUnavailable("LLM API key is not configured")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": max_output_tokens,
            "response_format": {"type": "json_object"},
        }
        timeout = httpx.Timeout(timeout_seconds)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(self._url, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            logger.warning("LLM request timed out after %ss", timeout_seconds)
            raise LLMProviderTimeout("LLM request timed out") from exc
        except httpx.RequestError as exc:
            logger.warning("LLM request failed: %s", type(exc).__name__)
            raise LLMProviderUnavailable("LLM provider is unreachable") from exc

        if response.status_code >= 500:
            logger.warning("LLM provider returned HTTP %s", response.status_code)
            raise LLMProviderUnavailable("LLM provider error")
        if response.status_code >= 400:
            logger.warning("LLM provider rejected request with HTTP %s", response.status_code)
            raise LLMProviderUnavailable("LLM provider rejected the request")

        try:
            body = response.json()
            if not isinstance(body, dict):
                raise LLMProviderMalformedResponse("LLM response payload was malformed")
            choices = body.get("choices")
            if not isinstance(choices, list) or not choices:
                raise LLMProviderMalformedResponse("LLM response payload was malformed")
            first = choices[0]
            if not isinstance(first, dict):
                raise LLMProviderMalformedResponse("LLM response payload was malformed")
            message = first.get("message")
            if not isinstance(message, dict):
                raise LLMProviderMalformedResponse("LLM response payload was malformed")
            content = message.get("content")
        except LLMProviderMalformedResponse:
            raise
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMProviderMalformedResponse("LLM response payload was malformed") from exc

        if not isinstance(content, str) or not content.strip():
            raise LLMProviderMalformedResponse("LLM returned empty content")

        logger.info(
            "LLM completion received (model=%s, chars=%d)",
            self._model,
            len(content),
        )
        return content


def build_llm_provider(settings: Settings) -> LLMProvider:
    """Construct the configured LLM provider."""
    if settings.llm_provider != "openai_compatible":
        raise LLMProviderUnavailable(
            f"Unsupported LLM provider: {settings.llm_provider!r}"
        )
    if not settings.llm_api_key.strip():
        raise LLMProviderUnavailable("LLM API key is not configured")
    return OpenAICompatibleProvider(settings)


__all__ = [
    "LLMProvider",
    "LLMProviderError",
    "LLMProviderMalformedResponse",
    "LLMProviderTimeout",
    "LLMProviderUnavailable",
    "OpenAICompatibleProvider",
    "build_llm_provider",
]
