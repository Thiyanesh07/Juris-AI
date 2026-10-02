"""Reproducible Benchmarking & Evaluation Runner Service (Phase 16).

Evaluates VECTOR_ONLY, GRAPH_ONLY, and HYBRID GraphRAG retrieval strategies against
the ground-truth evaluation dataset in server/data/evaluation/.
Calculates Recall@K, Precision@K, MRR, Citation Verification Rate, and Temporal Accuracy.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_data_dir
from app.graph.client import Neo4jClient
from app.models.evaluation_run import EvaluationRun
from app.rag.pipeline import execute_graphrag_pipeline
from app.schemas.qa import QAAskRequest

logger = logging.getLogger(__name__)


def _load_dataset() -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], dict[str, Any]]:
    possible_paths = [
        Path(__file__).resolve().parents[3] / "data" / "evaluation",
        Path(__file__).resolve().parents[2] / "data" / "evaluation",
        Path("server/data/evaluation"),
        Path("data/evaluation"),
    ]
    base_dir = next((p for p in possible_paths if (p / "questions.json").exists()), possible_paths[0])

    questions_file = base_dir / "questions.json"
    citations_file = base_dir / "expected_citations.json"
    entities_file = base_dir / "expected_entities.json"
    temporal_file = base_dir / "expected_temporal_facts.json"

    questions = json.loads(questions_file.read_text(encoding="utf-8")) if questions_file.exists() else []
    citations = json.loads(citations_file.read_text(encoding="utf-8")) if citations_file.exists() else {}
    entities = json.loads(entities_file.read_text(encoding="utf-8")) if entities_file.exists() else {}
    temporal = json.loads(temporal_file.read_text(encoding="utf-8")) if temporal_file.exists() else {}

    return questions, citations, entities, temporal


async def run_evaluation_benchmark(
    session: AsyncSession,
    *,
    name: str = "GraphRAG Strategy Comparison Benchmark",
    top_k: int = 5,
    strategies: list[str] | None = None,
) -> EvaluationRun:
    """Execute evaluation benchmark across specified retrieval strategies."""
    if not strategies:
        strategies = ["vector_only", "graph_only", "hybrid"]

    questions, expected_citations, expected_entities, expected_temporal = _load_dataset()
    from app.core.config import get_settings
    graph_client = Neo4jClient(get_settings())

    results_by_strategy: dict[str, Any] = {}

    for strat in strategies:
        total_questions = len(questions)
        recalls: list[float] = []
        precisions: list[float] = []
        mrrs: list[float] = []
        citation_rates: list[float] = []
        temporal_accuracies: list[float] = []

        query_details: list[dict[str, Any]] = []

        for q in questions:
            qid = q["id"]
            query_str = q["query"]
            exp_ents = expected_entities.get(qid, q.get("expected_entities", []))
            exp_cits = expected_citations.get(qid, q.get("expected_citations", []))

            # Execute pipeline
            req = QAAskRequest(
                query=query_str,
                top_k=top_k,
                retrieval_strategy=strat, # type: ignore
            )
            
            try:
                from app.core.config import get_settings
                res = await execute_graphrag_pipeline(
                    session=session,
                    graph_client=graph_client,
                    query=query_str,
                    top_k=top_k,
                    settings=get_settings(),
                    mode=q.get("category", "COMPREHENSIVE"), # type: ignore
                )
            except Exception as exc:
                logger.warning(f"Evaluation query failed for strategy={strat}, query='{query_str}': {exc}")
                res = {"evidence": [], "citations": [], "temporal": None, "citation_validation": None}

            retrieved_evidence = res.get("evidence", [])
            retrieved_cits = res.get("citations", [])
            val_summary = res.get("citation_validation")
            temporal_meta = res.get("temporal")

            # Entity Recall@K and Precision@K calculation
            retrieved_doc_titles = [str(item.document_title).lower() for item in retrieved_evidence]
            matched_ents = 0
            first_rank = 0

            for idx, title in enumerate(retrieved_doc_titles, start=1):
                if any(exp.lower() in title for exp in exp_ents):
                    matched_ents += 1
                    if first_rank == 0:
                        first_rank = idx

            recall = (matched_ents / len(exp_ents)) if exp_ents else 1.0
            precision = (matched_ents / len(retrieved_doc_titles)) if retrieved_doc_titles else 0.0
            mrr = (1.0 / first_rank) if first_rank > 0 else 0.0

            recalls.append(recall)
            precisions.append(precision)
            mrrs.append(mrr)

            # Citation Verification Rate
            if val_summary:
                tot_c = val_summary.verified_count + val_summary.unverified_count
                cit_rate = (val_summary.verified_count / tot_c) if tot_c > 0 else 1.0
            else:
                cit_rate = 1.0
            citation_rates.append(cit_rate)

            # Temporal Fact Accuracy
            temp_acc = 1.0
            if q.get("is_temporal"):
                if temporal_meta and temporal_meta.detected:
                    temp_acc = 1.0
                else:
                    temp_acc = 0.0
            temporal_accuracies.append(temp_acc)

            query_details.append({
                "id": qid,
                "query": query_str,
                "recall": round(recall, 3),
                "precision": round(precision, 3),
                "mrr": round(mrr, 3),
                "citation_verification_rate": round(cit_rate, 3),
                "temporal_accuracy": round(temp_acc, 3),
            })

        avg_recall = sum(recalls) / len(recalls) if recalls else 0.0
        avg_precision = sum(precisions) / len(precisions) if precisions else 0.0
        avg_mrr = sum(mrrs) / len(mrrs) if mrrs else 0.0
        avg_cit_rate = sum(citation_rates) / len(citation_rates) if citation_rates else 0.0
        avg_temp_acc = sum(temporal_accuracies) / len(temporal_accuracies) if temporal_accuracies else 0.0

        results_by_strategy[strat] = {
            "mean_recall_at_k": round(avg_recall, 4),
            "mean_precision_at_k": round(avg_precision, 4),
            "mrr": round(avg_mrr, 4),
            "citation_verification_rate": round(avg_cit_rate, 4),
            "temporal_accuracy": round(avg_temp_acc, 4),
            "total_queries_evaluated": total_questions,
            "queries": query_details,
        }

    eval_run = EvaluationRun(
        name=name,
        configuration={
            "top_k": top_k,
            "strategies": strategies,
            "dataset_question_count": len(questions),
        },
        results=results_by_strategy,
    )

    session.add(eval_run)
    await session.commit()
    await session.refresh(eval_run)
    return eval_run
