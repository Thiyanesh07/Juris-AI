"""InLegalBERT embedding implementation.

The base InLegalBERT checkpoint is an encoder, rather than a sentence-embedding
model.  We therefore use attention-mask-aware mean pooling over its final hidden
states and L2-normalise every vector.  This makes FAISS inner-product search a
cosine-similarity search and uses precisely the same path for chunks and queries.
"""

from __future__ import annotations

import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

from dataclasses import dataclass
from typing import Any, Protocol


class EmbeddingError(RuntimeError):
    """The configured embedding model could not produce a usable vector."""


class Encoder(Protocol):
    def encode(self, texts: list[str]) -> Any: ...


@dataclass(frozen=True)
class EmbeddingConfig:
    model_name: str
    device: str = "auto"
    batch_size: int = 16
    max_tokens: int = 512


class InLegalBertEmbedder:
    """Lazy, batched embedder backed by Hugging Face Transformers."""

    pooling_method = "attention_mask_mean_pooling"
    normalization = "l2"

    def __init__(self, config: EmbeddingConfig) -> None:
        self.config = config
        self._tokenizer: Any | None = None
        self._model: Any | None = None
        self._device: Any | None = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError as exc:  # pragma: no cover - depends on local extras
            raise EmbeddingError(
                "Retrieval dependencies are not installed; run `uv sync`."
            ) from exc

        requested = self.config.device.lower()
        if requested == "auto":
            device_name = "cuda" if torch.cuda.is_available() else "cpu"
        elif requested == "cuda" and not torch.cuda.is_available():
            raise EmbeddingError("EMBEDDING_DEVICE=cuda was requested but CUDA is unavailable")
        elif requested in {"cpu", "cuda"}:
            device_name = requested
        else:
            raise EmbeddingError("EMBEDDING_DEVICE must be auto, cpu, or cuda")
        try:
            if hasattr(torch, "set_num_threads"):
                torch.set_num_threads(1)
            self._tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
            try:
                self._model = AutoModel.from_pretrained(
                    self.config.model_name, low_cpu_mem_usage=True
                )
            except Exception:
                self._model = AutoModel.from_pretrained(self.config.model_name)
        except Exception as exc:  # pragma: no cover - network/cache dependent
            raise EmbeddingError(
                f"Unable to load embedding model {self.config.model_name!r}: {exc}"
            ) from exc
        self._device = torch.device(device_name)
        self._model.to(self._device)
        self._model.eval()

    def embed(self, texts: list[str]) -> Any:
        """Return a float32 ``(n, dimension)`` normalised matrix."""
        if not texts:
            raise EmbeddingError("Cannot embed an empty text collection")
        if any(not text.strip() for text in texts):
            raise EmbeddingError("Cannot embed blank text")
        self._load()
        assert self._tokenizer is not None and self._model is not None and self._device is not None
        try:
            import numpy as np
            import torch

            batches: list[Any] = []
            for start in range(0, len(texts), self.config.batch_size):
                batch = texts[start : start + self.config.batch_size]
                inputs = self._tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=self.config.max_tokens,
                    return_tensors="pt",
                )
                inputs = {key: value.to(self._device) for key, value in inputs.items()}
                with torch.inference_mode():
                    hidden = self._model(**inputs).last_hidden_state
                mask = inputs["attention_mask"].unsqueeze(-1).to(hidden.dtype)
                pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
                vectors = pooled.detach().cpu().numpy().astype(np.float32, copy=False)
                norms = np.linalg.norm(vectors, axis=1, keepdims=True)
                vectors = vectors / np.maximum(norms, 1e-12)
                batches.append(vectors)
            return np.vstack(batches).astype(np.float32, copy=False)
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingError(f"Embedding failed: {exc}") from exc
