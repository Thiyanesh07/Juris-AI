"""Service-level tests for legal QA orchestration."""

from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.qa.provider import LLMProviderTimeout, LLMProviderUnavailable
from app.qa.service import QAInvalidModelOutputError, ask_legal_question, effective_retrieval_top_k
from app.retrieval.embeddings import EmbeddingError
from tests.test_retrieval import _records


class FakeGraphClient:
    async def close(self) -> None:
        return None


class FakeLLMProvider:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls = 0
        self.user_messages: list[str] = []

    async def generate(
        self,
        *,
        system_message: str,
        user_message: str,
        timeout_seconds: float,
        max_output_tokens: int,
    ) -> str:
        _ = (system_message, timeout_seconds, max_output_tokens)
        self.user_messages.append(user_message)
        if self.calls >= len(self.responses):
            raise RuntimeError("No more fake LLM responses")
        text = self.responses[self.calls]
        self.calls += 1
        return text


def _valid_llm_json() -> str:
    return json.dumps(
        {
            "answer": "Equality is guaranteed [1].",
            "insufficient_evidence": False,
            "citations": [{"marker": 1, "evidence_rank": 1}],
        }
    )


def _hybrid_result(
    *,
    results: list[dict[str, Any]] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    if results is None:
        record = _records()[0]
        results = [
            {
                **record,
                "rank": 1,
                "dense_score": 0.95,
                "graph_score": 0.0,
                "hybrid_score": 0.665,
                "dense_rank": 1,
                "graph_rank": None,
                "dense_matched": True,
                "evidence_sources": ["dense"],
                "graph_context": None,
            }
        ]
    payload: dict[str, Any] = {
        "query": "equality",
        "mode": "hybrid",
        "fallback": None,
        "fallback_reason": None,
        "weights": {"vector": 0.7, "graph": 0.3},
        "score_type": "hybrid",
        "warnings": [],
        "results": results,
    }
    payload.update(overrides)
    return payload


def _qa_settings(**overrides: object) -> Settings:
    settings = get_settings()
    settings.llm_api_key = "test-key"
    settings.llm_provider = "openai_compatible"
    for key, value in overrides.items():
        setattr(settings, key, value)
    return settings


@pytest.mark.asyncio
async def test_successful_retrieval_and_generation(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _qa_settings()

    async def fake_hybrid(*_args, **_kwargs):
        return _hybrid_result()

    monkeypatch.setattr("app.qa.service.hybrid_retrieve", fake_hybrid)
    response = await ask_legal_question(
        session,
        FakeGraphClient(),
        "equality",
        3,
        settings,
        provider=FakeLLMProvider([_valid_llm_json()]),
    )
    assert response.status == "answered"
    assert response.llm_called is True
    assert response.citations[0].citation_ref == "Article 14"
    assert response.evidence[0].rank == 1


@pytest.mark.asyncio
async def test_empty_retrieval_skips_llm(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _qa_settings()
    provider = FakeLLMProvider([_valid_llm_json()])

    async def fake_hybrid(*_args, **_kwargs):
        return _hybrid_result(results=[])

    monkeypatch.setattr("app.qa.service.hybrid_retrieve", fake_hybrid)
    response = await ask_legal_question(
        session,
        FakeGraphClient(),
        "equality",
        3,
        settings,
        provider=provider,
    )
    assert response.status == "insufficient_evidence"
    assert response.llm_called is False
    assert response.answer is None
    assert response.citations == []
    assert response.evidence == []
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_retrieval_exception_propagates(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _qa_settings()

    async def fake_hybrid(*_args, **_kwargs):
        raise EmbeddingError("embed failed")

    monkeypatch.setattr("app.qa.service.hybrid_retrieve", fake_hybrid)
    with pytest.raises(EmbeddingError):
        await ask_legal_question(
            session,
            FakeGraphClient(),
            "equality",
            3,
            settings,
            provider=FakeLLMProvider([_valid_llm_json()]),
        )


@pytest.mark.asyncio
async def test_dense_only_fallback_still_generates(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _qa_settings()

    async def fake_hybrid(*_args, **_kwargs):
        return _hybrid_result(
            fallback="dense_only",
            fallback_reason="neo4j_unavailable",
        )

    monkeypatch.setattr("app.qa.service.hybrid_retrieve", fake_hybrid)
    response = await ask_legal_question(
        session,
        FakeGraphClient(),
        "equality",
        3,
        settings,
        provider=FakeLLMProvider([_valid_llm_json()]),
    )
    assert response.llm_called is True
    assert response.retrieval.fallback == "dense_only"
    assert response.retrieval.fallback_reason == "neo4j_unavailable"


@pytest.mark.asyncio
async def test_provider_timeout_propagates(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _qa_settings()

    class TimeoutProvider:
        async def generate(self, **_kwargs: Any) -> str:
            raise LLMProviderTimeout("timeout")

    async def fake_hybrid(*_args, **_kwargs):
        return _hybrid_result()

    monkeypatch.setattr("app.qa.service.hybrid_retrieve", fake_hybrid)
    with pytest.raises(LLMProviderTimeout):
        await ask_legal_question(
            session,
            FakeGraphClient(),
            "equality",
            3,
            settings,
            provider=TimeoutProvider(),
        )


async def _async_return(value: Any) -> Any:
    return value


@pytest.mark.asyncio
async def test_empty_retrieval_preserves_warnings(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _qa_settings()
    provider = FakeLLMProvider([_valid_llm_json()])

    async def fake_hybrid(*_args, **_kwargs):
        return _hybrid_result(
            results=[],
            warnings=["graph skipped"],
            fallback="dense_only",
            fallback_reason="neo4j_unavailable",
        )

    monkeypatch.setattr("app.qa.service.hybrid_retrieve", fake_hybrid)
    response = await ask_legal_question(
        session,
        FakeGraphClient(),
        "equality",
        3,
        settings,
        provider=provider,
    )
    assert response.llm_called is False
    assert response.retrieval.warnings == ["graph skipped"]
    assert response.retrieval.fallback == "dense_only"
    assert response.retrieval.fallback_reason == "neo4j_unavailable"


@pytest.mark.asyncio
async def test_missing_api_key_allows_empty_retrieval(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.qa.provider import build_llm_provider

    settings = _qa_settings(llm_api_key="")
    monkeypatch.setattr("app.qa.service.build_llm_provider", build_llm_provider)

    async def fake_hybrid(*_args, **_kwargs):
        return _hybrid_result(results=[])

    monkeypatch.setattr("app.qa.service.hybrid_retrieve", fake_hybrid)
    response = await ask_legal_question(
        session,
        FakeGraphClient(),
        "equality",
        3,
        settings,
    )
    assert response.status == "insufficient_evidence"
    assert response.llm_called is False


@pytest.mark.asyncio
async def test_missing_api_key_fails_after_evidence_retrieval(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.qa.provider import build_llm_provider

    settings = _qa_settings(llm_api_key="")
    calls = {"count": 0}
    monkeypatch.setattr("app.qa.service.build_llm_provider", build_llm_provider)

    async def fake_hybrid(*_args, **_kwargs):
        calls["count"] += 1
        return _hybrid_result()

    monkeypatch.setattr("app.qa.service.hybrid_retrieve", fake_hybrid)
    with pytest.raises(LLMProviderUnavailable):
        await ask_legal_question(
            session,
            FakeGraphClient(),
            "equality",
            3,
            settings,
        )
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_evidence_remains_rank_ordered(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _qa_settings()
    records = _records()
    results = []
    for index, record in enumerate(records, start=1):
        results.append(
            {
                **record,
                "rank": index,
                "dense_score": 0.9,
                "graph_score": 0.0,
                "hybrid_score": 0.63,
                "dense_rank": index,
                "graph_rank": None,
                "dense_matched": True,
                "evidence_sources": ["dense"],
                "graph_context": None,
            }
        )

    async def fake_hybrid(*_args, **_kwargs):
        return _hybrid_result(results=results)

    monkeypatch.setattr("app.qa.service.hybrid_retrieve", fake_hybrid)
    response = await ask_legal_question(
        session,
        FakeGraphClient(),
        "equality",
        5,
        settings,
        provider=FakeLLMProvider([_valid_llm_json()]),
    )
    assert [item.rank for item in response.evidence] == [1, 2]


@pytest.mark.asyncio
async def test_context_budget_drops_items(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _qa_settings(qa_max_context_chars=300, qa_max_chunk_chars=4000)
    records = _records()
    results = []
    for index, record in enumerate(records, start=1):
        results.append(
            {
                **record,
                "text": record["text"] * 30,
                "rank": index,
                "dense_score": 0.9,
                "graph_score": 0.0,
                "hybrid_score": 0.63,
                "dense_rank": index,
                "graph_rank": None,
                "dense_matched": True,
                "evidence_sources": ["dense"],
                "graph_context": None,
            }
        )

    monkeypatch.setattr(
        "app.qa.service.hybrid_retrieve",
        lambda *a, **k: _async_return(_hybrid_result(results=results)),
    )
    response = await ask_legal_question(
        session,
        FakeGraphClient(),
        "equality",
        5,
        settings,
        provider=FakeLLMProvider([_valid_llm_json()]),
    )
    assert response.retrieval.evidence_dropped_for_context >= 1
    assert len(response.evidence) < len(results)


@pytest.mark.asyncio
async def test_long_chunk_truncation(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _qa_settings(qa_max_chunk_chars=50)
    record = _records()[0]
    long_text = "word " * 40
    result = _hybrid_result(
        results=[
            {
                **record,
                "text": long_text,
                "rank": 1,
                "dense_score": 0.9,
                "graph_score": 0.0,
                "hybrid_score": 0.63,
                "dense_rank": 1,
                "graph_rank": None,
                "dense_matched": True,
                "evidence_sources": ["dense"],
                "graph_context": None,
            }
        ]
    )
    monkeypatch.setattr(
        "app.qa.service.hybrid_retrieve",
        lambda *a, **k: _async_return(result),
    )
    response = await ask_legal_question(
        session,
        FakeGraphClient(),
        "equality",
        3,
        settings,
        provider=FakeLLMProvider([_valid_llm_json()]),
    )
    assert "[truncated]" in response.evidence[0].text


@pytest.mark.asyncio
async def test_no_second_retrieval(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _qa_settings()
    calls = {"count": 0}

    async def fake_hybrid(*_args, **_kwargs):
        calls["count"] += 1
        return _hybrid_result()

    monkeypatch.setattr("app.qa.service.hybrid_retrieve", fake_hybrid)
    bad = json.dumps({"answer": "missing marker", "insufficient_evidence": False, "citations": []})
    provider = FakeLLMProvider([bad, _valid_llm_json()])
    await ask_legal_question(
        session,
        FakeGraphClient(),
        "equality",
        3,
        settings,
        provider=provider,
    )
    assert calls["count"] == 1
    assert provider.calls == 2
    assert "BEGIN UNTRUSTED LEGAL EVIDENCE" in provider.user_messages[1]
    assert "At least one citation is required" in provider.user_messages[1]


@pytest.mark.asyncio
async def test_invalid_output_after_retry_raises(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _qa_settings()
    monkeypatch.setattr(
        "app.qa.service.hybrid_retrieve",
        lambda *a, **k: _async_return(_hybrid_result()),
    )
    bad = json.dumps({"answer": "missing marker", "insufficient_evidence": False, "citations": []})
    with pytest.raises(QAInvalidModelOutputError):
        await ask_legal_question(
            session,
            FakeGraphClient(),
            "equality",
            3,
            settings,
            provider=FakeLLMProvider([bad, bad]),
        )


def test_effective_top_k_respects_qa_cap() -> None:
    settings = _qa_settings(qa_max_evidence=3, retrieval_default_top_k=5)
    assert effective_retrieval_top_k(settings, None) == 3
    assert effective_retrieval_top_k(settings, 10) == 3
