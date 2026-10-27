"""InLegalBERT Embedding Engine for standalone microservice.

Preserves exact attention-mask mean pooling and L2 normalization logic to guarantee
100% vector parity with existing 2,412 FAISS vectors.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Single-threaded environment settings for CPU inference safety
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"


class EmbeddingServiceError(RuntimeError):
    """Raised when embedding production fails."""


@dataclass(frozen=True)
class EmbedderConfig:
    model_name: str = "law-ai/InLegalBERT"
    device: str = "cpu"
    batch_size: int = 16
    max_tokens: int = 512


class StandaloneInLegalBertEmbedder:
    """Singleton model loader and mean-pooling L2-normalized embedder."""

    def __init__(self, config: EmbedderConfig | None = None) -> None:
        self.config = config or EmbedderConfig()
        self._tokenizer: Any | None = None
        self._model: Any | None = None
        self._device: Any | None = None
        self._is_loaded: bool = False

    def load_model(self) -> None:
        if self._is_loaded and self._model is not None:
            return

        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError as exc:
            raise EmbeddingServiceError(
                "Required ML libraries (torch, transformers) are missing."
            ) from exc

        logger.info("Loading model %r on device %s...", self.config.model_name, self.config.device)
        try:
            if hasattr(torch, "set_num_threads"):
                torch.set_num_threads(1)

            self._tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
            self._model = AutoModel.from_pretrained(self.config.model_name)
            self._device = torch.device(self.config.device)
            self._model.to(self._device)
            self._model.eval()
            self._is_loaded = True
            logger.info("Model %r loaded successfully.", self.config.model_name)
        except Exception as exc:
            logger.error("Failed to load model %r: %s", self.config.model_name, exc)
            raise EmbeddingServiceError(
                f"Unable to load embedding model {self.config.model_name!r}: {exc}"
            ) from exc

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Compute L2-normalized attention-mask mean pooled embeddings for texts.

        Returns:
            List of float vectors, each of dimension 768.
        """
        if not texts:
            raise ValueError("texts list cannot be empty")
        for i, text in enumerate(texts):
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"Text at index {i} must be a non-empty string")

        if not self._is_loaded:
            self.load_model()

        assert self._tokenizer is not None and self._model is not None and self._device is not None

        try:
            import torch

            all_vectors: list[np.ndarray] = []
            batch_size = self.config.batch_size

            for start_idx in range(0, len(texts), batch_size):
                batch_texts = texts[start_idx : start_idx + batch_size]
                inputs = self._tokenizer(
                    batch_texts,
                    padding=True,
                    truncation=True,
                    max_length=self.config.max_tokens,
                    return_tensors="pt",
                )
                inputs = {k: v.to(self._device) for k, v in inputs.items()}

                with torch.inference_mode():
                    outputs = self._model(**inputs)
                    hidden = outputs.last_hidden_state  # shape: (B, L, 768)

                mask = inputs["attention_mask"].unsqueeze(-1).to(hidden.dtype)
                pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)

                vectors = pooled.detach().cpu().numpy().astype(np.float32, copy=False)
                norms = np.linalg.norm(vectors, axis=1, keepdims=True)
                normalized = vectors / np.maximum(norms, 1e-12)
                all_vectors.append(normalized)

            stacked = np.vstack(all_vectors).astype(np.float32, copy=False)
            return stacked.tolist()
        except ValueError:
            raise
        except Exception as exc:
            logger.error("Inference execution failed: %s", exc)
            raise EmbeddingServiceError(f"Embedding inference failed: {exc}") from exc
