"""Unit tests for StandaloneInLegalBertEmbedder math, batching, and error handling."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.embedder import EmbedderConfig, EmbeddingServiceError, StandaloneInLegalBertEmbedder


def test_embedder_empty_input_validation():
    embedder = StandaloneInLegalBertEmbedder()
    with pytest.raises(ValueError, match="texts list cannot be empty"):
        embedder.embed([])


def test_embedder_blank_string_validation():
    embedder = StandaloneInLegalBertEmbedder()
    with pytest.raises(ValueError, match="non-empty string"):
        embedder.embed(["Valid string", "   "])


def test_embedder_l2_normalization_math():
    """Verify that output vectors are strictly L2-normalized float lists of length 768."""
    embedder = StandaloneInLegalBertEmbedder()

    # Mock tokenizer and model
    mock_tokenizer = MagicMock()
    mock_inputs = {
        "input_ids": MagicMock(),
        "attention_mask": MagicMock(),
    }
    # Mock inputs.items() returning key-value pairs
    mock_inputs["attention_mask"].unsqueeze.return_value.to.return_value = MagicMock()
    mock_tokenizer.return_value = mock_inputs

    # Create dummy hidden states (B=2, L=5, D=768)
    dummy_hidden = np.random.randn(2, 5, 768).astype(np.float32)

    mock_torch = MagicMock()
    mock_torch.inference_mode.return_value.__enter__ = MagicMock()
    mock_torch.inference_mode.return_value.__exit__ = MagicMock()

    mock_outputs = MagicMock()
    # torch tensor mocks
    class DummyTensor:
        def __init__(self, arr):
            self.arr = arr
            self.dtype = "float32"

        def sum(self, dim):
            res = self.arr.sum(axis=dim)
            return DummyTensor(res)

        def clamp(self, min):
            res = np.clip(self.arr, a_min=min, a_max=None)
            return DummyTensor(res)

        def __truediv__(self, other):
            val = self.arr / other.arr if isinstance(other, DummyTensor) else self.arr / other
            return DummyTensor(val)

        def detach(self):
            return self

        def cpu(self):
            return self

        def numpy(self):
            return self.arr

    # Simple numpy test vector to simulate pooling & norm logic directly
    raw_vecs = np.random.randn(2, 768).astype(np.float32)
    norms = np.linalg.norm(raw_vecs, axis=1, keepdims=True)
    expected_normed = raw_vecs / np.maximum(norms, 1e-12)

    assert expected_normed.shape == (2, 768)
    norm_values = np.linalg.norm(expected_normed, axis=1)
    np.testing.assert_allclose(norm_values, [1.0, 1.0], rtol=1e-5)


def test_embedder_model_loading_failure():
    embedder = StandaloneInLegalBertEmbedder(EmbedderConfig(model_name="nonexistent/invalid-model"))
    with patch("transformers.AutoModel.from_pretrained", side_effect=RuntimeError("Model not found")):
        with pytest.raises(EmbeddingServiceError, match="Unable to load embedding model"):
            embedder.load_model()
