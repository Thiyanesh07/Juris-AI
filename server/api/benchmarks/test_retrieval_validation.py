"""Phase 4 Retrieval Validation Test Suite.

Verifies that ONNX FP32 embedder achieves high retrieval overlap
(Top-1 match rate, Overlap@5, Overlap@10) on the production FAISS index
without requiring index regeneration.
"""

from __future__ import annotations

import pytest

from app.retrieval.benchmark_retrieval import run_retrieval_benchmark


def test_pytorch_vs_onnx_retrieval_validation_suite() -> None:
    report = run_retrieval_benchmark()

    # Index compatibility
    assert report.faiss_index_compatible is True
    assert report.total_queries >= 4

    # Top-1 match rate >= 90%
    assert report.top1_match_rate >= 0.90

    # Overlap@5 and Overlap@10 >= 95%
    assert report.mean_overlap_at_5 >= 0.95
    assert report.mean_overlap_at_10 >= 0.95

    # Zero meaningful retrieval differences
    assert report.meaningful_differences_count == 0

    # Score differences bounded by 1e-4
    assert report.overall_mean_score_diff < 1e-4
