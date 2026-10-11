"""Unit tests for Phase 2 ONNX InLegalBERT Embedder."""

from __future__ import annotations

import numpy as np
import pytest

from app.core.config import Settings, get_settings
from app.retrieval.embeddings import (
    EmbeddingConfig,
    EmbeddingError,
    InLegalBertEmbedder,
    OnnxInLegalBertEmbedder,
)
from app.retrieval.service import _cached_embedder, build_embedder


def test_onnx_embedder_imports_and_instantiates() -> None:
    config = EmbeddingConfig(
        model_name="law-ai/InLegalBERT",
        device="cpu",
        batch_size=4,
        max_tokens=512,
        backend="onnx",
    )
    embedder = OnnxInLegalBertEmbedder(config)
    assert embedder.pooling_method == "attention_mask_mean_pooling"
    assert embedder.normalization == "l2"


def test_onnx_embedder_outputs_normalized_768_dim_vectors() -> None:
    config = EmbeddingConfig(
        model_name="law-ai/InLegalBERT",
        device="cpu",
        batch_size=2,
        max_tokens=128,
        backend="onnx",
    )
    embedder = OnnxInLegalBertEmbedder(config)
    sample_texts = [
        "What does Article 21 of the Constitution of India protect?",
        "The Supreme Court of India interpreted procedure established by law.",
    ]
    vectors = embedder.embed(sample_texts)

    # Output shape (N, 768)
    assert isinstance(vectors, np.ndarray)
    assert vectors.shape == (2, 768)

    # Output dtype float32
    assert vectors.dtype == np.float32

    # Output is L2 normalized
    norms = np.linalg.norm(vectors, axis=1)
    np.testing.assert_allclose(norms, np.ones(2, dtype=np.float32), rtol=1e-5, atol=1e-5)


def test_onnx_embedder_rejects_empty_and_blank_texts() -> None:
    config = EmbeddingConfig(
        model_name="law-ai/InLegalBERT",
        device="cpu",
        batch_size=2,
        max_tokens=128,
        backend="onnx",
    )
    embedder = OnnxInLegalBertEmbedder(config)

    with pytest.raises(EmbeddingError, match="empty text collection"):
        embedder.embed([])

    with pytest.raises(EmbeddingError, match="blank text"):
        embedder.embed(["   ", "\n\t"])


def test_backend_configuration_selection() -> None:
    _cached_embedder.cache_clear()
    settings = get_settings()

    object.__setattr__(settings, "inlegalbert_backend", "onnx")
    onnx_embedder = build_embedder(settings)
    assert isinstance(onnx_embedder, OnnxInLegalBertEmbedder)

    _cached_embedder.cache_clear()
    object.__setattr__(settings, "inlegalbert_backend", "pytorch")
    pytorch_embedder = build_embedder(settings)
    assert isinstance(pytorch_embedder, InLegalBertEmbedder)

    # Reset default back to onnx
    object.__setattr__(settings, "inlegalbert_backend", "onnx")
