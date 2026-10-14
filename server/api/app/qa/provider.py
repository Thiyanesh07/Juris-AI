"""HTTP LLM provider abstraction (OpenAI-compatible chat completions)."""

from __future__ import annotations

import logging
import random
import asyncio
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

        max_retries = self._settings.llm_max_retries
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(self._url, headers=headers, json=payload)

                if response.status_code == 200:
                    break

                if response.status_code == 429 or 500 <= response.status_code < 600:
                    if attempt == max_retries:
                        logger.warning("LLM provider returned HTTP %s after %d retries", response.status_code, max_retries)
                        raise LLMProviderUnavailable(f"LLM provider error (HTTP {response.status_code})")

                    # Respect Retry-After header or use exponential backoff
                    retry_after = response.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        wait_time = float(retry_after)
                    else:
                        wait_time = (2 ** attempt) + random.uniform(0, 1)

                    logger.info("LLM provider returned HTTP %s. Retrying in %.2fs (attempt %d/%d)", response.status_code, wait_time, attempt + 1, max_retries)
                    await asyncio.sleep(wait_time)
                    continue

                if response.status_code >= 400:
                    logger.warning("LLM provider rejected request with HTTP %s", response.status_code)
                    raise LLMProviderUnavailable("LLM provider rejected the request")

            except (httpx.TimeoutException, httpx.RequestError) as exc:
                if attempt == max_retries:
                    logger.warning("LLM request failed after %d retries: %s", max_retries, type(exc).__name__)
                    raise LLMProviderUnavailable("LLM provider is unreachable") from exc

                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logger.info("LLM request failed (%s). Retrying in %.2fs (attempt %d/%d)", type(exc).__name__, wait_time, attempt + 1, max_retries)
                await asyncio.sleep(wait_time)

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


class GoogleGenAIProvider:
    """LLM provider for Google Gemini (google_genai)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._api_key = settings.llm_api_key.strip()
        self._model = settings.llm_model.strip() or "gemini-1.5-flash"
        
        base = settings.llm_base_url.rstrip("/") if settings.llm_base_url else ""
        if base and "openai" in base:
            self._openai_provider: OpenAICompatibleProvider | None = OpenAICompatibleProvider(settings)
        else:
            self._openai_provider = None
            model_id = self._model if self._model.startswith("models/") else f"models/{self._model}"
            self._url = f"https://generativelanguage.googleapis.com/v1beta/{model_id}:generateContent?key={self._api_key}"

    async def generate(
        self,
        *,
        system_message: str,
        user_message: str,
        timeout_seconds: float,
        max_output_tokens: int,
    ) -> str:
        if not self._api_key:
            raise LLMProviderUnavailable("LLM API key is not configured")

        if self._openai_provider is not None:
            return await self._openai_provider.generate(
                system_message=system_message,
                user_message=user_message,
                timeout_seconds=timeout_seconds,
                max_output_tokens=max_output_tokens,
            )

        headers = {"Content-Type": "application/json"}
        payload = {
            "system_instruction": {
                "parts": [{"text": system_message}]
            },
            "contents": [
                {"role": "user", "parts": [{"text": user_message}]}
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "maxOutputTokens": max_output_tokens,
            },
        }

        timeout = httpx.Timeout(timeout_seconds)

        max_retries = self._settings.llm_max_retries
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(self._url, headers=headers, json=payload)

                if response.status_code == 200:
                    break

                if response.status_code == 429 or 500 <= response.status_code < 600:
                    if attempt == max_retries:
                        logger.warning("Google GenAI returned HTTP %s after %d retries: %s", response.status_code, max_retries, response.text[:200])
                        raise LLMProviderUnavailable(f"LLM provider error (HTTP {response.status_code})")

                    # Respect Retry-After header or use exponential backoff
                    retry_after = response.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        wait_time = float(retry_after)
                    else:
                        wait_time = (2 ** attempt) + random.uniform(0, 1)

                    logger.info("Google GenAI returned HTTP %s. Retrying in %.2fs (attempt %d/%d)", response.status_code, wait_time, attempt + 1, max_retries)
                    await asyncio.sleep(wait_time)
                    continue

                if response.status_code >= 400:
                    logger.warning("Google GenAI rejected request with HTTP %s: %s", response.status_code, response.text[:200])
                    raise LLMProviderUnavailable(f"LLM provider rejected request (HTTP {response.status_code})")

            except (httpx.TimeoutException, httpx.RequestError) as exc:
                if attempt == max_retries:
                    logger.warning("Google GenAI LLM request failed after %d retries: %s", max_retries, type(exc).__name__)
                    raise LLMProviderUnavailable("LLM provider is unreachable") from exc

                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logger.info("Google GenAI LLM request failed (%s). Retrying in %.2fs (attempt %d/%d)", type(exc).__name__, wait_time, attempt + 1, max_retries)
                await asyncio.sleep(wait_time)

        try:
            body = response.json()
            if not isinstance(body, dict):
                raise LLMProviderMalformedResponse("Google GenAI response payload was malformed")
            candidates = body.get("candidates")
            if not isinstance(candidates, list) or not candidates:
                raise LLMProviderMalformedResponse("Google GenAI response returned no candidates")
            first = candidates[0]
            if not isinstance(first, dict):
                raise LLMProviderMalformedResponse("Google GenAI candidate was malformed")
            content_obj = first.get("content")
            if not isinstance(content_obj, dict):
                raise LLMProviderMalformedResponse("Google GenAI candidate content was malformed")
            parts = content_obj.get("parts")
            if not isinstance(parts, list) or not parts:
                raise LLMProviderMalformedResponse("Google GenAI content parts were missing")
            text_part = parts[0]
            if not isinstance(text_part, dict) or "text" not in text_part:
                raise LLMProviderMalformedResponse("Google GenAI text part was missing")
            content = text_part["text"]
        except LLMProviderMalformedResponse:
            raise
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMProviderMalformedResponse("Google GenAI response payload was malformed") from exc

        if not isinstance(content, str) or not content.strip():
            raise LLMProviderMalformedResponse("LLM returned empty content")

        logger.info(
            "Google GenAI LLM completion received (model=%s, chars=%d)",
            self._model,
            len(content),
        )
        return content


def build_llm_provider(settings: Settings) -> LLMProvider:
    """Construct the configured LLM provider."""
    provider_name = (settings.llm_provider or "").strip().lower()

    if not settings.llm_api_key.strip():
        raise LLMProviderUnavailable("LLM API key is not configured")

    if provider_name in ("google_genai", "gemini"):
        return GoogleGenAIProvider(settings)
    elif provider_name in ("openai_compatible", "openai", "groq", "together"):
        return OpenAICompatibleProvider(settings)
    else:
        if settings.llm_base_url and settings.llm_base_url.startswith("http"):
            return OpenAICompatibleProvider(settings)
        raise LLMProviderUnavailable(
            f"Unsupported LLM provider: {settings.llm_provider!r}"
        )


__all__ = [
    "GoogleGenAIProvider",
    "LLMProvider",
    "LLMProviderError",
    "LLMProviderMalformedResponse",
    "LLMProviderTimeout",
    "LLMProviderUnavailable",
    "OpenAICompatibleProvider",
    "build_llm_provider",
]
