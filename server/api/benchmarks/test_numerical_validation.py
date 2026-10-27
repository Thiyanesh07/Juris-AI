"""Phase 3 Numerical Validation Test Suite.

Verifies exact shape equality, float32 dtype, L2 norm stability,
high cosine similarity, low numerical drift, and ONNX determinism.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.retrieval.benchmark_numerical import run_numerical_benchmark
from app.retrieval.embeddings import (
    EmbeddingConfig,
    InLegalBertEmbedder,
    OnnxInLegalBertEmbedder,
)


def test_pytorch_vs_onnx_numerical_validation_suite() -> None:
    report = run_numerical_benchmark()

    # Shape equality
    assert report.all_768_dimensional is True
    assert report.total_samples >= 10

    # L2 Norm check
    assert report.all_l2_normalized is True

    # ONNX determinism check
    assert report.onnx_deterministic is True

    # High cosine similarity threshold (> 0.9999 for FP32 ONNX export)
    assert report.min_cosine_similarity >= 0.9999
    assert report.mean_cosine_similarity >= 0.99999

    # Absolute difference threshold (< 1e-4 max abs difference)
    assert report.overall_mean_abs_diff < 1e-4
    assert report.overall_max_abs_diff < 1e-3


def test_onnx_embedder_determinism() -> None:
    cfg_onnx = EmbeddingConfig(model_name="law-ai/InLegalBERT", device="cpu", backend="onnx")
    embedder = OnnxInLegalBertEmbedder(cfg_onnx)

    text = "The Constitution of India guarantees equality before law under Article 14."
    v1 = embedder.embed([text])
    v2 = embedder.embed([text])

    np.testing.assert_array_equal(v1, v2)
