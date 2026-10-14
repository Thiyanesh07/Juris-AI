"""Phase 12 InLegalBERT Runtime Optimization Investigation Harness.

Performs isolated, reproducible benchmarks to evaluate whether law-ai/InLegalBERT
can run efficiently within Render Free's 512 MB RAM limit (requiring >= 100 MB headroom,
i.e. Peak RSS <= 412 MB) without replacing the model, tokenizer, 768-dim output,
mean pooling, L2 normalization, or production FAISS index.

Does NOT modify production runtime code or deploy anything.
"""

from __future__ import annotations

import gc
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

# Set base environment
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

logger = logging.getLogger("investigate_phase12")


def get_process_rss_mb() -> float:
    import psutil
    proc = psutil.Process(os.getpid())
    return proc.memory_info().rss / (1024.0 * 1024.0)


# ==============================================================================
# Task 1: Audit Graph & Tokenizer
# ==============================================================================

def audit_onnx_graph_and_tokenizer() -> dict[str, Any]:
    import onnx
    from transformers import AutoTokenizer
    from app.core.config import get_data_dir
    from app.retrieval.export_onnx import get_onnx_model_path

    fp32_path = get_onnx_model_path()
    if not fp32_path.exists():
        raise FileNotFoundError(f"FP32 ONNX model not found at {fp32_path}")

    model = onnx.load(str(fp32_path), load_external_data=False)
    opset_versions = {op.domain or "ai.onnx": op.version for op in model.opset_import}
    
    node_types: dict[str, int] = {}
    for n in model.graph.node:
        node_types[n.op_type] = node_types.get(n.op_type, 0) + 1

    input_info = [
        {"name": inp.name, "type": inp.type.tensor_type.elem_type}
        for inp in model.graph.input
    ]
    output_info = [
        {"name": out.name, "type": out.type.tensor_type.elem_type}
        for out in model.graph.output
    ]

    # Tokenizer audit
    tok = AutoTokenizer.from_pretrained("law-ai/InLegalBERT")
    tok_info = {
        "class": tok.__class__.__name__,
        "vocab_size": tok.vocab_size,
        "model_max_length": tok.model_max_length,
        "is_fast": tok.is_fast,
    }

    # Weight initializers breakdown
    total_params = 0
    weights_mb = 0.0
    for init in model.graph.initializer:
        dims = list(init.dims)
        count = int(np.prod(dims)) if dims else 1
        total_params += count
    weights_mb = fp32_path.stat().st_size / (1024 * 1024)

    return {
        "fp32_path": str(fp32_path),
        "file_size_mb": round(weights_mb, 2),
        "total_initializers": len(model.graph.initializer),
        "total_nodes": len(model.graph.node),
        "opset_imports": opset_versions,
        "node_type_counts": dict(sorted(node_types.items())),
        "inputs": input_info,
        "outputs": output_info,
        "tokenizer": tok_info,
    }


# ==============================================================================
# Task 3: Generate 4-bit Weight-Only Quantized Variants
# ==============================================================================

def ensure_int4_models() -> dict[str, Path]:
    from app.core.config import get_data_dir
    from app.retrieval.export_onnx import get_onnx_model_path
    from onnxruntime.quantization.matmul_nbits_quantizer import MatMulNBitsQuantizer

    base_dir = get_data_dir() / "models" / "inlegalbert"
    fp32_path = get_onnx_model_path()

    variants = {
        "int4_b128_asym": base_dir / "model_int4_b128_asym.onnx",
        "int4_b64_asym": base_dir / "model_int4_b64_asym.onnx",
        "int4_b32_asym": base_dir / "model_int4_b32_asym.onnx",
        "int4_b128_sym": base_dir / "model_int4_b128_sym.onnx",
    }

    configs = {
        "int4_b128_asym": {"bits": 4, "block_size": 128, "is_symmetric": False},
        "int4_b64_asym": {"bits": 4, "block_size": 64, "is_symmetric": False},
        "int4_b32_asym": {"bits": 4, "block_size": 32, "is_symmetric": False},
        "int4_b128_sym": {"bits": 4, "block_size": 128, "is_symmetric": True},
    }

    for name, out_path in variants.items():
        if not out_path.exists():
            logger.info("Generating INT4 variant '%s' at %s...", name, out_path)
            cfg = configs[name]
            quantizer = MatMulNBitsQuantizer(
                str(fp32_path),
                bits=cfg["bits"],
                block_size=cfg["block_size"],
                is_symmetric=cfg["is_symmetric"],
            )
            quantizer.process()
            quantizer.model.save_model_to_file(str(out_path))
            logger.info("Generated %s (%.2f MB)", name, out_path.stat().st_size / (1024 * 1024))

    return variants


# ==============================================================================
# Isolated Worker for Memory & Latency Profiling
# ==============================================================================

def _worker_measure_runtime(config_json: str) -> str:
    """Isolated subprocess worker measuring precise RSS lifecycle and latency."""
    import gc
    import json
    import os
    import time
    import numpy as np
    import psutil
    from transformers import AutoTokenizer

    cfg = json.loads(config_json)
    backend_type = cfg["backend_type"]  # 'pytorch', 'onnx_fp32', 'onnx_int8', 'onnx_int4'
    model_path = cfg.get("model_path")
    intra_threads = cfg.get("intra_threads", 1)
    inter_threads = cfg.get("inter_threads", 1)
    opt_level = cfg.get("opt_level", 99)
    arena = cfg.get("arena", True)

    os.environ["OMP_NUM_THREADS"] = str(intra_threads)
    os.environ["MKL_NUM_THREADS"] = str(intra_threads)

    # 1. Startup RSS
    rss_startup = get_process_rss_mb()

    # 2. App & Settings init
    from app.core.config import get_data_dir, get_settings
    settings = get_settings()
    rss_app_init = get_process_rss_mb()

    # 3. FAISS index load
    from app.retrieval.index import load_index, search_index_rows
    base_data = get_data_dir()
    faiss_index, metadata = load_index(base_data, settings.vector_index_name)
    rss_faiss = get_process_rss_mb()

    # 4. Model initialization
    tok = AutoTokenizer.from_pretrained(settings.embedding_model_name)
    pt_model = None
    ort_session = None

    if backend_type == "pytorch":
        import torch
        if hasattr(torch, "set_num_threads"):
            torch.set_num_threads(intra_threads)
        from transformers import AutoModel
        pt_model = AutoModel.from_pretrained(settings.embedding_model_name)
        pt_model.eval()
    else:
        import onnxruntime as ort
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = intra_threads
        opts.inter_op_num_threads = inter_threads
        if opt_level == 0:
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL
        elif opt_level == 1:
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
        elif opt_level == 2:
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED
        else:
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        opts.enable_cpu_mem_arena = arena
        ort_session = ort.InferenceSession(str(model_path), sess_options=opts, providers=["CPUExecutionProvider"])
        input_names = [i.name for i in ort_session.get_inputs()]

    rss_model_init = get_process_rss_mb()

    def embed_texts(texts: list[str]) -> np.ndarray:
        if backend_type == "pytorch":
            import torch
            inputs = tok(texts, padding=True, truncation=True, max_length=512, return_tensors="pt")
            with torch.inference_mode():
                hidden = pt_model(**inputs).last_hidden_state
            mask = inputs["attention_mask"].unsqueeze(-1).to(hidden.dtype)
            pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
            vecs = pooled.detach().cpu().numpy().astype(np.float32)
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            return vecs / np.maximum(norms, 1e-12)
        else:
            inputs = tok(texts, padding=True, truncation=True, max_length=512, return_tensors="np")
            feed = {n: inputs[n] for n in input_names if n in inputs}
            out = ort_session.run(None, feed)[0]
            mask = np.expand_dims(inputs["attention_mask"], -1).astype(out.dtype)
            pooled = np.sum(out * mask, axis=1) / np.clip(np.sum(mask, axis=1), 1e-9, None)
            vecs = pooled.astype(np.float32)
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            return vecs / np.maximum(norms, 1e-12)

    canonical_q = "What does Article 21 protect?"

    # 5. First single inference
    t0 = time.perf_counter()
    v1 = embed_texts([canonical_q])
    t_first = time.perf_counter() - t0
    rss_first_inference = get_process_rss_mb()

    # 6. Latency benchmark on single query (10 warmup + 10 timed)
    latencies = []
    for _ in range(5):
        embed_texts([canonical_q])
    for _ in range(10):
        t_start = time.perf_counter()
        embed_texts([canonical_q])
        latencies.append((time.perf_counter() - t_start) * 1000.0)  # ms

    # 7. Batch inference (batch size 4 and batch size 16)
    b4_texts = [
        "What does Article 21 protect?",
        "How has the Supreme Court interpreted Article 21?",
        "What is the relationship between Section 66A of the Information Technology Act and Article 19?",
        "What is the Basic Structure Doctrine?",
    ]
    embed_texts(b4_texts)
    rss_batch_4 = get_process_rss_mb()

    b16_texts = b4_texts * 4
    embed_texts(b16_texts)
    rss_batch_16 = get_process_rss_mb()

    # 8. Single retrieval request through FAISS
    q_vec = embed_texts([canonical_q])
    hits = search_index_rows(faiss_index, metadata, q_vec, top_k=5)
    rss_single_retrieval = get_process_rss_mb()

    # 9. 10 repeated retrieval requests
    for i in range(10):
        q_i = b4_texts[i % len(b4_texts)]
        _v = embed_texts([q_i])
        _h = search_index_rows(faiss_index, metadata, _v, top_k=5)
    rss_repeated_10 = get_process_rss_mb()

    # 10. 20 repeated retrieval requests
    for i in range(10):
        q_i = b4_texts[i % len(b4_texts)]
        _v = embed_texts([q_i])
        _h = search_index_rows(faiss_index, metadata, _v, top_k=5)
    rss_repeated_20 = get_process_rss_mb()

    all_rss = [
        rss_startup,
        rss_app_init,
        rss_faiss,
        rss_model_init,
        rss_first_inference,
        rss_batch_4,
        rss_batch_16,
        rss_single_retrieval,
        rss_repeated_10,
        rss_repeated_20,
    ]
    peak_rss = float(max(all_rss))
    headroom = 512.0 - peak_rss

    result = {
        "name": cfg.get("name", "unnamed"),
        "backend_type": backend_type,
        "rss_startup": round(rss_startup, 2),
        "rss_app_init": round(rss_app_init, 2),
        "rss_faiss": round(rss_faiss, 2),
        "rss_model_init": round(rss_model_init, 2),
        "rss_first_inference": round(rss_first_inference, 2),
        "rss_batch_4": round(rss_batch_4, 2),
        "rss_batch_16": round(rss_batch_16, 2),
        "rss_single_retrieval": round(rss_single_retrieval, 2),
        "rss_repeated_10": round(rss_repeated_10, 2),
        "rss_repeated_20": round(rss_repeated_20, 2),
        "peak_rss": round(peak_rss, 2),
        "headroom_512mb": round(headroom, 2),
        "pass_headroom": bool(headroom >= 100.0),
        "latency_p50_ms": round(float(np.percentile(latencies, 50)), 2),
        "latency_p95_ms": round(float(np.percentile(latencies, 95)), 2),
        "latency_mean_ms": round(float(np.mean(latencies)), 2),
        "first_inference_latency_ms": round(t_first * 1000.0, 2),
    }
    return json.dumps(result)


def run_isolated_benchmark(cfg: dict[str, Any]) -> dict[str, Any]:
    """Execute worker measurement in a clean subprocess."""
    server_api_dir = Path(__file__).resolve().parent.parent.parent
    cmd = [
        sys.executable,
        "-c",
        f"from app.retrieval.investigate_phase12 import _worker_measure_runtime; print(_worker_measure_runtime({json.dumps(cfg)!r}))",
    ]
    res = subprocess.run(
        cmd,
        cwd=str(server_api_dir),
        capture_output=True,
        text=True,
        check=True,
    )
    lines = [line.strip() for line in res.stdout.strip().splitlines() if line.strip()]
    return json.loads(lines[-1])


# ==============================================================================
# Numerical & Retrieval Quality Evaluation
# ==============================================================================

def run_numerical_and_retrieval_eval(
    model_path: Path | None,
    backend_type: str,
    name: str,
    intra_threads: int = 1,
) -> dict[str, Any]:
    from transformers import AutoTokenizer
    import torch
    from app.core.config import get_data_dir, get_settings
    from app.retrieval.benchmark_numerical import load_benchmark_corpus_samples
    from app.retrieval.benchmark_retrieval import REPRESENTATIVE_LEGAL_QUERIES
    from app.retrieval.embeddings import EmbeddingConfig, InLegalBertEmbedder
    from app.retrieval.index import load_index, search_index_rows

    base_data = get_data_dir()
    faiss_index, metadata = load_index(base_data, "legal_chunks")
    samples = load_benchmark_corpus_samples()

    # PyTorch reference
    cfg_pt = EmbeddingConfig(model_name="law-ai/InLegalBERT", device="cpu", backend="pytorch")
    pt_emb = InLegalBertEmbedder(cfg_pt)

    tok = AutoTokenizer.from_pretrained("law-ai/InLegalBERT")
    
    if backend_type == "pytorch":
        embed_fn = lambda texts: pt_emb.embed(texts)
    else:
        import onnxruntime as ort
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = intra_threads
        opts.inter_op_num_threads = 1
        sess = ort.InferenceSession(str(model_path), sess_options=opts, providers=["CPUExecutionProvider"])
        in_names = [i.name for i in sess.get_inputs()]

        def _onnx_embed(texts: list[str]) -> np.ndarray:
            inputs = tok(texts, padding=True, truncation=True, max_length=512, return_tensors="np")
            feed = {n: inputs[n] for n in in_names if n in inputs}
            out = sess.run(None, feed)[0]
            mask = np.expand_dims(inputs["attention_mask"], -1).astype(out.dtype)
            pooled = np.sum(out * mask, axis=1) / np.clip(np.sum(mask, axis=1), 1e-9, None)
            vecs = pooled.astype(np.float32)
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            return vecs / np.maximum(norms, 1e-12)

        embed_fn = _onnx_embed

    # 1. Numerical evaluation on 29 samples
    cosines = []
    mads = []
    max_diffs = []
    all_768 = True
    all_l2 = True

    for cat, text in samples:
        v_ref = pt_emb.embed([text])[0]
        v_cand = embed_fn([text])[0]

        if v_cand.shape != (768,):
            all_768 = False
        norm = float(np.linalg.norm(v_cand))
        if abs(norm - 1.0) > 1e-4:
            all_l2 = False

        cos = float(np.dot(v_ref, v_cand) / (np.linalg.norm(v_ref) * norm))
        abs_diff = np.abs(v_ref - v_cand)
        cosines.append(cos)
        mads.append(float(np.mean(abs_diff)))
        max_diffs.append(float(np.max(abs_diff)))

    # Determinism check
    first_text = samples[0][1]
    det_1 = embed_fn([first_text])
    det_2 = embed_fn([first_text])
    deterministic = bool(np.allclose(det_1, det_2, atol=1e-6))

    # 2. Retrieval evaluation on 12 canonical queries against production FAISS
    top1_matches = 0
    top5_matches = 0
    top10_matches = 0
    overlaps_5 = []
    overlaps_10 = []
    score_diffs = []

    for q in REPRESENTATIVE_LEGAL_QUERIES:
        ref_vec = pt_emb.embed([q])
        cand_vec = embed_fn([q])

        ref_hits = search_index_rows(faiss_index, metadata, ref_vec, top_k=10)
        cand_hits = search_index_rows(faiss_index, metadata, cand_vec, top_k=10)

        ref_t1 = ref_hits[0]["chunk_id"] if ref_hits else None
        cand_t1 = cand_hits[0]["chunk_id"] if cand_hits else None
        if ref_t1 == cand_t1:
            top1_matches += 1

        ref_t5 = set(h["chunk_id"] for h in ref_hits[:5])
        cand_t5 = set(h["chunk_id"] for h in cand_hits[:5])
        if ref_t5 == cand_t5:
            top5_matches += 1
        overlaps_5.append(len(ref_t5 & cand_t5) / 5.0)

        ref_t10 = set(h["chunk_id"] for h in ref_hits[:10])
        cand_t10 = set(h["chunk_id"] for h in cand_hits[:10])
        if ref_t10 == cand_t10:
            top10_matches += 1
        overlaps_10.append(len(ref_t10 & cand_t10) / 10.0)

        for hr, hc in zip(ref_hits, cand_hits, strict=False):
            score_diffs.append(abs(hr["score"] - hc["score"]))

    n_q = len(REPRESENTATIVE_LEGAL_QUERIES)
    return {
        "name": name,
        "total_samples": len(samples),
        "min_cosine": round(float(np.min(cosines)), 8),
        "max_cosine": round(float(np.max(cosines)), 8),
        "mean_cosine": round(float(np.mean(cosines)), 8),
        "median_cosine": round(float(np.median(cosines)), 8),
        "overall_mad": round(float(np.mean(mads)), 8),
        "overall_max_diff": round(float(np.max(max_diffs)), 8),
        "all_768_dim": all_768,
        "all_l2_normalized": all_l2,
        "deterministic": deterministic,
        "total_retrieval_queries": n_q,
        "top1_match_rate": round(top1_matches / n_q * 100.0, 2),
        "top5_set_match_rate": round(top5_matches / n_q * 100.0, 2),
        "top10_set_match_rate": round(top10_matches / n_q * 100.0, 2),
        "mean_overlap_5": round(float(np.mean(overlaps_5)) * 100.0, 2),
        "mean_overlap_10": round(float(np.mean(overlaps_10)) * 100.0, 2),
        "mean_score_diff": round(float(np.mean(score_diffs)), 8),
        "max_score_diff": round(float(np.max(score_diffs)), 8),
    }


# ==============================================================================
# Full Investigation Orchestrator
# ==============================================================================

def execute_phase12_investigation() -> dict[str, Any]:
    from app.core.config import get_data_dir
    from app.retrieval.export_onnx import get_onnx_model_path
    from app.retrieval.quantize_onnx import get_onnx_int8_model_path

    print("================================================================================")
    print("PHASE 12 — INLEGALBERT RUNTIME OPTIMIZATION INVESTIGATION")
    print("================================================================================")

    # 1. Audit
    print("\n--- [Step 1] Auditing ONNX Graph & Tokenizer ---")
    audit = audit_onnx_graph_and_tokenizer()
    print(f"FP32 Model Size: {audit['file_size_mb']} MB")
    print(f"Total Nodes: {audit['total_nodes']}, Ops: {len(audit['node_type_counts'])}")
    print(f"Opset: {audit['opset_imports']}")
    print(f"Tokenizer: {audit['tokenizer']}")

    # 2. Ensure INT4 models
    print("\n--- [Step 2] Generating / Verifying INT4 Weight-Only Quantized Variants ---")
    int4_paths = ensure_int4_models()
    for k, p in int4_paths.items():
        print(f"  {k}: {p.stat().st_size / (1024*1024):.2f} MB")

    fp32_path = get_onnx_model_path()
    int8_path = get_onnx_int8_model_path()

    # 3. FP32 Parameter Sweeps (One at a time)
    print("\n--- [Step 3] Running FP32 Parameter Sweeps (Thread counts & Graph Opts) ---")
    fp32_sweep_configs = [
        # Baseline
        {"name": "FP32 (intra=1, inter=1, opt=ALL, arena=True) [Baseline]", "backend_type": "onnx_fp32", "model_path": str(fp32_path), "intra_threads": 1, "inter_threads": 1, "opt_level": 99, "arena": True},
        # Vary intra threads
        {"name": "FP32 (intra=2, inter=1, opt=ALL, arena=True)", "backend_type": "onnx_fp32", "model_path": str(fp32_path), "intra_threads": 2, "inter_threads": 1, "opt_level": 99, "arena": True},
        {"name": "FP32 (intra=4, inter=1, opt=ALL, arena=True)", "backend_type": "onnx_fp32", "model_path": str(fp32_path), "intra_threads": 4, "inter_threads": 1, "opt_level": 99, "arena": True},
        # Vary inter threads
        {"name": "FP32 (intra=1, inter=2, opt=ALL, arena=True)", "backend_type": "onnx_fp32", "model_path": str(fp32_path), "intra_threads": 1, "inter_threads": 2, "opt_level": 99, "arena": True},
        # Vary graph optimizations
        {"name": "FP32 (intra=1, inter=1, opt=DISABLE, arena=True)", "backend_type": "onnx_fp32", "model_path": str(fp32_path), "intra_threads": 1, "inter_threads": 1, "opt_level": 0, "arena": True},
        {"name": "FP32 (intra=1, inter=1, opt=BASIC, arena=True)", "backend_type": "onnx_fp32", "model_path": str(fp32_path), "intra_threads": 1, "inter_threads": 1, "opt_level": 1, "arena": True},
        {"name": "FP32 (intra=1, inter=1, opt=EXTENDED, arena=True)", "backend_type": "onnx_fp32", "model_path": str(fp32_path), "intra_threads": 1, "inter_threads": 1, "opt_level": 2, "arena": True},
        # Vary memory arena
        {"name": "FP32 (intra=1, inter=1, opt=ALL, arena=False)", "backend_type": "onnx_fp32", "model_path": str(fp32_path), "intra_threads": 1, "inter_threads": 1, "opt_level": 99, "arena": False},
        {"name": "FP32 (intra=1, inter=1, opt=DISABLE, arena=False)", "backend_type": "onnx_fp32", "model_path": str(fp32_path), "intra_threads": 1, "inter_threads": 1, "opt_level": 0, "arena": False},
    ]

    sweep_results = []
    for scfg in fp32_sweep_configs:
        print(f"  Measuring sweep: {scfg['name']}...")
        res = run_isolated_benchmark(scfg)
        sweep_results.append(res)
        print(f"    Peak RSS: {res['peak_rss']} MB | Headroom: {res['headroom_512mb']} MB | Latency (p50): {res['latency_p50_ms']} ms")

    # 4. Compare All Backends (PyTorch, FP32, INT8, INT4 variants)
    print("\n--- [Step 4] Measuring Memory Lifecycle across All Backends ---")
    candidate_profiles = [
        {"name": "PyTorch FP32 (Reference)", "backend_type": "pytorch", "intra_threads": 1},
        {"name": "ONNX FP32 (Baseline)", "backend_type": "onnx_fp32", "model_path": str(fp32_path), "intra_threads": 1, "opt_level": 99, "arena": True},
        {"name": "ONNX FP32 (No-Arena)", "backend_type": "onnx_fp32", "model_path": str(fp32_path), "intra_threads": 1, "opt_level": 99, "arena": False},
        {"name": "ONNX INT8 Dynamic", "backend_type": "onnx_int8", "model_path": str(int8_path), "intra_threads": 1, "opt_level": 99, "arena": True},
        {"name": "ONNX INT4 (RTN b128 asym)", "backend_type": "onnx_int4", "model_path": str(int4_paths["int4_b128_asym"]), "intra_threads": 1, "opt_level": 99, "arena": True},
        {"name": "ONNX INT4 (RTN b64 asym)", "backend_type": "onnx_int4", "model_path": str(int4_paths["int4_b64_asym"]), "intra_threads": 1, "opt_level": 99, "arena": True},
        {"name": "ONNX INT4 (RTN b32 asym)", "backend_type": "onnx_int4", "model_path": str(int4_paths["int4_b32_asym"]), "intra_threads": 1, "opt_level": 99, "arena": True},
        {"name": "ONNX INT4 (RTN b128 sym)", "backend_type": "onnx_int4", "model_path": str(int4_paths["int4_b128_sym"]), "intra_threads": 1, "opt_level": 99, "arena": True},
    ]

    candidate_memory_results = []
    for ccfg in candidate_profiles:
        print(f"  Measuring memory profile: {ccfg['name']}...")
        res = run_isolated_benchmark(ccfg)
        candidate_memory_results.append(res)
        print(f"    Peak RSS: {res['peak_rss']} MB | Headroom: {res['headroom_512mb']} MB | First Infer: {res['rss_first_inference']} MB | Repeated20: {res['rss_repeated_20']} MB")

    # 5. Quality & Retrieval Evaluation against PyTorch Reference
    print("\n--- [Step 5] Evaluating Numerical (29 samples) & Retrieval (12 queries) Quality ---")
    quality_candidates = [
        {"name": "PyTorch FP32 (Reference)", "backend_type": "pytorch", "model_path": None},
        {"name": "ONNX FP32", "backend_type": "onnx", "model_path": fp32_path},
        {"name": "ONNX INT8 Dynamic", "backend_type": "onnx", "model_path": int8_path},
        {"name": "ONNX INT4 (RTN b128 asym)", "backend_type": "onnx", "model_path": int4_paths["int4_b128_asym"]},
        {"name": "ONNX INT4 (RTN b64 asym)", "backend_type": "onnx", "model_path": int4_paths["int4_b64_asym"]},
        {"name": "ONNX INT4 (RTN b32 asym)", "backend_type": "onnx", "model_path": int4_paths["int4_b32_asym"]},
        {"name": "ONNX INT4 (RTN b128 sym)", "backend_type": "onnx", "model_path": int4_paths["int4_b128_sym"]},
    ]

    quality_results = []
    for qcfg in quality_candidates:
        print(f"  Evaluating quality: {qcfg['name']}...")
        qres = run_numerical_and_retrieval_eval(
            model_path=qcfg["model_path"],
            backend_type=qcfg["backend_type"],
            name=qcfg["name"],
        )
        quality_results.append(qres)
        print(f"    Mean Cosine: {qres['mean_cosine']:.6f} | Top-1: {qres['top1_match_rate']}% | Overlap@5: {qres['mean_overlap_5']}% | Overlap@10: {qres['mean_overlap_10']}%")

    # Combine into comprehensive report
    report = {
        "audit": audit,
        "fp32_sweeps": sweep_results,
        "candidate_memory": candidate_memory_results,
        "quality": quality_results,
    }

    out_file = Path(__file__).parent / "phase12_investigation_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nSaved detailed JSON results to {out_file}")

    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    execute_phase12_investigation()
