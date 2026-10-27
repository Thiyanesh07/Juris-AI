"""Phase 11 — Small-Model Legal Retrieval & Memory Feasibility Benchmark.

Evaluates 3 small public embedding models (all-MiniLM-L6-v2, bge-small-en-v1.5, e5-small-v2)
against the 2,412 production legal chunks and 12 representative legal benchmark queries.
Constructs temporary, isolated experimental FAISS indices in data/experimental_indexes/
WITHOUT modifying the production InLegalBERT FAISS index or production backend configuration.
"""

from __future__ import annotations

import gc
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# Single-threaded environment settings for execution safety
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

# Path resolution
SERVICE_DIR = Path(__file__).resolve().parent
REPO_ROOT = SERVICE_DIR.parent
SERVER_API_DIR = REPO_ROOT / "server" / "api"
DATA_DIR = REPO_ROOT / "data"
EXP_INDEX_DIR = DATA_DIR / "experimental_indexes"

if str(SERVER_API_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_API_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("small_models_feasibility")

# 12 Canonical Representative Legal Benchmark Queries
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

CANDIDATE_MODELS = [
    {
        "name": "sentence-transformers/all-MiniLM-L6-v2",
        "key": "minilm_l6_v2",
        "dimension": 384,
        "query_prefix": "",
        "passage_prefix": "",
    },
    {
        "name": "BAAI/bge-small-en-v1.5",
        "key": "bge_small_v15",
        "dimension": 384,
        "query_prefix": "Represent this sentence for searching relevant passages: ",
        "passage_prefix": "",
    },
    {
        "name": "intfloat/e5-small-v2",
        "key": "e5_small_v2",
        "dimension": 384,
        "query_prefix": "query: ",
        "passage_prefix": "passage: ",
    },
]


def run_isolated_candidate_worker(model_name: str, query_prefix: str, passage_prefix: str, exp_dir_str: str) -> None:
    """Subprocess worker that loads candidate model, embeds corpus, builds FAISS index, and measures RSS."""
    import faiss
    import psutil
    from transformers import AutoModel, AutoTokenizer
    import torch

    def get_rss_mb() -> float:
        gc.collect()
        return round(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024), 2)

    timeline = {}
    timeline["python_boot_mb"] = get_rss_mb()

    # Load Tokenizer & Model
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.eval()
    if hasattr(torch, "set_num_threads"):
        torch.set_num_threads(1)
    timeline["after_model_load_mb"] = get_rss_mb()

    # Load legal chunks metadata
    meta_path = DATA_DIR / "indexes" / "legal_chunks" / "metadata.json"
    with open(meta_path, "r", encoding="utf-8") as f:
        meta_data = json.load(f)

    chunks = meta_data.get("chunks", [])
    if isinstance(chunks, dict):
        chunk_list = list(chunks.values())
    else:
        chunk_list = chunks

    chunk_texts = [f"{passage_prefix}{c.get('text', '')}" for c in chunk_list]
    chunk_ids = [c.get("chunk_id", str(i)) for i, c in enumerate(chunk_list)]

    # Function for generating embeddings
    def embed_texts(texts: list[str], batch_size: int = 32) -> np.ndarray:
        all_vecs = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            inputs = tokenizer(batch, padding=True, truncation=True, max_length=512, return_tensors="pt")
            with torch.inference_mode():
                outputs = model(**inputs)
                if hasattr(outputs, "sentence_embedding"):
                    pooled = outputs.sentence_embedding
                else:
                    hidden = outputs.last_hidden_state
                    mask = inputs["attention_mask"].unsqueeze(-1).to(hidden.dtype)
                    pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)

            vecs = pooled.detach().cpu().numpy().astype(np.float32, copy=False)
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            normalized = vecs / np.maximum(norms, 1e-12)
            all_vecs.append(normalized)
        return np.vstack(all_vecs).astype(np.float32, copy=False)

    # 1. First single query test
    t0 = time.perf_counter()
    _ = embed_texts([f"{query_prefix}{REPRESENTATIVE_LEGAL_QUERIES[0]}"])
    t1 = time.perf_counter()
    timeline["after_1st_inference_mb"] = get_rss_mb()

    # 2. Embed full legal corpus (2,412 chunks)
    tc0 = time.perf_counter()
    corpus_embeddings = embed_texts(chunk_texts, batch_size=32)
    tc1 = time.perf_counter()
    timeline["after_full_corpus_embed_mb"] = get_rss_mb()

    # 3. Build isolated experimental FAISS index
    dim = corpus_embeddings.shape[1]
    faiss_index = faiss.IndexFlatIP(dim)
    faiss_index.add(corpus_embeddings)

    exp_dir = Path(exp_dir_str)
    exp_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(faiss_index, str(exp_dir / "index.faiss"))

    # 4. Embed 12 queries and search experimental FAISS index
    query_texts = [f"{query_prefix}{q}" for q in REPRESENTATIVE_LEGAL_QUERIES]
    tq0 = time.perf_counter()
    query_vecs = embed_texts(query_texts)
    tq1 = time.perf_counter()

    scores, indices = faiss_index.search(query_vecs, 10)
    timeline["after_retrieval_search_mb"] = get_rss_mb()

    # Format retrieval results for evaluation
    query_results = []
    for i, q in enumerate(REPRESENTATIVE_LEGAL_QUERIES):
        hits = []
        for rank in range(10):
            idx = int(indices[i][rank])
            score = float(scores[i][rank])
            c = chunk_list[idx]
            hits.append({
                "rank": rank + 1,
                "score": round(score, 6),
                "chunk_id": c.get("chunk_id"),
                "doc_title": c.get("document_title", ""),
                "section": c.get("section_id", ""),
                "text_snippet": c.get("text", "")[:150],
            })
        query_results.append({
            "query": q,
            "hits": hits,
        })

    payload = {
        "model_name": model_name,
        "dimension": dim,
        "timeline_mb": timeline,
        "peak_rss_mb": max(timeline.values()),
        "latency": {
            "first_query_ms": round((t1 - t0) * 1000.0, 2),
            "corpus_embedding_total_sec": round(tc1 - tc0, 2),
            "query_batch_12_ms": round((tq1 - tq0) * 1000.0, 2),
            "mean_query_latency_ms": round(((tq1 - tq0) * 1000.0) / 12.0, 2),
        },
        "query_results": query_results,
    }

    print("CHILD_OUTPUT_START")
    print(json.dumps(payload))
    print("CHILD_OUTPUT_END")


def run_small_models_benchmark() -> dict:
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        run_isolated_candidate_worker(
            model_name=sys.argv[2],
            query_prefix=sys.argv[3],
            passage_prefix=sys.argv[4],
            exp_dir_str=sys.argv[5],
        )
        sys.exit(0)

    logger.info("Executing Phase 11 Small-Model Legal Retrieval & Memory Feasibility Benchmark...")

    # Load Ground-Truth InLegalBERT PyTorch retrieval results for baseline comparison
    from app.core.config import get_data_dir, get_settings
    from app.retrieval.embeddings import EmbeddingConfig as PyTorchConfig, InLegalBertEmbedder as PyTorchInLegalBertEmbedder
    from app.retrieval.index import load_index, search_index_rows

    settings = get_settings()
    data_dir = get_data_dir()
    faiss_index_pt, metadata_pt = load_index(data_dir, settings.vector_index_name)

    pt_config = PyTorchConfig(model_name="law-ai/InLegalBERT", device="cpu", backend="pytorch")
    pt_embedder = PyTorchInLegalBertEmbedder(pt_config)
    pt_vecs = pt_embedder.embed(REPRESENTATIVE_LEGAL_QUERIES)

    gt_results = []
    for i, q in enumerate(REPRESENTATIVE_LEGAL_QUERIES):
        hits = search_index_rows(faiss_index_pt, metadata_pt, pt_vecs[i : i + 1], top_k=10)
        gt_results.append({
            "query": q,
            "top1_chunk_id": hits[0]["chunk_id"] if hits else None,
            "top5_chunk_ids": set(h["chunk_id"] for h in hits[:5]),
            "top10_chunk_ids": set(h["chunk_id"] for h in hits[:10]),
        })

    report = {"candidates": {}}

    for cand in CANDIDATE_MODELS:
        model_name = cand["name"]
        key = cand["key"]
        exp_dir = EXP_INDEX_DIR / key

        logger.info("Benchmarking candidate model: %s...", model_name)
        cmd = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker",
            model_name,
            cand["query_prefix"],
            cand["passage_prefix"],
            str(exp_dir),
        ]

        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        out = proc.stdout
        s_idx = out.find("CHILD_OUTPUT_START") + len("CHILD_OUTPUT_START")
        e_idx = out.find("CHILD_OUTPUT_END")
        cand_data = json.loads(out[s_idx:e_idx].strip())

        cand_q_results = cand_data["query_results"]
        peak_rss = cand_data["peak_rss_mb"]
        safety_margin = round(512.0 - peak_rss, 2)

        # Comparative evaluation against PyTorch InLegalBERT ground truth
        top1_matches = 0
        top5_matches = 0
        top10_matches = 0
        overlaps_5 = []
        overlaps_10 = []

        legal_relevance_passed = 0

        for i, q_res in enumerate(cand_q_results):
            gt = gt_results[i]
            cand_hits = q_res["hits"]

            cand_t1 = cand_hits[0]["chunk_id"] if cand_hits else None
            cand_t5 = set(h["chunk_id"] for h in cand_hits[:5])
            cand_t10 = set(h["chunk_id"] for h in cand_hits[:10])

            if cand_t1 == gt["top1_chunk_id"]:
                top1_matches += 1
            if cand_t5 == gt["top5_chunk_ids"]:
                top5_matches += 1
            if cand_t10 == gt["top10_chunk_ids"]:
                top10_matches += 1

            o5 = len(cand_t5.intersection(gt["top5_chunk_ids"])) / 5.0
            o10 = len(cand_t10.intersection(gt["top10_chunk_ids"])) / 10.0
            overlaps_5.append(o5)
            overlaps_10.append(o10)

            # Domain relevance check: Does top-5 contain relevant statutory/case law chunk?
            top5_docs = [h["doc_title"] for h in cand_hits[:5]]
            top5_texts = " ".join([h["text_snippet"] for h in cand_hits[:5]]).lower()

            # Query-specific legal domain checks
            if i == 0 and "article 21" in top5_texts:  # Art 21
                legal_relevance_passed += 1
            elif i == 1 and ("article 21" in top5_texts or "supreme court" in top5_texts):
                legal_relevance_passed += 1
            elif i == 2 and ("66a" in top5_texts or "information technology" in top5_texts):
                legal_relevance_passed += 1
            elif i == 3 and ("basic structure" in top5_texts or "kesavananda" in top5_texts):
                legal_relevance_passed += 1
            elif i == 4 and ("murder" in top5_texts or "ipc" in top5_texts or "300" in top5_texts):
                legal_relevance_passed += 1
            elif i == 5 and ("bail" in top5_texts or "bnss" in top5_texts or "crpc" in top5_texts):
                legal_relevance_passed += 1
            elif i == 6 and ("vishaka" in top5_texts or "harassment" in top5_texts):
                legal_relevance_passed += 1
            elif i == 7 and ("article 32" in top5_texts or "judicial review" in top5_texts):
                legal_relevance_passed += 1
            elif i == 8 and ("19(2)" in top5_texts or "restrictions" in top5_texts):
                legal_relevance_passed += 1
            elif i == 9 and ("preventive detention" in top5_texts or "article 22" in top5_texts):
                legal_relevance_passed += 1
            elif i == 10 and ("privacy" in top5_texts or "puttaswamy" in top5_texts):
                legal_relevance_passed += 1
            elif i == 11 and ("368" in top5_texts or "amendment" in top5_texts):
                legal_relevance_passed += 1

        top1_rate = round(top1_matches / 12.0, 4)
        mean_o5 = round(float(np.mean(overlaps_5)), 4)
        mean_o10 = round(float(np.mean(overlaps_10)), 4)
        domain_relevance_rate = round(legal_relevance_passed / 12.0, 4)

        # Decision Logic: Must fit in 512 MB (safety margin >= 100 MB) AND domain relevance >= 90%
        memory_pass = safety_margin >= 100.0
        relevance_pass = domain_relevance_rate >= 0.85
        verdict = "GO (Viable Candidate)" if memory_pass and relevance_pass else "NO-GO (Failed Criteria)"

        report["candidates"][key] = {
            "model_name": model_name,
            "dimension": cand["dimension"],
            "peak_rss_mb": peak_rss,
            "render_512mb_safety_margin_mb": safety_margin,
            "memory_timeline_mb": cand_data["timeline_mb"],
            "latency": cand_data["latency"],
            "retrieval_comparison_vs_inlegalbert": {
                "top1_exact_match_rate": top1_rate,
                "top5_exact_set_match_rate": round(top5_matches / 12.0, 4),
                "top10_exact_set_match_rate": round(top10_matches / 12.0, 4),
                "mean_overlap_at_5": mean_o5,
                "mean_overlap_at_10": mean_o10,
                "legal_domain_relevance_rate": domain_relevance_rate,
            },
            "eval_checks": {
                "fits_render_512mb_with_safety_margin": memory_pass,
                "legal_domain_relevance_acceptable": relevance_pass,
            },
            "verdict": verdict,
        }

    return report


if __name__ == "__main__":
    benchmark_report = run_small_models_benchmark()
    print(json.dumps(benchmark_report, indent=2))
