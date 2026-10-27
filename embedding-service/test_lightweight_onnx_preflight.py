"""Lightweight ONNX Preflight Memory & Numerical Parity Benchmark.

Evaluates ONNX Runtime + AutoTokenizer embedder WITHOUT importing PyTorch or AutoModel at runtime.
Measures process RSS memory overhead (MB), latency, cosine similarity,
and FAISS Top-1, Top-5, and Top-10 retrieval agreement against production FAISS index.
"""

from __future__ import annotations

import gc
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

# Single-threaded execution for execution environment safety
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

# Directory resolution
SERVICE_DIR = Path(__file__).resolve().parent
REPO_ROOT = SERVICE_DIR.parent
SERVER_API_DIR = REPO_ROOT / "server" / "api"
DATA_DIR = REPO_ROOT / "data"

if str(SERVER_API_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_API_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("onnx_preflight")

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


def run_standalone_pure_onnx_worker(model_path_str: str) -> None:
    """Isolated subprocess worker measuring ONNX Runtime + AutoTokenizer RSS memory."""
    import psutil
    from transformers import AutoTokenizer
    import onnxruntime as ort

    def get_rss() -> float:
        gc.collect()
        return round(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024), 2)

    timeline = {}
    timeline["python_boot_mb"] = get_rss()

    # Load AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained("law-ai/InLegalBERT")
    timeline["after_tokenizer_mb"] = get_rss()

    # Load ONNX Session
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 1
    opts.inter_op_num_threads = 1
    session = ort.InferenceSession(model_path_str, sess_options=opts, providers=["CPUExecutionProvider"])
    timeline["after_session_load_mb"] = get_rss()

    # Helper function for inference
    def embed_texts(texts: list[str]) -> np.ndarray:
        inputs = tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="np",
        )
        session_inputs = [i.name for i in session.get_inputs()]
        feed = {name: inputs[name] for name in session_inputs if name in inputs}

        outputs = session.run(None, feed)
        hidden = outputs[0]  # shape: (B, L, 768)
        mask = np.expand_dims(inputs["attention_mask"], axis=-1).astype(hidden.dtype)
        pooled = np.sum(hidden * mask, axis=1) / np.clip(np.sum(mask, axis=1), a_min=1e-9, a_max=None)
        vecs = pooled.astype(np.float32, copy=False)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        return (vecs / np.maximum(norms, 1e-12)).astype(np.float32, copy=False)

    # 1st single query inference
    t0 = time.perf_counter()
    v1 = embed_texts([REPRESENTATIVE_LEGAL_QUERIES[0]])
    t1 = time.perf_counter()
    timeline["after_1st_inference_mb"] = get_rss()

    # Batch 12 queries inference
    tb0 = time.perf_counter()
    v12 = embed_texts(REPRESENTATIVE_LEGAL_QUERIES)
    tb1 = time.perf_counter()
    timeline["after_batch_12_mb"] = get_rss()

    # Repeated requests (50 iterations)
    for _ in range(50):
        _ = embed_texts(REPRESENTATIVE_LEGAL_QUERIES[:4])
    timeline["after_50_iterations_mb"] = get_rss()

    result_payload = {
        "timeline": timeline,
        "peak_rss_mb": max(timeline.values()),
        "single_query_ms": round((t1 - t0) * 1000.0, 2),
        "batch_12_queries_ms": round((tb1 - tb0) * 1000.0, 2),
        "vectors_12": v12.tolist(),
    }
    print("CHILD_OUTPUT_START")
    print(json.dumps(result_payload))
    print("CHILD_OUTPUT_END")


def run_preflight_benchmark() -> dict:
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        run_standalone_pure_onnx_worker(sys.argv[2])
        sys.exit(0)

    logger.info("Running Lightweight ONNX Preflight Memory & Numerical Parity Benchmark...")

    # 1. Generate PyTorch ground truth vectors
    logger.info("Generating PyTorch InLegalBERT ground-truth vectors...")
    from app.core.config import get_data_dir, get_settings
    from app.retrieval.embeddings import EmbeddingConfig as PyTorchConfig, InLegalBertEmbedder as PyTorchInLegalBertEmbedder
    from app.retrieval.index import load_index, search_index_rows

    settings = get_settings()
    data_dir = get_data_dir()
    faiss_index, metadata = load_index(data_dir, settings.vector_index_name)

    pt_config = PyTorchConfig(model_name="law-ai/InLegalBERT", device="cpu", backend="pytorch")
    pt_embedder = PyTorchInLegalBertEmbedder(pt_config)
    pt_vecs = pt_embedder.embed(REPRESENTATIVE_LEGAL_QUERIES)  # shape: (12, 768)

    pt_hits_list = [search_index_rows(faiss_index, metadata, pt_vecs[i : i + 1], top_k=10) for i in range(12)]

    # Function to run worker in a clean isolated subprocess to get true standalone RSS
    def run_isolated_model_benchmark(model_path: Path) -> dict:
        cmd = [sys.executable, str(Path(__file__).resolve()), "--worker", str(model_path)]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)

        output = proc.stdout
        start_idx = output.find("CHILD_OUTPUT_START") + len("CHILD_OUTPUT_START")
        end_idx = output.find("CHILD_OUTPUT_END")
        child_json = output[start_idx:end_idx].strip()
        data = json.loads(child_json)

        onnx_vecs = np.array(data["vectors_12"], dtype=np.float32)
        timeline = data["timeline"]
        peak_rss = data["peak_rss_mb"]

        # Compute cosine similarity vs PyTorch ground truth
        cosines = [
            float(np.dot(pt_vecs[i], onnx_vecs[i]) / (np.linalg.norm(pt_vecs[i]) * np.linalg.norm(onnx_vecs[i])))
            for i in range(len(REPRESENTATIVE_LEGAL_QUERIES))
        ]

        # FAISS retrieval overlap vs PyTorch ground truth
        top1_matches = 0
        top5_exact_matches = 0
        top10_exact_matches = 0
        overlaps_5 = []
        overlaps_10 = []

        for i in range(len(REPRESENTATIVE_LEGAL_QUERIES)):
            onnx_hits = search_index_rows(faiss_index, metadata, onnx_vecs[i : i + 1], top_k=10)
            pt_hits = pt_hits_list[i]

            pt_t1 = pt_hits[0]["chunk_id"] if pt_hits else None
            onnx_t1 = onnx_hits[0]["chunk_id"] if onnx_hits else None
            if pt_t1 == onnx_t1:
                top1_matches += 1

            pt_t5 = set(h["chunk_id"] for h in pt_hits[:5])
            onnx_t5 = set(h["chunk_id"] for h in onnx_hits[:5])
            if pt_t5 == onnx_t5:
                top5_exact_matches += 1

            pt_t10 = set(h["chunk_id"] for h in pt_hits[:10])
            onnx_t10 = set(h["chunk_id"] for h in onnx_hits[:10])
            if pt_t10 == onnx_t10:
                top10_exact_matches += 1

            overlaps_5.append(len(pt_t5.intersection(onnx_t5)) / 5.0)
            overlaps_10.append(len(pt_t10.intersection(onnx_t10)) / 10.0)

        safety_margin = round(512.0 - peak_rss, 2)
        verdict = "GO" if peak_rss < 450.0 and np.min(cosines) > 0.9999 and top1_matches == 12 else "NO-GO"

        return {
            "model_path": str(model_path),
            "file_size_mb": round(model_path.stat().st_size / (1024 * 1024), 2),
            "standalone_peak_rss_mb": peak_rss,
            "render_512mb_safety_margin_mb": safety_margin,
            "memory_timeline_mb": timeline,
            "latency": {
                "single_query_ms": data["single_query_ms"],
                "batch_12_queries_ms": data["batch_12_queries_ms"],
                "per_query_ms": round(data["batch_12_queries_ms"] / 12.0, 2),
            },
            "numerical_parity": {
                "min_cosine_similarity": round(float(np.min(cosines)), 8),
                "mean_cosine_similarity": round(float(np.mean(cosines)), 8),
                "max_cosine_similarity": round(float(np.max(cosines)), 8),
            },
            "faiss_retrieval_agreement": {
                "top1_match_rate": round(top1_matches / 12.0, 4),
                "top5_exact_set_match_rate": round(top5_exact_matches / 12.0, 4),
                "top10_exact_set_match_rate": round(top10_exact_matches / 12.0, 4),
                "mean_overlap_at_5": round(float(np.mean(overlaps_5)), 4),
                "mean_overlap_at_10": round(float(np.mean(overlaps_10)), 4),
            },
            "verdict": verdict,
        }

    report = {}

    # 1. FP32 ONNX Preflight Benchmark
    onnx_fp32_path = DATA_DIR / "models" / "inlegalbert" / "model.onnx"
    logger.info("Executing isolated preflight benchmark for ONNX FP32...")
    report["fp32_onnx"] = run_isolated_model_benchmark(onnx_fp32_path)

    # 2. INT8 ONNX Preflight Benchmark
    onnx_int8_path = DATA_DIR / "models" / "inlegalbert" / "model_int8.onnx"
    if onnx_int8_path.is_file():
        logger.info("Executing isolated preflight benchmark for ONNX INT8...")
        report["int8_onnx"] = run_isolated_model_benchmark(onnx_int8_path)

    return report


if __name__ == "__main__":
    res = run_preflight_benchmark()
    print(json.dumps(res, indent=2))
