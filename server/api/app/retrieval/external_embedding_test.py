"""External InLegalBERT Service Feasibility Test (Phase 7).

Tests Hugging Face Inference API for law-ai/InLegalBERT feature extraction / embeddings,
evaluating response schema, pooling/normalization compatibility, FAISS retrieval overlap,
latency, rate limits, and hosting viability.

Does NOT modify production configuration or pipeline behavior.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx
import numpy as np

from app.core.config import get_data_dir, get_settings
from app.retrieval.embeddings import EmbeddingConfig, InLegalBertEmbedder
from app.retrieval.index import load_index, search_index_rows

logger = logging.getLogger(__name__)

TEST_QUERIES = [
    "What does Article 21 protect?",
    "How has the Supreme Court interpreted Article 21?",
    "What is the relationship between Section 66A of the Information Technology Act and Article 19?",
    "What is the Basic Structure Doctrine?",
]

# Hugging Face Inference Endpoint URLs
HF_API_URL_LEGACY = "https://api-inference.huggingface.co/pipeline/feature-extraction/law-ai/InLegalBERT"
HF_API_URL_STANDARD = "https://api-inference.huggingface.co/models/law-ai/InLegalBERT"
HF_ROUTER_URL = "https://router.huggingface.co/hf-inference/models/law-ai/InLegalBERT"


def test_hf_inference_api(
    texts: list[str],
    hf_token: str | None = None,
) -> tuple[np.ndarray | None, dict[str, Any]]:
    """Test Hugging Face Inference API for law-ai/InLegalBERT feature extraction."""
    headers = {"Content-Type": "application/json"}
    token = hf_token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    endpoints = [
        ("legacy_feature_extraction", HF_API_URL_LEGACY),
        ("standard_models_endpoint", HF_API_URL_STANDARD),
        ("router_endpoint", HF_ROUTER_URL),
    ]

    details: dict[str, Any] = {"token_provided": bool(token), "endpoints_tested": {}}
    client = httpx.Client(timeout=30.0)

    for ep_name, ep_url in endpoints:
        start_t = time.perf_counter()
        try:
            # Test payload for HF feature extraction
            payload = {
                "inputs": texts,
                "options": {"wait_for_model": True, "use_cache": True},
            }
            res = client.post(ep_url, json=payload, headers=headers)
            elapsed = (time.perf_counter() - start_t) * 1000.0

            ep_result = {
                "status_code": res.status_code,
                "elapsed_ms": round(elapsed, 2),
                "headers": dict(res.headers),
            }

            if res.status_code == 200:
                data = res.json()
                ep_result["response_type"] = type(data).__name__
                if isinstance(data, list):
                    ep_result["response_len"] = len(data)
                    # Inspect shape of returned features
                    arr = np.array(data, dtype=np.float32)
                    ep_result["shape"] = list(arr.shape)
                    details["endpoints_tested"][ep_name] = ep_result
                    client.close()

                    # Check output structure:
                    # Case A: (batch, seq_len, 768) -> unpooled last_hidden_state
                    # Case B: (batch, 768) -> mean/cls pooled remotely by HF
                    if arr.ndim == 3 and arr.shape[2] == 768:
                        # Mean pool over sequence dimension (axis 1)
                        pooled = np.mean(arr, axis=1)
                        norms = np.linalg.norm(pooled, axis=1, keepdims=True)
                        normalized = pooled / np.maximum(norms, 1e-12)
                        return normalized.astype(np.float32), details
                    elif arr.ndim == 2 and arr.shape[1] == 768:
                        # L2 normalize
                        norms = np.linalg.norm(arr, axis=1, keepdims=True)
                        normalized = arr / np.maximum(norms, 1e-12)
                        return normalized.astype(np.float32), details
                    elif arr.ndim == 1 and arr.shape[0] == 768:
                        # Single text return
                        normalized = arr / max(float(np.linalg.norm(arr)), 1e-12)
                        return normalized.reshape(1, 768).astype(np.float32), details

            else:
                ep_result["response_body"] = res.text[:300]

            details["endpoints_tested"][ep_name] = ep_result

        except Exception as exc:
            details["endpoints_tested"][ep_name] = {
                "status_code": None,
                "error": str(exc),
            }

    client.close()
    return None, details


def run_external_feasibility_test() -> dict[str, Any]:
    """Execute complete Phase 7 external embedding feasibility assessment."""
    start_time = time.perf_counter()
    report: dict[str, Any] = {}

    # Step 1 & 2: Query HF API for sample legal queries
    logger.info("Testing Hugging Face Inference API for law-ai/InLegalBERT...")
    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY")
    ext_vecs, details = test_hf_inference_api(TEST_QUERIES, hf_token=hf_token)

    report["hf_api_details"] = details
    report["hf_api_available"] = ext_vecs is not None

    if ext_vecs is None:
        report["verdict"] = "NOT SUITABLE"
        report["reason"] = (
            "Hugging Face Inference API did not return a usable 768-dimensional float32 feature tensor. "
            f"API response details: {json.dumps(details, indent=2)}"
        )
        return report

    # Step 3: Compare external embeddings with local PyTorch InLegalBERT
    cfg_pt = EmbeddingConfig(model_name="law-ai/InLegalBERT", device="cpu", backend="pytorch")
    local_embedder = InLegalBertEmbedder(cfg_pt)
    local_vecs = local_embedder.embed(TEST_QUERIES)  # Shape: (4, 768)

    cosines = [
        float(np.dot(local_vecs[i], ext_vecs[i]) / (np.linalg.norm(local_vecs[i]) * np.linalg.norm(ext_vecs[i])))
        for i in range(len(TEST_QUERIES))
    ]
    abs_diffs = np.abs(local_vecs - ext_vecs)

    report["embedding_metrics"] = {
        "external_shape": list(ext_vecs.shape),
        "external_dtype": str(ext_vecs.dtype),
        "min_cosine_vs_local": round(float(np.min(cosines)), 8),
        "mean_cosine_vs_local": round(float(np.mean(cosines)), 8),
        "max_cosine_vs_local": round(float(np.max(cosines)), 8),
        "mean_abs_diff_vs_local": round(float(np.mean(abs_diffs)), 8),
        "max_abs_diff_vs_local": round(float(np.max(abs_diffs)), 8),
    }

    # Step 4: FAISS Retrieval Test against Production FAISS Index
    settings = get_settings()
    base_data = get_data_dir()
    faiss_index, metadata = load_index(base_data, settings.vector_index_name)

    top1_matches = 0
    top5_matches = 0

    for i, q in enumerate(TEST_QUERIES):
        local_hits = search_index_rows(faiss_index, metadata, local_vecs[i : i + 1], top_k=5)
        ext_hits = search_index_rows(faiss_index, metadata, ext_vecs[i : i + 1], top_k=5)

        local_t1 = local_hits[0]["chunk_id"] if local_hits else None
        ext_t1 = ext_hits[0]["chunk_id"] if ext_hits else None
        if local_t1 == ext_t1:
            top1_matches += 1

        local_t5 = set(h["chunk_id"] for h in local_hits)
        ext_t5 = set(h["chunk_id"] for h in ext_hits)
        if local_t5 == ext_t5:
            top5_matches += 1

    report["faiss_retrieval"] = {
        "top1_match_rate": round(top1_matches / len(TEST_QUERIES), 4),
        "top5_exact_set_match_rate": round(top5_matches / len(TEST_QUERIES), 4),
    }

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    report["elapsed_total_ms"] = round(elapsed_ms, 2)

    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = run_external_feasibility_test()
    print(json.dumps(res, indent=2))
