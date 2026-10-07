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

