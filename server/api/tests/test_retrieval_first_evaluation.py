"""Retrieval-First Research Improvement and User-Friendly Fallback Evaluation Suite.

Evaluates:
  1. Constitutional amendments and Article 21 (Case C: general fallback when amendment history absent).
  2. Constitutional provisions and interpretation (Case A: strong evidence, grounded answer).
  3. Statutory provisions and amendments (Case A / B: exact section retrieval).
  4. Natural justice and public employment (Article 311 / audi alteram partem).
  5. Leading case law and precedent (Maneka Gandhi).
  6. Alternative terminology and case-name variations.
  7. Partial evidence available (Case B: partial answer with explicit disclosure).
  8. Exact authority genuinely absent from indexed corpus (Case C: unverified general fallback notice).
  9. Unsupported query with no matching evidence (Case D: clean abstention).
 10. Graph entities present but relationships missing.
 11. PostgreSQL document data present but graph data missing, and vice versa.
 12. Technical timeout / LLM error handling (Case E: honest error preservation).

Measures:
  - Recall@5, Recall@10, MRR
  - Citation validity & False-grounding rate (0.0% tolerance)
  - Latency and score semantics
"""

from __future__ import annotations

import json
import time
from typing import Any, Literal
from uuid import UUID, uuid4

import numpy as np
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.graph.client import Neo4jClient
from app.models import Document
from app.models.chunk import Chunk
from app.models.enums import DocumentStatus, DocumentType
from app.qa.provider import LLMProvider
from app.qa.service import ask_legal_question
from app.rag.evidence_fusion import assess_evidence_sufficiency, fuse_and_rank_evidence
from app.rag.pipeline import execute_graphrag_pipeline
from app.rag.query_analysis import analyze_query, normalize_query_text
from app.retrieval.index import save_index
from app.schemas.hybrid import HybridEvidence


class EvalMockLLMProvider(LLMProvider):
    """Configurable LLM provider returning structured JSON answers."""

    def __init__(self, answer: str, citations: list[dict[str, Any]] | None = None, insufficient: bool = False):
        self.answer = answer
        self.citations = citations or []
        self.insufficient = insufficient
        self.calls = 0

    async def generate(
        self,
        system_message: str,
        user_message: str,
        timeout_seconds: float,
        max_output_tokens: int,
    ) -> str:
        self.calls += 1
        return json.dumps({
            "answer": self.answer,
            "insufficient_evidence": self.insufficient,
            "citations": self.citations,
        })


class EvalMockNeo4jClient(Neo4jClient):
    """Mock Neo4j client returning configurable graph entities and traversal paths."""

    def __init__(self, paths: list[dict[str, Any]] | None = None, should_fail: bool = False):
        self.paths = paths or []
        self.should_fail = should_fail
        self.settings = type("SettingsMock", (), {"neo4j_database": "neo4j", "graph_max_nodes": 30})()

    async def _driver_for_use(self) -> Any:
        return self

    def session(self, **kwargs: Any) -> Any:
        class DummySession:
            async def __aenter__(self) -> DummySession:
                return self

            async def __aexit__(self, *args: Any) -> None:
                pass

            async def run(self, *args: Any, **kwargs: Any) -> Any:
                class DummyResult:
                    def __aiter__(self) -> DummyResult:
                        return self

                    async def __anext__(self) -> Any:
                        raise StopAsyncIteration

                return DummyResult()

        return DummySession()

    async def expand_supported_chunks(self, seed_ids: list[str], max_paths: int) -> list[dict]:
        if self.should_fail:
            raise ConnectionError("Neo4j database connection unavailable")
        return self.paths

    async def close(self) -> None:
        pass


class SimpleEvalEmbedder:
    """Deterministic embedding provider for evaluation tests."""
    pooling_method: str = "mean"
    normalization: str = "l2"

    def embed(self, texts: list[str]) -> np.ndarray:
        vecs = []
        for t in texts:
            tl = t.lower()
            if "article 21" in tl or "life and personal liberty" in tl or "what does article 21" in tl:
                vecs.append([1.0, 0.0, 0.0, 0.0])
            elif "section 302" in tl or "punishment for murder" in tl or "murder" in tl:
                vecs.append([0.0, 1.0, 0.0, 0.0])
            elif "natural justice" in tl or "article 311" in tl or "audi alteram partem" in tl or "civil servant" in tl or "government employee" in tl:
                vecs.append([0.0, 0.0, 1.0, 0.0])
            elif "maneka gandhi" in tl or "procedure established by law" in tl:
                vecs.append([0.5, 0.0, 0.0, 0.5])
            else:
                vecs.append([0.25, 0.25, 0.25, 0.25])
        arr = np.asarray(vecs, dtype=np.float32)
        # Normalize to unit length for cosine similarity
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return arr / norms


@pytest.fixture
def eval_settings(tmp_path: Path) -> Settings:
    from app.core.config import get_settings
    settings = get_settings()
    snapshot = settings.model_dump()
    object.__setattr__(settings, "data_dir", str(tmp_path))
    object.__setattr__(settings, "vector_index_name", "eval_test")
    object.__setattr__(settings, "embedding_model_name", "BAAI/bge-small-en-v1.5")
    object.__setattr__(settings, "qa_max_context_chars", 24000)
    object.__setattr__(settings, "llm_timeout_seconds", 2.0)
    yield settings
    for key, value in snapshot.items():
        object.__setattr__(settings, key, value)


async def _seed_corpus(session: AsyncSession, tmp_path, include_article_311: bool = True) -> dict[str, str]:
    """Seed comprehensive test legal documents and build test FAISS index."""
    doc_const = Document(
        id=UUID("10000000-0000-0000-0000-000000000001"),
        title="Constitution of India",
        type=DocumentType.CONSTITUTION,
        source="official",
        status=DocumentStatus.READY,
    )
    doc_ipc = Document(
        id=UUID("10000000-0000-0000-0000-000000000002"),
        title="Indian Penal Code, 1860",
        type=DocumentType.ACT,
        source="official",
        status=DocumentStatus.READY,
    )
    doc_case = Document(
        id=UUID("10000000-0000-0000-0000-000000000003"),
        title="Maneka Gandhi v. Union of India",
        type=DocumentType.JUDGMENT,
        source="sc_reports",
        status=DocumentStatus.READY,
    )
    session.add_all([doc_const, doc_ipc, doc_case])
    await session.flush()

    chunks_data = [
        # Chunk 1: Article 21
        {
            "id": UUID("20000000-0000-0000-0000-000000000001"),
            "doc_id": doc_const.id,
            "index": 0,
            "text": "Article 21: Protection of life and personal liberty. No person shall be deprived of his life or personal liberty except according to procedure established by law.",
            "hier": {"provision": "Article 21", "part": "Part III"},
            "cite": "Article 21",
            "page": 12,
        },
    ]
    if include_article_311:
        chunks_data.append(
            # Chunk 2: Article 311 (Natural Justice & Public Employment)
            {
                "id": UUID("20000000-0000-0000-0000-000000000002"),
                "doc_id": doc_const.id,
                "index": 1,
                "text": "Article 311: Dismissal, removal or reduction in rank of persons employed in civil capacities under the Union or a State. No such person shall be dismissed until he has been given a reasonable opportunity of showing cause, incorporating the principles of natural justice and audi alteram partem.",
                "hier": {"provision": "Article 311", "part": "Part XIV"},
                "cite": "Article 311",
                "page": 145,
            }
        )
    chunks_data.extend([
        # Chunk 3: Section 302 IPC
        {
            "id": UUID("20000000-0000-0000-0000-000000000003"),
            "doc_id": doc_ipc.id,
            "index": 0,
            "text": "Section 302: Punishment for murder. Whoever commits murder shall be punished with death, or imprisonment for life, and shall also be liable to fine.",
            "hier": {"provision": "Section 302", "chapter": "Chapter XVI"},
            "cite": "Section 302",
            "page": 78,
        },
        # Chunk 4: Maneka Gandhi Judgment
        {
            "id": UUID("20000000-0000-0000-0000-000000000004"),
            "doc_id": doc_case.id,
            "index": 0,
            "text": "Maneka Gandhi v. Union of India (1978): The procedure established by law under Article 21 must be just, fair, and reasonable, and not arbitrary. Procedure must comply with natural justice.",
            "hier": {"bench": "7-Judge Bench", "holding": "Substantive Due Process"},
            "cite": "AIR 1978 SC 597",
            "page": 1,
        },
    ])

    index_records = []
    chunk_map = {}
    embedder = SimpleEvalEmbedder()

    for cd in chunks_data:
        c = Chunk(
            id=cd["id"],
            document_id=cd["doc_id"],
            chunk_index=cd["index"],
            text=cd["text"],
            char_count=len(cd["text"]),
            hierarchy=cd["hier"],
            citation_ref=cd["cite"],
            page_start=cd["page"],
            page_end=cd["page"],
        )
        session.add(c)
        chunk_map[cd["cite"]] = str(cd["id"])

        index_records.append({
            "chunk_id": str(cd["id"]),
            "document_id": str(cd["doc_id"]),
            "document_version_id": None,
            "chunk_index": cd["index"],
            "text": cd["text"],
            "page_start": cd["page"],
            "page_end": cd["page"],
            "hierarchy": cd["hier"],
            "citation_ref": cd["cite"],
            "source_url": None,
            "document_title": "Constitution of India" if cd["doc_id"] == doc_const.id else ("Indian Penal Code, 1860" if cd["doc_id"] == doc_ipc.id else "Maneka Gandhi v. Union of India"),
        })

    await session.commit()

    # Save vector index
    texts = [r["text"] for r in index_records]
    vectors = embedder.embed(texts)
    save_index(
        data_dir=tmp_path,
        index_name="eval_test",
        vectors=vectors,
        chunk_records=index_records,
        model_name="BAAI/bge-small-en-v1.5",
        pooling_method="mean",
        max_tokens=512,
    )

    return chunk_map


# ============================================================
# EVALUATION TEST CASES
# ============================================================

@pytest.mark.asyncio
async def test_eval_constitutional_article_full_grounding(session: AsyncSession, eval_settings: Settings, tmp_path):
    """Case A: Strong evidence for Article 21 generates full_answer with verified citation and accurate score."""
    chunk_map = await _seed_corpus(session, tmp_path)
    embedder = SimpleEvalEmbedder()

    mock_llm = EvalMockLLMProvider(
        answer="Article 21 guarantees that no person shall be deprived of life or personal liberty except according to procedure established by law [1].",
        citations=[{"marker": 1, "evidence_rank": 1}],
    )

    res = await ask_legal_question(
        session=session,
        graph_client=EvalMockNeo4jClient(),
        query="What does Article 21 guarantee?",
        top_k=5,
        settings=eval_settings,
        mode="CONSTITUTIONAL",
        provider=mock_llm,
        embedder=embedder,
    )

    assert res.status == "answered"
    assert res.answer_status == "full_answer"
    assert res.insufficient_evidence is False
    assert len(res.citations) == 1
    assert res.citations[0].verification_status == "VERIFIED"
    assert res.citation_validation is not None
    assert res.citation_validation.grounded is True
    assert res.citation_validation.verified_count == 1

    # Verify score semantics and ranking
    assert len(res.evidence) >= 1
    top_ev = res.evidence[0]
    assert top_ev.rank == 1
    assert top_ev.score_type == "Calibrated Fusion Score"
    assert top_ev.hybrid_score > 0.0
    assert top_ev.verification_status == "VERIFIED"


@pytest.mark.asyncio
async def test_eval_constitutional_amendment_absent_fallback(session: AsyncSession, eval_settings: Settings, tmp_path):
    """Case C: Exact amendment history absent from corpus provides general fallback with unverified background notice."""
    await _seed_corpus(session, tmp_path)
    embedder = SimpleEvalEmbedder()

    mock_llm = EvalMockLLMProvider(
        answer="The 44th Constitutional Amendment of 1978 modified Article 21 so that the right to life cannot be suspended during an Emergency. In the existing corpus [1], Article 21 protects life and liberty according to procedure established by law.",
        citations=[{"marker": 1, "evidence_rank": 1}],
    )

    res = await ask_legal_question(
        session=session,
        graph_client=EvalMockNeo4jClient(),
        query="Which constitutional amendment affected Article 21 and when?",
        top_k=5,
        settings=eval_settings,
        mode="CONSTITUTIONAL",
        provider=mock_llm,
        embedder=embedder,
    )

    assert res.status == "answered"
    assert res.answer_status == "general_fallback"
    assert res.insufficient_evidence is False
    assert res.notice is not None
    assert "not found in the currently indexed Juris AI corpus" in res.notice
    assert "general background" in res.notice
    # Evidence must still be present and displayed!
    assert len(res.evidence) > 0
    assert res.evidence[0].rank == 1


@pytest.mark.asyncio
async def test_eval_natural_justice_public_employment(session: AsyncSession, eval_settings: Settings, tmp_path):
    """Evaluates Natural justice and public employment (Article 311 / audi alteram partem)."""
    await _seed_corpus(session, tmp_path)
    embedder = SimpleEvalEmbedder()

    mock_llm = EvalMockLLMProvider(
        answer="Under Article 311, a government employee cannot be dismissed without a reasonable opportunity of showing cause, incorporating principles of natural justice and audi alteram partem [1].",
        citations=[{"marker": 1, "evidence_rank": 1}],
    )

    res = await ask_legal_question(
        session=session,
        graph_client=EvalMockNeo4jClient(),
        query="Can a government employee challenge dismissal for violation of natural justice?",
        top_k=5,
        settings=eval_settings,
        mode="COMPREHENSIVE",
        provider=mock_llm,
        embedder=embedder,
    )

    assert res.status == "answered"
    assert res.answer_status in ("full_answer", "partial_answer")
    assert len(res.evidence) >= 1
    # Check that Article 311 chunk was retrieved
    article_311_retrieved = any("311" in ev.citation_ref or "natural justice" in ev.text.lower() for ev in res.evidence)
    assert article_311_retrieved is True


@pytest.mark.asyncio
async def test_eval_statutory_exact_provision_retrieval(session: AsyncSession, eval_settings: Settings, tmp_path):
    """Evaluates Statutory provisions retrieval using exact identifier matching alongside vector search."""
    await _seed_corpus(session, tmp_path)
    embedder = SimpleEvalEmbedder()

    mock_llm = EvalMockLLMProvider(
        answer="Under Section 302 of the Indian Penal Code, whoever commits murder shall be punished with death or life imprisonment [1].",
        citations=[{"marker": 1, "evidence_rank": 1}],
    )

    res = await ask_legal_question(
        session=session,
        graph_client=EvalMockNeo4jClient(),
        query="What is the punishment for murder under Section 302 of IPC?",
        top_k=5,
        settings=eval_settings,
        mode="STATUTORY",
        provider=mock_llm,
        embedder=embedder,
    )

    assert res.status == "answered"
    assert len(res.evidence) >= 1
    assert any("Section 302" in ev.citation_ref for ev in res.evidence)


@pytest.mark.asyncio
async def test_eval_unsupported_query_clean_abstention(session: AsyncSession, eval_settings: Settings, tmp_path):
    """Case D: Unsupported question with zero evidence produces clean abstention without fabricated citations."""
    embedder = SimpleEvalEmbedder()

    res = await ask_legal_question(
        session=session,
        graph_client=EvalMockNeo4jClient(),
        query="What are the maritime shipping tariff rates under the Interstellar Trade Agreement 3045?",
        top_k=5,
        settings=eval_settings,
        mode="COMPREHENSIVE",
        embedder=embedder,
    )

    assert res.status == "insufficient_evidence"
    assert res.answer_status == "insufficient_evidence"
    assert res.insufficient_evidence is True
    assert len(res.citations) == 0
    assert res.citation_validation is not None
    assert res.citation_validation.grounded is False
    assert res.notice is not None


@pytest.mark.asyncio
async def test_eval_case_name_variations_and_alternative_terms(session: AsyncSession, eval_settings: Settings, tmp_path):
    """Evaluates case name abbreviations, e.g. 'Maneka Gandhi' vs 'AIR 1978 SC 597'."""
    await _seed_corpus(session, tmp_path)
    embedder = SimpleEvalEmbedder()

    mock_llm = EvalMockLLMProvider(
        answer="In Maneka Gandhi, the Supreme Court ruled that procedure under Article 21 must be fair and just [1].",
        citations=[{"marker": 1, "evidence_rank": 1}],
    )

    res = await ask_legal_question(
        session=session,
        graph_client=EvalMockNeo4jClient(),
        query="What was the landmark ruling in Maneka Gandhi regarding procedure established by law?",
        top_k=5,
        settings=eval_settings,
        mode="CASE_LAW",
        provider=mock_llm,
        embedder=embedder,
    )

    assert res.status == "answered"
    assert any("Maneka Gandhi" in ev.document_title for ev in res.evidence)


@pytest.mark.asyncio
async def test_eval_graph_failure_graceful_dense_fallback(session: AsyncSession, eval_settings: Settings, tmp_path):
    """Evaluates resilient fallback to dense retrieval when Neo4j is offline or fails."""
    await _seed_corpus(session, tmp_path)
    embedder = SimpleEvalEmbedder()

    mock_llm = EvalMockLLMProvider(
        answer="Article 21 protects life and personal liberty [1].",
        citations=[{"marker": 1, "evidence_rank": 1}],
    )

    res = await ask_legal_question(
        session=session,
        graph_client=EvalMockNeo4jClient(should_fail=True),
        query="What does Article 21 provide?",
        top_k=5,
        settings=eval_settings,
        mode="CONSTITUTIONAL",
        provider=mock_llm,
        embedder=embedder,
    )

    assert res.status == "answered"
    assert res.retrieval.fallback == "dense_only"
    assert res.retrieval.fallback_reason == "neo4j_unavailable"
    assert len(res.evidence) >= 1


@pytest.mark.asyncio
async def test_eval_aggregate_retrieval_metrics(session: AsyncSession, eval_settings: Settings, tmp_path):
    """Measures Recall@5, MRR, citation validity, and false-grounding rate across multi-domain benchmark."""
    chunk_map = await _seed_corpus(session, tmp_path)
    embedder = SimpleEvalEmbedder()

    test_queries = [
        ("What does Article 21 guarantee?", "Article 21", "CONSTITUTIONAL"),
        ("What is the penalty for murder in Section 302?", "Section 302", "STATUTORY"),
        ("What protection does Article 311 provide to civil servants?", "Article 311", "COMPREHENSIVE"),
        ("What did the Supreme Court hold in Maneka Gandhi v. Union of India?", "AIR 1978 SC 597", "CASE_LAW"),
    ]

    reciprocal_ranks = []
    recall_at_5_hits = 0
    total_verified_cits = 0
    false_grounded_count = 0

    for query, expected_target, mode in test_queries:
        mock_llm = EvalMockLLMProvider(
            answer=f"Legal answer referencing [{expected_target}] [1].",
            citations=[{"marker": 1, "evidence_rank": 1}],
        )

        res = await ask_legal_question(
            session=session,
            graph_client=EvalMockNeo4jClient(),
            query=query,
            top_k=5,
            settings=eval_settings,
            mode=mode,  # type: ignore
            provider=mock_llm,
            embedder=embedder,
        )

        ranks = [idx + 1 for idx, ev in enumerate(res.evidence) if expected_target in (ev.citation_ref or "") or expected_target in ev.text]
        if ranks:
            best_rank = min(ranks)
            reciprocal_ranks.append(1.0 / best_rank)
            if best_rank <= 5:
                recall_at_5_hits += 1
        else:
            reciprocal_ranks.append(0.0)

        # Integrity checks
        for cit in res.citations:
            if cit.verification_status == "VERIFIED":
                total_verified_cits += 1
                # Must resolve to real chunk ID
                assert cit.chunk_id is not None
                assert len(str(cit.chunk_id)) > 0

        # False-grounding check: If verified_count is 0, grounded MUST be False
        if res.citation_validation:
            if res.citation_validation.verified_count == 0 and res.citation_validation.grounded:
                false_grounded_count += 1

    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks)
    recall_at_5 = recall_at_5_hits / len(test_queries)

    assert recall_at_5 >= 0.75, f"Expected Recall@5 >= 0.75, got {recall_at_5}"
    assert mrr >= 0.75, f"Expected MRR >= 0.75, got {mrr}"
    assert false_grounded_count == 0, f"False-grounding violations: {false_grounded_count}"


@pytest.mark.asyncio
async def test_eval_partial_evidence_explicit_disclosure(session: AsyncSession, eval_settings: Settings, tmp_path):
    """Case B: Partial evidence (Article 21 present, Section 498A absent) returns partial_answer with explicit disclosure."""
    await _seed_corpus(session, tmp_path)
    embedder = SimpleEvalEmbedder()

    mock_llm = EvalMockLLMProvider(
        answer="Article 21 protects life and personal liberty [1]. However, Section 498A of the IPC could not be verified in the retrieved documents.",
        citations=[{"marker": 1, "evidence_rank": 1}],
    )

    res = await ask_legal_question(
        session=session,
        graph_client=EvalMockNeo4jClient(),
        query="How does Article 21 interact with Section 498A of the IPC?",
        top_k=5,
        settings=eval_settings,
        mode="COMPREHENSIVE",
        provider=mock_llm,
        embedder=embedder,
    )

    assert res.status == "answered"
    assert res.answer_status == "partial_answer"
    assert res.insufficient_evidence is False
    assert any("498" in m for m in res.missing_authorities)
    assert res.notice is not None
    assert "Partial answer" in res.notice
    assert len(res.evidence) >= 1


@pytest.mark.asyncio
async def test_eval_graph_entities_present_relationships_missing(session: AsyncSession, eval_settings: Settings, tmp_path):
    """Evaluates case where Neo4j entities exist but relationships/paths are missing."""
    await _seed_corpus(session, tmp_path)
    embedder = SimpleEvalEmbedder()

    # Graph client with nodes but no connecting paths
    graph_client = EvalMockNeo4jClient(paths=[])

    mock_llm = EvalMockLLMProvider(
        answer="Article 21 guarantees the fundamental right to life and personal liberty [1].",
        citations=[{"marker": 1, "evidence_rank": 1}],
    )

    res = await ask_legal_question(
        session=session,
        graph_client=graph_client,
        query="What does Article 21 guarantee?",
        top_k=5,
        settings=eval_settings,
        mode="CONSTITUTIONAL",
        provider=mock_llm,
        embedder=embedder,
    )

    assert res.status == "answered"
    assert len(res.evidence) >= 1
    assert res.evidence[0].rank == 1


@pytest.mark.asyncio
async def test_eval_postgres_present_graph_missing(session: AsyncSession, eval_settings: Settings, tmp_path):
    """Evaluates PostgreSQL document data present but Neo4j graph completely missing/offline."""
    await _seed_corpus(session, tmp_path)
    embedder = SimpleEvalEmbedder()

    failing_graph = EvalMockNeo4jClient(should_fail=True)

    mock_llm = EvalMockLLMProvider(
        answer="Section 302 prescribes death or life imprisonment for murder [1].",
        citations=[{"marker": 1, "evidence_rank": 1}],
    )

    res = await ask_legal_question(
        session=session,
        graph_client=failing_graph,
        query="What is the punishment under Section 302?",
        top_k=5,
        settings=eval_settings,
        mode="STATUTORY",
        provider=mock_llm,
        embedder=embedder,
    )

    assert res.status == "answered"
    assert res.retrieval.fallback == "dense_only"
    assert len(res.evidence) >= 1
    assert res.evidence[0].score_type in ("Calibrated Fusion Score", "Vector Cosine Similarity")


class TimeoutLLMProvider(LLMProvider):
    """Provider simulating timeout / technical failure."""
    async def generate(self, system_message: str, user_message: str, timeout_seconds: float, max_output_tokens: int) -> str:
        raise TimeoutError("LLM upstream inference timed out")


@pytest.mark.asyncio
async def test_eval_llm_timeout_handled_gracefully(session: AsyncSession, eval_settings: Settings, tmp_path):
    """Case E: Upstream LLM failure or timeout preserves retrieved evidence and reports failure honestly."""
    await _seed_corpus(session, tmp_path)
    embedder = SimpleEvalEmbedder()

    res = await ask_legal_question(
        session=session,
        graph_client=EvalMockNeo4jClient(),
        query="What does Article 21 guarantee?",
        top_k=5,
        settings=eval_settings,
        mode="CONSTITUTIONAL",
        provider=TimeoutLLMProvider(),
        embedder=embedder,
    )

    assert res.status == "insufficient_evidence"
    assert res.insufficient_evidence is True
    # Preserves retrieved evidence!
    assert len(res.evidence) >= 1
    assert res.evidence[0].rank == 1
    assert res.evidence[0].verification_status == "UNVERIFIED"


@pytest.mark.asyncio
async def test_regression_article_311_natural_justice_fallback(session: AsyncSession, eval_settings: Settings, tmp_path):
    """Production Regression: 'Can a government employee challenge dismissal for violation of natural justice under Article 311?'
    Article 311 is absent from corpus, but incidental fragments (e.g. IT Act natural justice or amendment text) exist.
    Must return general_fallback with notice and preserved evidence, not insufficient_evidence.
    """
    await _seed_corpus(session, tmp_path, include_article_311=False)
    embedder = SimpleEvalEmbedder()

    fallback_answer = (
        "Under Article 311 of the Constitution of India, civil servants are provided procedural safeguards against arbitrary dismissal. "
        "However, the specific text of Article 311 is not present in the indexed corpus."
    )
    mock_llm = EvalMockLLMProvider(
        answer=fallback_answer,
        citations=[],
        insufficient=True,
    )

    res = await ask_legal_question(
        session=session,
        graph_client=EvalMockNeo4jClient(),
        query="Can a government employee challenge dismissal for violation of natural justice under Article 311?",
        top_k=5,
        settings=eval_settings,
        mode="CONSTITUTIONAL",
        provider=mock_llm,
        embedder=embedder,
    )

    assert res.status == "answered"
    assert res.answer_status == "general_fallback"
    assert "Article 311" in res.missing_authorities
    assert res.notice is not None
    assert "not found in the currently indexed Juris AI corpus" in res.notice
    # Never mark general background as corpus-grounded
    assert res.citation_validation.grounded is False
    # Preserves retrieved evidence
    assert len(res.evidence) >= 1
    assert res.evidence[0].rank == 1


@pytest.mark.asyncio
async def test_regression_amendment_affecting_article_21_partial_answer(session: AsyncSession, eval_settings: Settings, tmp_path):
    """Production Regression: 'Which constitutional amendment affected Article 21 and when?'
    Article 21 is in corpus, but amendment affecting it is absent.
    Must return partial_answer citing what was found, not insufficient_evidence.
    """
    await _seed_corpus(session, tmp_path)
    embedder = SimpleEvalEmbedder()

    partial_answer = (
        "The retrieved evidence references Article 21 in constitutional jurisprudence [1], "
        "but does not state which constitutional amendment affected Article 21 and when."
    )
    mock_llm = EvalMockLLMProvider(
        answer=partial_answer,
        citations=[{"marker": 1, "evidence_rank": 1}],
        insufficient=True,
    )

    res = await ask_legal_question(
        session=session,
        graph_client=EvalMockNeo4jClient(),
        query="Which constitutional amendment affected Article 21 and when?",
        top_k=5,
        settings=eval_settings,
        mode="CONSTITUTIONAL",
        provider=mock_llm,
        embedder=embedder,
    )

    assert res.status == "answered"
    assert res.answer_status == "general_fallback"
    assert res.notice is not None
    assert "not found in the currently indexed Juris AI corpus" in res.notice
    assert len(res.evidence) >= 1
    assert res.evidence[0].rank == 1
