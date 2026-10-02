import json
import pytest
from app.core.config import get_settings
from app.rag.pipeline import execute_graphrag_pipeline
from app.rag.query_analysis import analyze_query
from app.rag.validation import validate_response_groundedness
from app.qa.provider import LLMProvider
from tests.fake_neo4j import FakeNeo4jClient


def _valid_llm_json(answer: str = "According to [1], Article 21 protects life and personal liberty.") -> str:
    return json.dumps(
        {
            "answer": answer,
            "insufficient_evidence": False,
            "citations": [{"marker": 1, "evidence_rank": 1}],
        }
    )


class MockLLMProvider(LLMProvider):
    def __init__(self, answer_text: str | None = None) -> None:
        if answer_text and answer_text.startswith("{"):
            self.answer_text = answer_text
        elif answer_text:
            self.answer_text = _valid_llm_json(answer_text)
        else:
            self.answer_text = _valid_llm_json()
        self.calls = 0

    async def generate(
        self,
        system_message: str,
        user_message: str,
        timeout_seconds: float,
        max_output_tokens: int,
    ) -> str:
        self.calls += 1
        return self.answer_text


@pytest.mark.asyncio
async def test_pipeline_temporal_query_end_to_end(session):
    query = "What did Article 21 protect in 1978?"
    mock_provider = MockLLMProvider("In 1978, the Supreme Court in Maneka Gandhi expanded Article 21.")
    fake_graph = FakeNeo4jClient()
    settings = get_settings()
    
    resp = await execute_graphrag_pipeline(
        session=session,
        graph_client=fake_graph,
        query=query,
        top_k=5,
        settings=settings,
        mode="COMPREHENSIVE",
        provider=mock_provider,
    )
    
    assert resp["temporal"] is not None
    assert resp["temporal"].detected is True
    assert resp["temporal"].target_year == 1978
    assert resp["citation_validation"] is not None
    assert isinstance(resp["temporal"].timeline_events, list)


@pytest.mark.asyncio
async def test_pipeline_non_temporal_query_end_to_end(session):
    query = "What does Article 21 protect?"
    mock_provider = MockLLMProvider("Article 21 protects life and personal liberty.")
    fake_graph = FakeNeo4jClient()
    settings = get_settings()
    
    resp = await execute_graphrag_pipeline(
        session=session,
        graph_client=fake_graph,
        query=query,
        top_k=5,
        settings=settings,
        mode="COMPREHENSIVE",
        provider=mock_provider,
    )
    
    assert resp["temporal"] is not None
    assert resp["temporal"].detected is False
    assert resp["status"] in ("answered", "insufficient_evidence")


def test_validate_response_groundedness_unit():
    qa = analyze_query("What did Article 21 protect in 1978?")
    report = validate_response_groundedness(
        answer="In 1978, Maneka Gandhi expanded Article 21.",
        citations=[],
        query_analysis=qa,
        resolved_version=None,
        insufficient_evidence=False,
    )
    assert report.grounded is True
    assert report.temporal_valid is True
    assert report.citation_valid is True
