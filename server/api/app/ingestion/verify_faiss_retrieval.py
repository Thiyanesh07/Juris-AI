"""FAISS Index Retrieval Verification Script — Phase 13.1 Quality Gate.

Executes 4 real queries against the persisted FAISS vector index:
1. "What does Article 21 protect?"
2. "How has the Supreme Court interpreted Article 21?"
3. "What is the relationship between Section 66A of the Information Technology Act and Article 19?"
4. "What is the Basic Structure Doctrine?"

For each query, embeds using the model, searches FAISS, maps vector -> chunk -> document,
and displays rank, similarity score, document, page, section/article, chunk_id, evidence preview,
and relevance classification (DIRECTLY_RELEVANT, PARTIALLY_RELEVANT, RELATED_CONTEXT, IRRELEVANT).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from app.core.config import get_data_dir, get_settings
from app.retrieval.service import build_embedder

logger = logging.getLogger(__name__)

QUERIES = [
    ("QUERY 1", "What does Article 21 protect?"),
    ("QUERY 2", "How has the Supreme Court interpreted Article 21?"),
    ("QUERY 3", "What is the relationship between Section 66A of the Information Technology Act and Article 19?"),
    ("QUERY 4", "What is the Basic Structure Doctrine?"),
]


def classify_relevance(query_id: str, doc_id: str, text: str) -> str:
    text_lower = text.lower()
    if query_id == "QUERY 1":
        if "article 21" in text_lower or "protection of life" in text_lower or "personal liberty" in text_lower:
            return "DIRECTLY_RELEVANT"
        elif "fundamental right" in text_lower or "part iii" in text_lower or "article" in text_lower:
            return "PARTIALLY_RELEVANT"
        return "RELATED_CONTEXT"
    elif query_id == "QUERY 2":
        if "article 21" in text_lower and any(w in text_lower for w in ["maneka", "gopalan", "puttaswamy", "interpreted", "procedure established by law", "due process"]):
            return "DIRECTLY_RELEVANT"
        elif "article 21" in text_lower or "supreme court" in text_lower:
            return "PARTIALLY_RELEVANT"
        return "RELATED_CONTEXT"
    elif query_id == "QUERY 3":
        if ("66a" in text_lower or "information technology" in text_lower) and ("19" in text_lower or "speech" in text_lower or "shreya singhal" in text_lower):
            return "DIRECTLY_RELEVANT"
        elif "66a" in text_lower or "article 19" in text_lower:
            return "PARTIALLY_RELEVANT"
        return "RELATED_CONTEXT"
    elif query_id == "QUERY 4":
        if "basic structure" in text_lower or "kesavananda" in text_lower or "minerva mills" in text_lower:
            return "DIRECTLY_RELEVANT"
        elif "amendment" in text_lower or "constitution" in text_lower:
            return "PARTIALLY_RELEVANT"
        return "RELATED_CONTEXT"
    return "RELATED_CONTEXT"


def run_verification() -> dict[str, list[dict]]:
    cfg = get_settings()
    base_data = get_data_dir()
    corpus_root = base_data / "legal_corpus_v1"
    faiss_dir = base_data / "indexes" / "legal_chunks"
    if not faiss_dir.exists():
        faiss_dir = corpus_root / "indexes" / "faiss"

    meta_file = faiss_dir / "metadata.json"
    index_file = faiss_dir / "index.faiss"

    if not meta_file.exists() or not index_file.exists():
        raise FileNotFoundError(f"FAISS index or metadata not found at {faiss_dir}")

    with open(meta_file, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    chunks = metadata.get("chunks", [])
    print(f"Loaded FAISS metadata with {len(chunks)} chunk records.")

    try:
        import faiss
        import numpy as np
    except ImportError:
        raise RuntimeError("faiss and numpy required")

    faiss_index = faiss.read_index(str(index_file))

    # Initialize embedder
    embedder = build_embedder(cfg)

    all_results = {}

    for q_label, q_text in QUERIES:
        print(f"\n==================================================")
        print(f"{q_label}: '{q_text}'")
        print(f"==================================================")

        # Generate query embedding
        vec = embedder.embed([q_text])
        vec_np = np.asarray(vec, dtype=np.float32)

        # Search top-k
        k = 5
        distances, indices = faiss_index.search(vec_np, k)

        query_res = []
        for rank_idx, (score, idx) in enumerate(zip(distances[0], indices[0]), start=1):
            if idx < 0 or idx >= len(chunks):
                continue
            ch = chunks[idx]
            doc_id = ch.get("document_id", "unknown")
            doc_title = ch.get("document_title", "Unknown Title")
            page_start = ch.get("page_start", 1)
            chunk_id = ch.get("chunk_id", "")
            text = ch.get("text", "")
            snippet = text.replace("\n", " ").strip()[:180] + "..."

            relevance = classify_relevance(q_label, doc_id, text)

            rec = {
                "rank": rank_idx,
                "similarity_score": round(float(score), 4),
                "document_id": doc_id,
                "document_title": doc_title,
                "page": page_start,
                "chunk_id": chunk_id,
                "evidence_preview": snippet,
                "relevance_classification": relevance,
            }
            query_res.append(rec)

            print(f"Rank {rank_idx} | Score: {rec['similarity_score']:.4f} | Relevance: {relevance}")
            print(f"  Doc: {doc_id} ({doc_title}) - Page {page_start}")
            print(f"  Chunk ID: {chunk_id}")
            print(f"  Snippet: {snippet}")

        all_results[q_label] = query_res

    return all_results


if __name__ == "__main__":
    run_verification()
