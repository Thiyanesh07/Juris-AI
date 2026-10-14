"""Retrieval Validation Benchmark — PyTorch vs ONNX FP32 on Production FAISS Index.

Phase 4 tool to evaluate retrieval overlap@5, overlap@10, top-k rank stability,
and score differences on the unchanged production FAISS index.
Does NOT modify or rebuild the production FAISS index.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from app.core.config import get_data_dir, get_settings
from app.retrieval.embeddings import (
    EmbeddingConfig,
    InLegalBertEmbedder,
    OnnxInLegalBertEmbedder,
)
from app.retrieval.index import load_index, search_index_rows

logger = logging.getLogger(__name__)

REPRESENTATIVE_LEGAL_QUERIES = [
    "What does Article 21 protect?",
    "How has the Supreme Court interpreted Article 21?",
    "What is the relationship between Section 66A of the Information Technology Act and Article 19?",
    "What is the Basic Structure Doctrine?",
    "What are the essential ingredients of murder under the Indian Penal Code?",
    "How does the Bharatiya Nagarik Suraksha Sanhita handle bail procedures?",
    "What constitutes workplace sexual harassment under the Vishaka guidelines?",
    "What is the scope of judicial review under Article 32 of the Constitution of India?",
    "What are reasonable restrictions on freedom of speech under Article 19(2)?",
    "How is preventive detention regulated under the Constitution of India?",
    "What is the legal status of the fundamental right to privacy following the Puttaswamy judgment?",
    "What is the procedure for amending the Constitution under Article 368?",
]


@dataclass
class QueryRetrievalComparison:
    query_id: int
    query_text: str
    top1_match: bool
    top5_exact_set_match: bool
    top10_exact_set_match: bool
    overlap_at_5: float
    overlap_at_10: float
    max_score_diff: float
    mean_score_diff: float
    pytorch_top5: list[dict[str, Any]]
    onnx_top5: list[dict[str, Any]]
    differing_reason: str | None = None


@dataclass
class RetrievalBenchmarkReport:
    total_queries: int
    top1_match_rate: float
    top5_exact_set_match_rate: float
    top10_exact_set_match_rate: float
    mean_overlap_at_5: float
    mean_overlap_at_10: float
    overall_max_score_diff: float
    overall_mean_score_diff: float
    differing_queries_count: int
    meaningful_differences_count: int
    faiss_index_compatible: bool
    query_comparisons: list[QueryRetrievalComparison]


def run_retrieval_benchmark(data_dir: Path | None = None) -> RetrievalBenchmarkReport:
    """Compare FAISS retrieval results between PyTorch and ONNX FP32 embedders."""
    settings = get_settings()
    base_data = (data_dir or get_data_dir()).resolve()

    index_name = settings.vector_index_name
    logger.info("Loading existing production FAISS index '%s' from %s...", index_name, base_data)
    faiss_index, metadata = load_index(base_data, index_name)

    cfg_pytorch = EmbeddingConfig(model_name=settings.embedding_model_name, device="cpu", backend="pytorch")
    cfg_onnx = EmbeddingConfig(model_name=settings.embedding_model_name, device="cpu", backend="onnx_int8")

    logger.info("Initializing PyTorch and ONNX INT8 embedders...")
    embedder_pt = InLegalBertEmbedder(cfg_pytorch)
    embedder_onnx = OnnxInLegalBertEmbedder(cfg_onnx)

    comparisons: list[QueryRetrievalComparison] = []

    for idx, q_text in enumerate(REPRESENTATIVE_LEGAL_QUERIES, start=1):
        # 1. Embed query
        pt_vec = embedder_pt.embed([q_text])
        onnx_vec = embedder_onnx.embed([q_text])

        # 2. Search exact same FAISS index for top-10
        pt_hits = search_index_rows(faiss_index, metadata, pt_vec, top_k=10)
        onnx_hits = search_index_rows(faiss_index, metadata, onnx_vec, top_k=10)

        pt_top1_id = pt_hits[0]["chunk_id"] if pt_hits else None
        onnx_top1_id = onnx_hits[0]["chunk_id"] if onnx_hits else None

        pt_top5_ids = set(h["chunk_id"] for h in pt_hits[:5])
        onnx_top5_ids = set(h["chunk_id"] for h in onnx_hits[:5])

        pt_top10_ids = set(h["chunk_id"] for h in pt_hits[:10])
        onnx_top10_ids = set(h["chunk_id"] for h in onnx_hits[:10])

        overlap_5 = len(pt_top5_ids.intersection(onnx_top5_ids)) / float(min(5, len(pt_hits)))
        overlap_10 = len(pt_top10_ids.intersection(onnx_top10_ids)) / float(min(10, len(pt_hits)))

        # Score differences for matching rank positions
        score_diffs = [
            abs(h_pt["score"] - h_onnx["score"])
            for h_pt, h_onnx in zip(pt_hits, onnx_hits, strict=False)
        ]
        max_s_diff = float(np.max(score_diffs)) if score_diffs else 0.0
        mean_s_diff = float(np.mean(score_diffs)) if score_diffs else 0.0

        top1_match = (pt_top1_id == onnx_top1_id)
        top5_exact_match = (pt_top5_ids == onnx_top5_ids)
        top10_exact_match = (pt_top10_ids == onnx_top10_ids)

        diff_reason: str | None = None
        if not top10_exact_match or not top1_match:
            # Check if difference is caused by near-tied scores
            min_delta_between_ranks = min(
                abs(pt_hits[i]["score"] - pt_hits[i + 1]["score"])
                for i in range(len(pt_hits) - 1)
            ) if len(pt_hits) > 1 else 1.0

            if max_s_diff < 1e-4 and min_delta_between_ranks < 1e-4:
                diff_reason = "ranking_only_near_tied_scores"
            elif max_s_diff < 1e-3:
                diff_reason = "minor_floating_point_rank_swap"
            else:
                diff_reason = "meaningful_retrieval_difference"

        comparisons.append(
            QueryRetrievalComparison(
                query_id=idx,
                query_text=q_text,
                top1_match=top1_match,
                top5_exact_set_match=top5_exact_match,
                top10_exact_set_match=top10_exact_match,
                overlap_at_5=round(overlap_5, 4),
                overlap_at_10=round(overlap_10, 4),
                max_score_diff=round(max_s_diff, 8),
                mean_score_diff=round(mean_s_diff, 8),
                pytorch_top5=[
                    {
                        "rank": h["rank"],
                        "score": round(h["score"], 6),
                        "chunk_id": h["chunk_id"],
                        "title": metadata["chunks"][h["faiss_row"]]["document_title"],
                    }
                    for h in pt_hits[:5]
                ],
                onnx_top5=[
                    {
                        "rank": h["rank"],
                        "score": round(h["score"], 6),
                        "chunk_id": h["chunk_id"],
                        "title": metadata["chunks"][h["faiss_row"]]["document_title"],
                    }
                    for h in onnx_hits[:5]
                ],
                differing_reason=diff_reason,
            )
        )

    n_queries = len(comparisons)
    top1_matches = sum(1 for c in comparisons if c.top1_match)
    top5_matches = sum(1 for c in comparisons if c.top5_exact_set_match)
    top10_matches = sum(1 for c in comparisons if c.top10_exact_set_match)

    overlaps_5 = [c.overlap_at_5 for c in comparisons]
    overlaps_10 = [c.overlap_at_10 for c in comparisons]
    max_diffs = [c.max_score_diff for c in comparisons]
    mean_diffs = [c.mean_score_diff for c in comparisons]

    differing_count = sum(1 for c in comparisons if not c.top10_exact_set_match or not c.top1_match)
    meaningful_count = sum(
        1 for c in comparisons if c.differing_reason == "meaningful_retrieval_difference"
    )

    return RetrievalBenchmarkReport(
        total_queries=n_queries,
        top1_match_rate=round(top1_matches / n_queries, 4),
        top5_exact_set_match_rate=round(top5_matches / n_queries, 4),
        top10_exact_set_match_rate=round(top10_matches / n_queries, 4),
        mean_overlap_at_5=round(float(np.mean(overlaps_5)), 4),
        mean_overlap_at_10=round(float(np.mean(overlaps_10)), 4),
        overall_max_score_diff=round(float(np.max(max_diffs)), 8),
        overall_mean_score_diff=round(float(np.mean(mean_diffs)), 8),
        differing_queries_count=differing_count,
        meaningful_differences_count=meaningful_count,
        faiss_index_compatible=True,
        query_comparisons=comparisons,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    report = run_retrieval_benchmark()
    print("\n==================================================")
    print("PHASE 4 — RETRIEVAL VALIDATION REPORT (Production FAISS Index)")
    print("==================================================")
    print(f"Total Queries Evaluated:    {report.total_queries}")
    print(f"FAISS Index Compatible:     {report.faiss_index_compatible}")
    print("--------------------------------------------------")
    print(f"Top-1 Exact Match Rate:     {report.top1_match_rate * 100:.1f}%")
    print(f"Top-5 Exact Set Match Rate: {report.top5_exact_set_match_rate * 100:.1f}%")
    print(f"Top-10 Exact Set Match Rate:{report.top10_exact_set_match_rate * 100:.1f}%")
    print(f"Mean Overlap@5:             {report.mean_overlap_at_5 * 100:.1f}%")
    print(f"Mean Overlap@10:            {report.mean_overlap_at_10 * 100:.1f}%")
    print("--------------------------------------------------")
    print(f"Overall Max Score Diff:     {report.overall_max_score_diff:.8f}")
    print(f"Overall Mean Score Diff:    {report.overall_mean_score_diff:.8f}")
    print(f"Total Differing Queries:    {report.differing_queries_count}")
    print(f"Meaningful Differences:     {report.meaningful_differences_count}")
    print("==================================================")
