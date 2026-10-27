"""Unit tests for the OpenAI-compatible LLM provider."""

from __future__ import annotations

import logging
from typing import Any

import httpx
import pytest

from app.core.config import Settings
from app.qa.provider import (
    LLMProviderMalformedResponse,
    LLMProviderTimeout,
    LLMProviderUnavailable,
    OpenAICompatibleProvider,
    build_llm_provider,
)


def _settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {
        "session_secret": "x",
        "llm_provider": "openai_compatible",
        "llm_model": "gpt-4o-mini",
        "llm_api_key": "secret-key",
        "llm_base_url": "https://api.openai.com/v1",
    }
    base.update(overrides)
    return Settings(**base)


class _FakeAsyncClient:
    def __init__(self, handler: Any, **_kwargs: Any) -> None:
        self.handler = handler

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any],
    ) -> httpx.Response:
        res: httpx.Response = await self.handler(url, headers=headers, json=json)
        return res


def _make_client(handler: Any) -> Any:
    def _factory(*args: object, **kwargs: Any) -> _FakeAsyncClient:
        return _FakeAsyncClient(handler, **kwargs)

    return _factory


@pytest.mark.asyncio
async def test_successful_http_response(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(url: str, *, headers: dict[str, str], json: dict[str, Any]) -> httpx.Response:
        assert headers["Authorization"] == "Bearer secret-key"
        assert url.endswith("/chat/completions")
        assert json["model"] == "gpt-4o-mini"
        assert json["max_tokens"] == 100
        assert json["response_format"] == {"type": "json_object"}
        assert json["messages"][0]["role"] == "system"
        assert json["messages"][1]["role"] == "user"
        assert "api_key" not in json
        assert "secret-key" not in json.values()
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"answer":"ok"}'}}]},
        )

    captured: dict[str, Any] = {}

    def fake_client(*_args: Any, **kwargs: Any) -> _FakeAsyncClient:
        captured.update(kwargs)
        return _FakeAsyncClient(handler, **kwargs)

    monkeypatch.setattr("app.qa.provider.httpx.AsyncClient", fake_client)
    provider = OpenAICompatibleProvider(_settings())
    text = await provider.generate(
        system_message="sys",
        user_message="user",
        timeout_seconds=5,
        max_output_tokens=100,
    )
    assert "ok" in text
    assert isinstance(captured.get("timeout"), httpx.Timeout)


@pytest.mark.asyncio
async def test_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(_url: str, **_kwargs: Any) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    monkeypatch.setattr(
        "app.qa.provider.httpx.AsyncClient",
        _make_client(handler),
    )
    provider = OpenAICompatibleProvider(_settings())
    with pytest.raises(LLMProviderTimeout):
        await provider.generate(
            system_message="s",
            user_message="u",
            timeout_seconds=1,
            max_output_tokens=10,
        )


@pytest.mark.asyncio
async def test_connection_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(_url: str, **_kwargs: Any) -> httpx.Response:
        raise httpx.ConnectError("down")

    monkeypatch.setattr(
        "app.qa.provider.httpx.AsyncClient",
        _make_client(handler),
    )
    provider = OpenAICompatibleProvider(_settings())
    with pytest.raises(LLMProviderUnavailable):
        await provider.generate(
            system_message="s",
            user_message="u",
            timeout_seconds=1,
            max_output_tokens=10,
        )


@pytest.mark.asyncio
async def test_http_5xx(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(_url: str, **_kwargs: Any) -> httpx.Response:
        return httpx.Response(503, json={"error": "busy"})

    monkeypatch.setattr(
        "app.qa.provider.httpx.AsyncClient",
        _make_client(handler),
    )
    provider = OpenAICompatibleProvider(_settings())
    with pytest.raises(LLMProviderUnavailable):
        await provider.generate(
            system_message="s",
            user_message="u",
            timeout_seconds=1,
            max_output_tokens=10,
        )


@pytest.mark.asyncio
async def test_http_4xx(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(_url: str, **_kwargs: Any) -> httpx.Response:
        return httpx.Response(401, json={"error": "bad key"})

    monkeypatch.setattr(
        "app.qa.provider.httpx.AsyncClient",
        _make_client(handler),
    )
    provider = OpenAICompatibleProvider(_settings())
    with pytest.raises(LLMProviderUnavailable):
        await provider.generate(
            system_message="s",
            user_message="u",
            timeout_seconds=1,
            max_output_tokens=10,
        )


def test_missing_api_key() -> None:
    with pytest.raises(LLMProviderUnavailable):
        build_llm_provider(_settings(llm_api_key=""))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"unexpected": True},
        {"choices": []},
        {"choices": [{}]},
        {"choices": [{"message": {}}]},
        {"choices": [{"message": {"content": None}}]},
        {"choices": "nope"},
    ],
)
async def test_malformed_response_shapes(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, Any],
) -> None:
    async def handler(_url: str, **_kwargs: Any) -> httpx.Response:
        return httpx.Response(200, json=payload)

    monkeypatch.setattr(
        "app.qa.provider.httpx.AsyncClient",
        _make_client(handler),
    )
    provider = OpenAICompatibleProvider(_settings())
    with pytest.raises(LLMProviderMalformedResponse):
        await provider.generate(
            system_message="s",
            user_message="u",
            timeout_seconds=1,
            max_output_tokens=10,
        )


@pytest.mark.asyncio
async def test_api_key_not_logged(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)

    async def handler(_url: str, **_kwargs: Any) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"answer":"x"}'}}]},
        )

    monkeypatch.setattr(
        "app.qa.provider.httpx.AsyncClient",
        _make_client(handler),
    )
    provider = OpenAICompatibleProvider(_settings())
    await provider.generate(
        system_message="s",
        user_message="u",
        timeout_seconds=1,
        max_output_tokens=10,
    )
    joined = " ".join(record.message for record in caplog.records)
    assert "secret-key" not in joined


@pytest.mark.asyncio
async def test_google_genai_provider_success(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(url: str, *, headers: dict[str, str], json: dict[str, Any]) -> httpx.Response:
        assert "generativelanguage.googleapis.com" in url
        assert json["system_instruction"]["parts"][0]["text"] == "sys"
        assert json["contents"][0]["parts"][0]["text"] == "user"
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": '{"answer":"gemini_ok"}'}]}}]},
        )

    monkeypatch.setattr(
        "app.qa.provider.httpx.AsyncClient",
        _make_client(handler),
    )
    settings = _settings(llm_provider="google_genai", llm_model="gemini-1.5-flash", llm_base_url="")
    provider = build_llm_provider(settings)
    text = await provider.generate(
        system_message="sys",
        user_message="user",
        timeout_seconds=5,
        max_output_tokens=100,
    )
    assert "gemini_ok" in text


@pytest.mark.asyncio
async def test_google_genai_with_base_url_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """When LLM_BASE_URL is not set (defaulting to openai.com), Google GenAI still uses Google API."""
    captured_url: str = ""

    async def handler(url: str, *, headers: dict[str, str], json: dict[str, Any]) -> httpx.Response:
        nonlocal captured_url
        captured_url = url
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": '{"answer":"gemini_unset_ok"}'}]}}]},
        )

    monkeypatch.setattr("app.qa.provider.httpx.AsyncClient", _make_client(handler))
    # Note: _settings() defaults llm_base_url to "https://api.openai.com/v1"
    settings = _settings(llm_provider="google_genai", llm_model="gemini-1.5-flash")
    provider = build_llm_provider(settings)
    assert isinstance(provider, build_llm_provider(settings).__class__)
    text = await provider.generate(
        system_message="sys",
        user_message="user",
        timeout_seconds=5,
        max_output_tokens=100,
    )
    assert "gemini_unset_ok" in text
    assert "generativelanguage.googleapis.com" in captured_url
    assert "api.openai.com" not in captured_url


@pytest.mark.asyncio
async def test_google_genai_with_unexpected_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """When LLM_BASE_URL contains an unexpected host, Google GenAI defaults to Google API."""
    captured_url: str = ""

    async def handler(url: str, *, headers: dict[str, str], json: dict[str, Any]) -> httpx.Response:
        nonlocal captured_url
        captured_url = url
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": '{"answer":"gemini_unexpected_ok"}'}]}}]},
        )

    monkeypatch.setattr("app.qa.provider.httpx.AsyncClient", _make_client(handler))
    settings = _settings(
        llm_provider="google_genai",
        llm_model="gemini-1.5-flash",
        llm_base_url="https://unexpected-proxy.internal/v1",
    )
    provider = build_llm_provider(settings)
    text = await provider.generate(
        system_message="sys",
        user_message="user",
        timeout_seconds=5,
        max_output_tokens=100,
    )
    assert "gemini_unexpected_ok" in text
    assert "generativelanguage.googleapis.com" in captured_url
    assert "unexpected-proxy.internal" not in captured_url


@pytest.mark.asyncio
async def test_openai_compatible_with_valid_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenAI-compatible provider respects custom base URL."""
    captured_url: str = ""

    async def handler(url: str, *, headers: dict[str, str], json: dict[str, Any]) -> httpx.Response:
        nonlocal captured_url
        captured_url = url
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"answer":"openai_custom_ok"}'}}]},
        )

    monkeypatch.setattr("app.qa.provider.httpx.AsyncClient", _make_client(handler))
    settings = _settings(
        llm_provider="openai_compatible",
        llm_base_url="https://api.together.xyz/v1",
    )
    provider = build_llm_provider(settings)
    text = await provider.generate(
        system_message="sys",
        user_message="user",
        timeout_seconds=5,
        max_output_tokens=100,
    )
    assert "openai_custom_ok" in text
    assert captured_url == "https://api.together.xyz/v1/chat/completions"


def test_missing_or_invalid_provider_configuration() -> None:
    """Verify robust error handling for missing or invalid provider configuration."""
    # 1. Missing provider
    with pytest.raises(LLMProviderUnavailable, match="LLM provider is not configured"):
        build_llm_provider(_settings(llm_provider=""))

    # 2. Unsupported provider
    with pytest.raises(LLMProviderUnavailable, match="Unsupported LLM provider"):
        build_llm_provider(_settings(llm_provider="claude_unsupported"))

    # 3. Missing API key
    with pytest.raises(LLMProviderUnavailable, match="LLM API key is not configured"):
        build_llm_provider(_settings(llm_api_key=""))

    # 4. OpenAI-compatible with empty base URL
    with pytest.raises(LLMProviderUnavailable, match="LLM base URL is not configured"):
        build_llm_provider(_settings(llm_provider="openai_compatible", llm_base_url=""))

