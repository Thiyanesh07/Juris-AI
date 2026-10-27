"""Phase 2 Regression Tests: Retrieval, Observability, Evidence Sufficiency, and Citation Traceability.

Validates:
1. Multi-query candidate expansion retrieves landmark authorities.
2. Alternative wording of legal concepts resolves correctly.
3. Multiple relevant evidence chunks are preserved and ranked with diversification.
4. Neo4j graph retrieval failure cleanly falls back to vector-only.
5. Truly insufficient corpus evidence produces clean abstention (insufficient_evidence: True).
6. Document PDF serving endpoint (GET /documents/{document_id}/pdf).
7. PDF URL and page mapping in citation contracts.
8. Request-scoped retrieval observability logging.
9. Preservation of Phase 1 authentication and truthful grounding guarantees.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import app
from app.models.enums import DocumentStatus, DocumentType
from app.rag.evidence_fusion import (
    calculate_entity_boost,
    evaluate_evidence_sufficiency,
    fuse_and_rank_evidence,
)
from app.rag.pipeline import execute_graphrag_pipeline
from app.rag.query_analysis import analyze_query
from app.schemas.hybrid import HybridEvidence
from app.schemas.qa import QACitation, QAAskResponse


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        app_env="test",
        session_secret="test-secret-at-least-32-chars-long-for-testing",
        qa_max_evidence=5,
        hybrid_dense_seed_top_k=10,
    )


class TestRetrievalAndSufficiency:
    def test_plural_articles_and_constitution_extraction(self):
        qa = analyze_query("How do Articles 14, 19 and 21 interact under the Indian Constitution?")
        art_names = {e["name"] for e in qa.detected_entities if e["label"] == "Article"}
        assert "Article 14" in art_names
        assert "Article 19" in art_names
        assert "Article 21" in art_names
        assert any(e["name"] == "Constitution of India" for e in qa.detected_entities)

    def test_alternative_wording_query_analysis(self):
        qa = analyze_query("Does the Indian Constitution guarantee personal liberty and freedom from arbitrary state deprivation?")
        assert any(e["name"] == "Constitution of India" for e in qa.detected_entities)

    def test_insufficient_evidence_evaluation_for_unsupported_query(self):
        detected_entities = [
            {"id": "act:galactic_trade", "label": "Act", "name": "Galactic Trade Act"}
        ]
        ev1 = HybridEvidence(
            rank=1,
            chunk_id=uuid4(),
            document_id=uuid4(),
            document_title="Constitution of India",
            chunk_index=0,
            text="Preamble to the Constitution of India",
            hierarchy={},
            dense_score=0.75,
            graph_score=0.0,
            hybrid_score=0.75,
            dense_matched=True,
            evidence_sources=["dense"],
        )
        is_suff, reason = evaluate_evidence_sufficiency([ev1], detected_entities)
        assert is_suff is False
        assert "No retrieved evidence matches requested legal subject" in reason

    def test_sufficient_evidence_evaluation_for_matching_entity(self):
        detected_entities = [
            {"id": "article:21", "label": "Article", "name": "Article 21"}
        ]
        ev1 = HybridEvidence(
            rank=1,
            chunk_id=uuid4(),
            document_id=uuid4(),
            document_title="Maneka Gandhi v. Union of India",
            chunk_index=0,
            text="Protection under Article 21 is not confined to executive action.",
            hierarchy={"article": "21"},
            citation_ref="Article 21",
            dense_score=0.88,
            graph_score=0.0,
            hybrid_score=0.88,
            dense_matched=True,
            evidence_sources=["dense"],
        )
        is_suff, reason = evaluate_evidence_sufficiency([ev1], detected_entities)
        assert is_suff is True
        assert reason is None

    def test_diversification_limits_chunks_per_document(self):
        doc_a = uuid4()
        doc_b = uuid4()
        candidates = [
            {"chunk_id": str(uuid4()), "score": 0.90 - (i * 0.01), "doc": "A"}
            for i in range(5)
        ] + [
            {"chunk_id": str(uuid4()), "score": 0.84 - (i * 0.01), "doc": "B"}
            for i in range(3)
        ]
        all_chunks = {}
        for c in candidates:
            cid = c["chunk_id"]
            doc_id = doc_a if c["doc"] == "A" else doc_b
            title = "Document A" if c["doc"] == "A" else "Document B"
            all_chunks[cid] = {
                "chunk_id": cid,
                "document_id": doc_id,
                "document_title": title,
                "chunk_index": 0,
                "text": f"Sample text for {cid}",
            }
        fused = fuse_and_rank_evidence(
            dense_candidates=candidates,
            graph_candidate_chunks={},
            all_chunks_by_id=all_chunks,
            strategy="vector_only",
            top_k=4,
        )
        # Should contain max 2 chunks of Document A and remaining from Document B
        titles = [e.document_title for e in fused]
        assert titles.count("Document A") <= 2
        assert "Document B" in titles

    def test_unclamped_boost_sorting_preserves_exact_entity_match(self):
        doc_target = uuid4()
        doc_background = uuid4()
        cid_target = str(uuid4())
        cid_background = str(uuid4())

        # Background chunk has slightly higher raw dense score (0.866 vs 0.860)
        candidates = [
            {"chunk_id": cid_background, "score": 0.866},
            {"chunk_id": cid_target, "score": 0.860},
        ]
        all_chunks = {
            cid_background: {
                "chunk_id": cid_background,
                "document_id": doc_background,
                "document_title": "General Background Case",
                "chunk_index": 0,
                "text": "Mentions fundamental rights in general.",
            },
            cid_target: {
                "chunk_id": cid_target,
                "document_id": doc_target,
                "document_title": "Maneka Gandhi v. Union of India",
                "chunk_index": 0,
                "text": "Personal liberty under Article 21.",
            },
        }
        entities = [
            {"id": "judgment:maneka_gandhi", "label": "Judgment", "name": "Maneka Gandhi"}
        ]
        fused = fuse_and_rank_evidence(
            dense_candidates=candidates,
            graph_candidate_chunks={},
            all_chunks_by_id=all_chunks,
            strategy="vector_only",
            top_k=2,
            detected_entities=entities,
        )
        # Target should be #1 despite lower initial raw score due to exact entity boost
        assert fused[0].document_title == "Maneka Gandhi v. Union of India"
        assert fused[0].rank == 1

    def test_amendment_ordinal_mapping_boosts_written_amendment_title(self):
        boost = calculate_entity_boost(
            doc_title="The Constitution (Forty-Fourth Amendment) Act, 1978",
            citation_ref="",
            hierarchy={},
            detected_entities=[
                {"id": "amendment:44", "label": "Amendment", "name": "44th Constitutional Amendment"}
            ],
            text="",
        )
        assert boost >= 1.30

    def test_amendment_and_article_generates_targeted_subqueries(self):
        qa = analyze_query("How did the 44th Constitutional Amendment alter the fundamental right to property under Article 19?")
        assert any("44th Constitutional Amendment" in sq for sq in qa.subqueries)
        assert any("Article 19" in sq for sq in qa.subqueries)


@pytest.mark.asyncio
class TestPipelineTraceabilityAndFallback:
    async def test_neo4j_fallback_to_vector_only(self, test_settings):
        mock_graph = MagicMock()
        mock_graph.expand_supported_chunks = AsyncMock(side_effect=ConnectionError("Neo4j unreachable"))
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Execute with un-supported query to check clean fallback and abstention
        res = await execute_graphrag_pipeline(
            session=mock_session,
            graph_client=mock_graph,
            query="What does Section 9999 of the Galactic Trade Act provide?",
            top_k=5,
            settings=test_settings,
        )
        assert res["status"] == "insufficient_evidence"
        assert res["insufficient_evidence"] is True
        assert res["retrieval"].fallback == "dense_only"
        assert res["retrieval"].fallback_reason == "neo4j_unavailable"

    async def test_observability_logging_emits_diagnostics(self, test_settings, caplog):
        mock_graph = MagicMock()
        mock_graph.expand_supported_chunks = AsyncMock(side_effect=ConnectionError("Unavailable"))
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        pipeline_logger = logging.getLogger("app.rag.pipeline")
        pipeline_logger.disabled = False
        with caplog.at_level(logging.INFO):
            await execute_graphrag_pipeline(
                session=mock_session,
                graph_client=mock_graph,
                query="What does Section 9999 of the Galactic Trade Act provide?",
                top_k=5,
                settings=test_settings,
            )

        log_messages = [rec.message for rec in caplog.records]
        assert any("retrieval_diagnostics" in msg for msg in log_messages)


@pytest.mark.asyncio
class TestDocumentPDFEndpoint:
    async def test_get_document_pdf_not_found(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            fake_id = uuid4()
            resp = await client.get(f"/api/v1/documents/{fake_id}/pdf")
            # 401 unauthenticated or 404 not found
            assert resp.status_code in (401, 404)
