"""Numerical Validation Benchmark — PyTorch vs ONNX FP32 vs ONNX INT8 InLegalBERT.

Phase 6 tool to evaluate numerical equivalence, float stability, and determinism
across PyTorch FP32, ONNX FP32, and ONNX INT8.
Does NOT modify production FAISS index or production retrieval behavior.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from app.core.config import get_data_dir
from app.retrieval.embeddings import (
    EmbeddingConfig,
    InLegalBertEmbedder,
    OnnxInLegalBertEmbedder,
)

logger = logging.getLogger(__name__)

CANONICAL_QUERIES = [
    "What does Article 21 protect?",
    "How has the Supreme Court interpreted Article 21?",
    "What is the relationship between Section 66A of the Information Technology Act and Article 19?",
    "What is the Basic Structure Doctrine?",
]


@dataclass
class SampleMetricThreeWay:
    sample_id: int
    category: str
    char_length: int
    word_count: int
    shape_equal: bool
    dtype_equal: bool
    pytorch_l2_norm: float
    onnx_fp32_l2_norm: float
    onnx_int8_l2_norm: float
    cosine_pt_vs_fp32: float
    cosine_pt_vs_int8: float
    cosine_fp32_vs_int8: float
    mad_pt_vs_int8: float
    max_abs_diff_pt_vs_int8: float


@dataclass
class ThreeWayBenchmarkReport:
    total_samples: int
    min_cosine_pt_vs_int8: float
    max_cosine_pt_vs_int8: float
    mean_cosine_pt_vs_int8: float
    median_cosine_pt_vs_int8: float
    overall_mean_abs_diff_pt_vs_int8: float
    overall_max_abs_diff_pt_vs_int8: float
    all_768_dimensional: bool
    all_l2_normalized: bool
    int8_deterministic: bool
    sample_metrics: list[SampleMetricThreeWay]


def load_benchmark_corpus_samples(data_dir: Path | None = None, target_count: int = 30) -> list[tuple[str, str]]:
    """Load representative legal text samples across short, medium, long, and max-token lengths."""
    base_data = (data_dir or get_data_dir()).resolve()
    samples: list[tuple[str, str]] = []

    for q in CANONICAL_QUERIES:
        samples.append(("short_query", q))

    meta_path = base_data / "indexes" / "legal_chunks" / "metadata.json"
    if not meta_path.is_file():
        meta_path = base_data / "legal_corpus_v1" / "indexes" / "faiss" / "metadata.json"

    if meta_path.is_file():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            chunks = meta.get("chunks", [])
            for ch in chunks:
                text = ch.get("text", "").strip()
                if not text:
                    continue
                words = len(text.split())
                if words < 30 and len(samples) < 10:
                    samples.append(("short_text", text))
                elif 30 <= words < 120 and len([s for s in samples if s[0] == "medium_paragraph"]) < 10:
                    samples.append(("medium_paragraph", text))
                elif 120 <= words < 300 and len([s for s in samples if s[0] == "long_text"]) < 10:
                    samples.append(("long_text", text))
                elif words >= 300 and len([s for s in samples if s[0] == "near_512_tokens"]) < 5:
                    samples.append(("near_512_tokens", text))

                if len(samples) >= target_count + len(CANONICAL_QUERIES):
                    break
        except Exception as exc:
            logger.warning("Failed to load corpus metadata for benchmark: %s", exc)

    return samples[:target_count]


def run_three_way_numerical_benchmark(data_dir: Path | None = None) -> ThreeWayBenchmarkReport:
    """Run numerical comparison between PyTorch FP32, ONNX FP32, and ONNX INT8 embedders."""
    cfg_pytorch = EmbeddingConfig(model_name="law-ai/InLegalBERT", device="cpu", backend="pytorch")
    cfg_fp32 = EmbeddingConfig(model_name="law-ai/InLegalBERT", device="cpu", backend="onnx")
    cfg_int8 = EmbeddingConfig(model_name="law-ai/InLegalBERT", device="cpu", backend="onnx_int8")

    logger.info("Initializing PyTorch InLegalBERT embedder...")
    embedder_pt = InLegalBertEmbedder(cfg_pytorch)

    logger.info("Initializing ONNX FP32 InLegalBERT embedder...")
    embedder_fp32 = OnnxInLegalBertEmbedder(cfg_fp32)

    logger.info("Initializing ONNX INT8 InLegalBERT embedder...")
    embedder_int8 = OnnxInLegalBertEmbedder(cfg_int8)

    samples = load_benchmark_corpus_samples(data_dir=data_dir)
    logger.info("Running 3-way numerical benchmark on %d legal text samples...", len(samples))

    metrics: list[SampleMetricThreeWay] = []

    for idx, (cat, text) in enumerate(samples, start=1):
        pt_vec = embedder_pt.embed([text])[0]
        fp32_vec = embedder_fp32.embed([text])[0]
        int8_vec = embedder_int8.embed([text])[0]

        pt_norm = float(np.linalg.norm(pt_vec))
        fp32_norm = float(np.linalg.norm(fp32_vec))
        int8_norm = float(np.linalg.norm(int8_vec))

        cos_pt_fp32 = float(np.dot(pt_vec, fp32_vec) / (pt_norm * fp32_norm))
        cos_pt_int8 = float(np.dot(pt_vec, int8_vec) / (pt_norm * int8_norm))
        cos_fp32_int8 = float(np.dot(fp32_vec, int8_vec) / (fp32_norm * int8_norm))

        abs_diff_pt_int8 = np.abs(pt_vec - int8_vec)
        mad_pt_int8 = float(np.mean(abs_diff_pt_int8))
        max_diff_pt_int8 = float(np.max(abs_diff_pt_int8))

        metrics.append(
            SampleMetricThreeWay(
                sample_id=idx,
                category=cat,
                char_length=len(text),
                word_count=len(text.split()),
                shape_equal=(pt_vec.shape == fp32_vec.shape == int8_vec.shape == (768,)),
                dtype_equal=(pt_vec.dtype == fp32_vec.dtype == int8_vec.dtype == np.float32),
                pytorch_l2_norm=round(pt_norm, 6),
                onnx_fp32_l2_norm=round(fp32_norm, 6),
                onnx_int8_l2_norm=round(int8_norm, 6),
                cosine_pt_vs_fp32=round(cos_pt_fp32, 8),
                cosine_pt_vs_int8=round(cos_pt_int8, 8),
                cosine_fp32_vs_int8=round(cos_fp32_int8, 8),
                mad_pt_vs_int8=round(mad_pt_int8, 8),
                max_abs_diff_pt_vs_int8=round(max_diff_pt_int8, 8),
            )
        )

    # Determinism test for INT8
    first_text = samples[0][1]
    int8_r1 = embedder_int8.embed([first_text])
    int8_r2 = embedder_int8.embed([first_text])
    int8_deterministic = bool(np.array_equal(int8_r1, int8_r2))

    cosines_pt_int8 = [m.cosine_pt_vs_int8 for m in metrics]
    mads = [m.mad_pt_vs_int8 for m in metrics]
    max_diffs = [m.max_abs_diff_pt_vs_int8 for m in metrics]

    all_768 = all(m.shape_equal for m in metrics)
    all_normalized = all(
        abs(m.pytorch_l2_norm - 1.0) < 1e-4 and abs(m.onnx_int8_l2_norm - 1.0) < 1e-4
        for m in metrics
    )

    return ThreeWayBenchmarkReport(
        total_samples=len(metrics),
        min_cosine_pt_vs_int8=round(float(np.min(cosines_pt_int8)), 8),
        max_cosine_pt_vs_int8=round(float(np.max(cosines_pt_int8)), 8),
        mean_cosine_pt_vs_int8=round(float(np.mean(cosines_pt_int8)), 8),
        median_cosine_pt_vs_int8=round(float(np.median(cosines_pt_int8)), 8),
        overall_mean_abs_diff_pt_vs_int8=round(float(np.mean(mads)), 8),
        overall_max_abs_diff_pt_vs_int8=round(float(np.max(max_diffs)), 8),
        all_768_dimensional=all_768,
        all_l2_normalized=all_normalized,
        int8_deterministic=int8_deterministic,
        sample_metrics=metrics,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    report = run_three_way_numerical_benchmark()
    print("\n==================================================")
    print("PHASE 6 — NUMERICAL BENCHMARK REPORT (PyTorch vs ONNX INT8)")
    print("==================================================")
    print(f"Total Samples Evaluated:     {report.total_samples}")
    print(f"Shape Compatibility (768):    {report.all_768_dimensional}")
    print(f"L2 Normalisation (1.0):      {report.all_l2_normalized}")
    print(f"INT8 Determinism Passed:     {report.int8_deterministic}")
    print("--------------------------------------------------")
    print(f"Min Cosine (PyTorch vs INT8): {report.min_cosine_pt_vs_int8:.8f}")
    print(f"Max Cosine (PyTorch vs INT8): {report.max_cosine_pt_vs_int8:.8f}")
    print(f"Mean Cosine (PyTorch vs INT8):{report.mean_cosine_pt_vs_int8:.8f}")
    print(f"Median Cosine (PyTorch vs INT8):{report.median_cosine_pt_vs_int8:.8f}")
    print("--------------------------------------------------")
    print(f"Mean Abs Diff (PyTorch vs INT8):{report.overall_mean_abs_diff_pt_vs_int8:.8f}")
    print(f"Max Abs Diff (PyTorch vs INT8): {report.overall_max_abs_diff_pt_vs_int8:.8f}")
    print("==================================================")
