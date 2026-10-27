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
                        wait_time = min(float(retry_after), 2.0)
                    else:
                        wait_time = min((2 ** attempt) + random.uniform(0, 0.5), 2.0)

                    logger.info("LLM provider returned HTTP %s. Retrying in %.2fs (attempt %d/%d)", response.status_code, wait_time, attempt + 1, max_retries)
                    await asyncio.sleep(wait_time)
                    continue

                if response.status_code >= 400:
                    logger.warning("LLM provider rejected request with HTTP %s", response.status_code)
                    raise LLMProviderUnavailable("LLM provider rejected the request")

            except httpx.TimeoutException as exc:
                if attempt == max_retries:
                    logger.warning("LLM request timed out after %d retries: %s", max_retries, type(exc).__name__)
                    raise LLMProviderTimeout("LLM provider timed out") from exc

                wait_time = min((2 ** attempt) + random.uniform(0, 0.5), 2.0)
                logger.info("LLM request timed out (%s). Retrying in %.2fs (attempt %d/%d)", type(exc).__name__, wait_time, attempt + 1, max_retries)
                await asyncio.sleep(wait_time)
            except httpx.RequestError as exc:
                if attempt == max_retries:
                    logger.warning("LLM request failed after %d retries: %s", max_retries, type(exc).__name__)
                    raise LLMProviderUnavailable("LLM provider is unreachable") from exc

                wait_time = min((2 ** attempt) + random.uniform(0, 0.5), 2.0)
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
        model_id = self._model if self._model.startswith("models/") else f"models/{self._model}"

        # Google GenAI uses the Generative Language API endpoint.
        # If an explicit Google GenAI base URL is provided (e.g. custom proxy or private endpoint
        # targeting generativelanguage or googleapis.com), respect it.
        # Otherwise, or if base_url points to an unrelated/OpenAI endpoint, default to the official endpoint.
        base = (settings.llm_base_url or "").strip().rstrip("/")
        if base and ("googleapis.com" in base or "generativelanguage" in base):
            self._url = f"{base}/{model_id}:generateContent?key={self._api_key}"
        else:
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
                        wait_time = min(float(retry_after), 2.0)
                    else:
                        wait_time = min((2 ** attempt) + random.uniform(0, 0.5), 2.0)

                    logger.info("Google GenAI returned HTTP %s. Retrying in %.2fs (attempt %d/%d)", response.status_code, wait_time, attempt + 1, max_retries)
                    await asyncio.sleep(wait_time)
                    continue

                if response.status_code >= 400:
                    logger.warning("Google GenAI rejected request with HTTP %s: %s", response.status_code, response.text[:200])
                    raise LLMProviderUnavailable(f"LLM provider rejected request (HTTP {response.status_code})")

            except httpx.TimeoutException as exc:
                if attempt == max_retries:
                    logger.warning("Google GenAI LLM request timed out after %d retries: %s", max_retries, type(exc).__name__)
                    raise LLMProviderTimeout("Google GenAI LLM provider timed out") from exc

                wait_time = min((2 ** attempt) + random.uniform(0, 0.5), 2.0)
                logger.info("Google GenAI LLM request timed out (%s). Retrying in %.2fs (attempt %d/%d)", type(exc).__name__, wait_time, attempt + 1, max_retries)
                await asyncio.sleep(wait_time)
            except httpx.RequestError as exc:
                if attempt == max_retries:
                    logger.warning("Google GenAI LLM request failed after %d retries: %s", max_retries, type(exc).__name__)
                    raise LLMProviderUnavailable("LLM provider is unreachable") from exc

                wait_time = min((2 ** attempt) + random.uniform(0, 0.5), 2.0)
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

    if not provider_name:
        raise LLMProviderUnavailable("LLM provider is not configured")

    if provider_name in ("google_genai", "gemini"):
        return GoogleGenAIProvider(settings)
    elif provider_name in ("openai_compatible", "openai", "groq", "together"):
        if not settings.llm_base_url.strip():
            raise LLMProviderUnavailable("LLM base URL is not configured for OpenAI-compatible provider")
        return OpenAICompatibleProvider(settings)
    else:
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
