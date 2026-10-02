"""Phase 14 Retrieval Evaluation module.

Evaluates and compares Vector-only, Graph-only, and Hybrid retrieval across
the six required end-to-end legal queries.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.graph.client import Neo4jClient
from app.qa.service import ask_legal_question
from app.qa.provider import LLMProvider

logger = logging.getLogger(__name__)

EVALUATION_QUERIES = [
    "What does Article 21 protect?",
    "How has the Supreme Court interpreted Article 21?",
    "What is the relationship between Section 66A of the Information Technology Act and Article 19?",
    "What is the Basic Structure Doctrine?",
    "How did Maneka Gandhi change the interpretation of Article 21?",
    "How does Shreya Singhal relate Section 66A to freedom of speech?",
]


async def evaluate_retrieval_strategies(
    session: AsyncSession,
    graph_client: Neo4jClient,
    settings: Settings,
    *,
    provider: LLMProvider | None = None,
    embedder: Any | None = None,
) -> dict[str, Any]:
    """Run comparative evaluation of Vector-only, Graph-only, and Hybrid strategies."""
    results_by_query: list[dict[str, Any]] = []
    strategies = ["vector_only", "graph_only", "hybrid"]

    for q_idx, q_text in enumerate(EVALUATION_QUERIES, start=1):
        query_metrics: dict[str, Any] = {"query_id": f"QUERY_{q_idx}", "query": q_text, "strategies": {}}

        for strat in strategies:
            start_t = time.perf_counter()
            try:
                qa_res = await ask_legal_question(
                    session=session,
                    graph_client=graph_client,
                    query=q_text,
                    top_k=5,
                    settings=settings,
                    retrieval_strategy=strat, # type: ignore
                    provider=provider,
                    embedder=embedder,
                )
                latency_ms = int((time.perf_counter() - start_t) * 1000)

                ev_count = len(qa_res.evidence)
                cit_count = len(qa_res.citations)
                doc_titles = {e.document_title for e in qa_res.evidence}

                query_metrics["strategies"][strat] = {
                    "latency_ms": latency_ms,
                    "status": qa_res.status,
                    "evidence_count": ev_count,
                    "citation_count": cit_count,
                    "source_diversity": len(doc_titles),
                    "grounded": not qa_res.insufficient_evidence,
                    "nodes_retrieved": len(qa_res.graph.nodes) if qa_res.graph else 0,
                }
            except Exception as exc:
                latency_ms = int((time.perf_counter() - start_t) * 1000)
                query_metrics["strategies"][strat] = {
                    "latency_ms": latency_ms,
                    "status": "error",
                    "error": str(exc),
                    "grounded": False,
                }

        results_by_query.append(query_metrics)

    return {
        "evaluation_count": len(EVALUATION_QUERIES),
        "queries": results_by_query,
    }
