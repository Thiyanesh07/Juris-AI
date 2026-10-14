"""Memory Benchmark Script — PyTorch vs ONNX FP32 vs ONNX INT8 InLegalBERT.

Phase 6 tool to measure process Resident Set Size (RSS) memory across application startup,
FAISS index load, model initialization, first embedding peak, full retrieval request,
and repeated retrieval requests for all three backends.

Runs each backend in a separate isolated subprocess to prevent cross-contamination.
Does NOT modify model, FAISS index, or production behavior.
"""

from __future__ import annotations

import gc
import json
import logging
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from app.core.config import get_data_dir

logger = logging.getLogger(__name__)


@dataclass
class BackendMemoryProfile:
    backend: str
    startup_rss_mb: float
    app_init_rss_mb: float
    faiss_loaded_rss_mb: float
    first_embedding_rss_mb: float
    post_first_embedding_rss_mb: float
    single_retrieval_rss_mb: float
    repeated_10_requests_rss_mb: float
    repeated_20_requests_rss_mb: float
    peak_rss_mb: float
    peak_increase_from_baseline_mb: float
    pytorch_model_loaded_in_sys_modules: bool
    memory_stable_across_repeats: bool


def _get_process_rss_mb() -> float:
    import psutil
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024.0 * 1024.0)


def _worker_measure_backend(backend: str) -> str:
    """Executed inside an isolated worker subprocess."""
    import gc
    import psutil

    os.environ["INLEGALBERT_BACKEND"] = backend
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"

    # Step 1: Startup baseline RSS
    rss_1_startup = _get_process_rss_mb()

    # Step 2: App & Settings initialization RSS
    from app.core.config import get_data_dir, get_settings
    from app.main import app as fastapi_app  # noqa: F401

    settings = get_settings()
    object.__setattr__(settings, "inlegalbert_backend", backend)
    rss_2_app_init = _get_process_rss_mb()

    # Step 3: Load FAISS Index into memory
    from app.retrieval.index import load_index
    base_data = get_data_dir()
    index_name = settings.vector_index_name
    faiss_index, metadata = load_index(base_data, index_name)
    rss_3_faiss = _get_process_rss_mb()

    # Step 4: First model load & embedding
    from app.retrieval.service import _cached_embedder, build_embedder, retrieve
    _cached_embedder.cache_clear()
    embedder = build_embedder(settings)

    test_queries = [
        "What does Article 21 protect?",
        "How has the Supreme Court interpreted Article 21?",
        "What is the relationship between Section 66A of the Information Technology Act and Article 19?",
        "What is the Basic Structure Doctrine?",
        "What are the essential ingredients of murder under Section 300 IPC?",
    ]

    _v1 = embedder.embed([test_queries[0]])
    rss_4_first_embed = _get_process_rss_mb()

    # Step 5: Post first embedding after GC
    gc.collect()
    rss_5_post_first_embed = _get_process_rss_mb()

    # Step 6: Full retrieval request execution
    res1 = retrieve(test_queries[0], 5, settings, embedder=embedder)
    rss_6_single_retrieval = _get_process_rss_mb()

    # Step 7: 10 repeated retrieval requests
    for i in range(10):
        q = test_queries[i % len(test_queries)]
        _res = retrieve(q, 5, settings, embedder=embedder)

    rss_7_repeated_10 = _get_process_rss_mb()

    # Step 8: 10 more repeated requests (total 20) to check memory accumulation
    for i in range(10):
        q = test_queries[i % len(test_queries)]
        _res = retrieve(q, 5, settings, embedder=embedder)

    rss_8_repeated_20 = _get_process_rss_mb()

    pytorch_weights_present = False
    if backend in {"onnx", "onnx_int8"}:
        pytorch_weights_present = hasattr(embedder, "_model") and getattr(embedder, "_model") is not None

    all_rss_points = [
        rss_1_startup,
        rss_2_app_init,
        rss_3_faiss,
        rss_4_first_embed,
        rss_5_post_first_embed,
        rss_6_single_retrieval,
        rss_7_repeated_10,
        rss_8_repeated_20,
    ]
    peak_rss = float(max(all_rss_points))
    peak_increase = float(peak_rss - rss_1_startup)

    drift_mb = abs(rss_8_repeated_20 - rss_7_repeated_10)
    stable = drift_mb < 15.0

    profile = BackendMemoryProfile(
        backend=backend,
        startup_rss_mb=round(rss_1_startup, 2),
        app_init_rss_mb=round(rss_2_app_init, 2),
        faiss_loaded_rss_mb=round(rss_3_faiss, 2),
        first_embedding_rss_mb=round(rss_4_first_embed, 2),
        post_first_embedding_rss_mb=round(rss_5_post_first_embed, 2),
        single_retrieval_rss_mb=round(rss_6_single_retrieval, 2),
        repeated_10_requests_rss_mb=round(rss_7_repeated_10, 2),
        repeated_20_requests_rss_mb=round(rss_8_repeated_20, 2),
        peak_rss_mb=round(peak_rss, 2),
        peak_increase_from_baseline_mb=round(peak_increase, 2),
        pytorch_model_loaded_in_sys_modules=pytorch_weights_present,
        memory_stable_across_repeats=stable,
    )
    return json.dumps(asdict(profile))


def run_isolated_memory_benchmark(backend: str) -> BackendMemoryProfile:
    """Run worker measurement for backend in a fresh subprocess."""
    server_api_dir = Path(__file__).resolve().parent.parent.parent
    cmd = [
        sys.executable,
        "-c",
        f"from app.retrieval.benchmark_memory import _worker_measure_backend; print(_worker_measure_backend({backend!r}))",
    ]
    res = subprocess.run(
        cmd,
        cwd=str(server_api_dir),
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(res.stdout.strip().splitlines()[-1])
    return BackendMemoryProfile(**data)


def run_full_3way_memory_benchmark() -> tuple[BackendMemoryProfile, BackendMemoryProfile, BackendMemoryProfile]:
    logger.info("Measuring isolated memory profile for PyTorch backend...")
    pytorch_profile = run_isolated_memory_benchmark("pytorch")

    logger.info("Measuring isolated memory profile for ONNX FP32 backend...")
    onnx_fp32_profile = run_isolated_memory_benchmark("onnx")

    logger.info("Measuring isolated memory profile for ONNX INT8 backend...")
    onnx_int8_profile = run_isolated_memory_benchmark("onnx_int8")

    return pytorch_profile, onnx_fp32_profile, onnx_int8_profile


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    py_prof, fp32_prof, int8_prof = run_full_3way_memory_benchmark()

    render_limit_mb = 512.0
    int8_headroom_mb = render_limit_mb - int8_prof.peak_rss_mb

    print("\n==========================================================================================")
    print("PHASE 6 — MEMORY BENCHMARK REPORT (PyTorch vs ONNX FP32 vs ONNX INT8)")
    print("==========================================================================================")
    print(f"{'Memory Stage / Metric':<35} | {'PyTorch FP32':<15} | {'ONNX FP32':<15} | {'ONNX INT8':<15}")
    print("-" * 92)
    print(f"{'Startup RSS Baseline':<35} | {py_prof.startup_rss_mb:>12.2f} MB | {fp32_prof.startup_rss_mb:>12.2f} MB | {int8_prof.startup_rss_mb:>12.2f} MB")
    print(f"{'App & Config Init RSS':<35} | {py_prof.app_init_rss_mb:>12.2f} MB | {fp32_prof.app_init_rss_mb:>12.2f} MB | {int8_prof.app_init_rss_mb:>12.2f} MB")
    print(f"{'FAISS Index Loaded RSS':<35} | {py_prof.faiss_loaded_rss_mb:>12.2f} MB | {fp32_prof.faiss_loaded_rss_mb:>12.2f} MB | {int8_prof.faiss_loaded_rss_mb:>12.2f} MB")
    print(f"{'First Embedding Peak RSS':<35} | {py_prof.first_embedding_rss_mb:>12.2f} MB | {fp32_prof.first_embedding_rss_mb:>12.2f} MB | {int8_prof.first_embedding_rss_mb:>12.2f} MB")
    print(f"{'Post-Embedding RSS':<35} | {py_prof.post_first_embedding_rss_mb:>12.2f} MB | {fp32_prof.post_first_embedding_rss_mb:>12.2f} MB | {int8_prof.post_first_embedding_rss_mb:>12.2f} MB")
    print(f"{'Single Retrieval Request RSS':<35} | {py_prof.single_retrieval_rss_mb:>12.2f} MB | {fp32_prof.single_retrieval_rss_mb:>12.2f} MB | {int8_prof.single_retrieval_rss_mb:>12.2f} MB")
    print(f"{'10 Repeated Requests RSS':<35} | {py_prof.repeated_10_requests_rss_mb:>12.2f} MB | {fp32_prof.repeated_10_requests_rss_mb:>12.2f} MB | {int8_prof.repeated_10_requests_rss_mb:>12.2f} MB")
    print(f"{'20 Repeated Requests RSS':<35} | {py_prof.repeated_20_requests_rss_mb:>12.2f} MB | {fp32_prof.repeated_20_requests_rss_mb:>12.2f} MB | {int8_prof.repeated_20_requests_rss_mb:>12.2f} MB")
    print("-" * 92)
    print(f"{'Overall Peak RSS':<35} | {py_prof.peak_rss_mb:>12.2f} MB | {fp32_prof.peak_rss_mb:>12.2f} MB | {int8_prof.peak_rss_mb:>12.2f} MB")
    print(f"{'Peak Net Increase from Baseline':<35} | {py_prof.peak_increase_from_baseline_mb:>12.2f} MB | {fp32_prof.peak_increase_from_baseline_mb:>12.2f} MB | {int8_prof.peak_increase_from_baseline_mb:>12.2f} MB")
    print(f"{'Memory Stable Across Repeats':<35} | {str(py_prof.memory_stable_across_repeats):>15} | {str(fp32_prof.memory_stable_across_repeats):>15} | {str(int8_prof.memory_stable_across_repeats):>15}")
    print("==========================================================================================")
    print(f"Render 512 MB Headroom with ONNX INT8: {int8_headroom_mb:.2f} MB ({int8_headroom_mb / render_limit_mb * 100.0:.1f}%)")
    print("==========================================================================================")
