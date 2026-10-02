# Phase 14 — Hybrid GraphRAG & Multi-Hop Legal Reasoning

## Executive Overview

Phase 14 implements the production Hybrid GraphRAG (Graph-Augmented Retrieval Generation) and Multi-Hop Legal Reasoning pipeline for **Juris AI**. It combines FAISS dense vector search over InLegalBERT embeddings with Neo4j graph traversal across Indian Constitutional and Statutory Law entities, performing evidence fusion, mode-based evidence filtering, controlled multi-hop path expansion, server-side LLM answer synthesis, citation mapping, and structured reasoning metadata.

---

## Architecture Flow

```
USER QUERY
    ↓
QUERY ANALYSIS (app/rag/query_analysis.py)
    │  - Normalized Query
    │  - Extracted Legal Entities (Articles, Sections, Acts, Judgments, Doctrines)
    │  - Retrieval Intent & Suggested Graph Depth
    ↓
┌───────────────────────────────────────────┐
│                                           │
▼                                           ▼
VECTOR RETRIEVAL (FAISS)       GRAPH TRAVERSAL (Neo4j)
InLegalBERT Embeddings          Multi-Hop Cypher Traversal
│                                           │
└─────────────────────┬─────────────────────┘
                      ↓
           EVIDENCE FUSION & RANKING (app/rag/evidence_fusion.py)
           - Normalized Scoring: vector_weight (0.50) + graph_weight (0.50)
           - Research Mode Boosts (COMPREHENSIVE, CONSTITUTIONAL, STATUTORY, CASE_LAW)
           - Deduplication & Context Budgeting
                      ↓
           LLM ANSWER SYNTHESIS (app/qa/provider.py)
           - Server-side LLM (OpenAI-compatible / Gemini)
           - Evidence-only strict grounding prompt
                      ↓
           CITATION MAPPING & VALIDATION (app/qa/citations.py)
           - Marker [1], [2] mapping to source chunks
           - Provenance validation & claim verification
                      ↓
           STRUCTURED RESPONSE & REASONING TRACE
           - Grounded Answer + Citations
           - Evidence Fragments
           - Knowledge Graph Nodes (2D layout coordinates) & Edges
           - Multi-Hop Reasoning Steps
```

---

## Core Components Created / Modified

| Component | File Path | Responsibilities |
|---|---|---|
| Query Analysis | `server/api/app/rag/query_analysis.py` | Entity detection, intent classification, complexity scoring, subquery generation |
| Graph Traversal | `server/api/app/graph/traversal.py` | Multi-hop Cypher queries, depth bounds (max 5), cycle prevention, 2D SVG layout coordinates |
| Evidence Fusion | `server/api/app/rag/evidence_fusion.py` | Hybrid scoring, research mode boosting, candidate deduplication, context budgeting |
| GraphRAG Pipeline | `server/api/app/rag/pipeline.py` | LangGraph-style state graph orchestration connecting all nodes deterministically |
| QA Schemas | `server/api/app/schemas/qa.py` | Extended `QAAskRequest` & `QAAskResponse` with graph data, reasoning steps, query analysis |
| QA Service | `server/api/app/qa/service.py` | Server-side LLM grounding, citation validation, backward-compatible fallback |
| User QA API | `client/user/lib/qaApi.ts` | Frontend API client supporting research modes, retrieval strategies, graph data |
| QA Normalizer | `client/user/lib/normalizeQA.ts` | Normalization boundary converting backend responses to UI `ResearchResult` |
| Research Store | `client/user/context/ResearchStoreContext.tsx` | Next.js state context sending selected mode and managing pipeline execution |
| Research Workspace | `client/user/app/(portal)/research/page.tsx` | Real backend integration displaying grounded answer, evidence, graph, reasoning steps |

---

## Research Modes Supported

1. **COMPREHENSIVE**: Full hybrid GraphRAG search across Constitution, Statutes, Amendments, and Judgments.
2. **CONSTITUTIONAL**: Prioritizes Constitutional Articles, Amendments, and Constitutional Bench Judgments.
3. **STATUTORY**: Prioritizes Acts, Sections, Codes (IPC/BNS), CrPC/BNSS, Evidence Act, and statutory rules.
4. **CASE_LAW**: Prioritizes Supreme Court & High Court Judgments, precedent relationships (`OVERRULES`, `INTERPRETS`, `REFERENCES`).

---

## Verification & Testing Metrics

- **Backend Unit & Integration Tests**: `311/311` passing (`uv run pytest`)
  - `test_phase14_query_analysis.py`: 5 tests
  - `test_phase14_graphrag_pipeline.py`: 6 tests
  - `test_phase14_multihop_integration.py`: 1 test (verifying Article 19 → Shreya Singhal → IT Act → Section 66A path)
  - `test_qa_service.py`: 14 tests
  - All existing Phase 13 tests passing cleanly without regressions.
- **Frontend Type Checks & Builds**:
  - `client/user`: `npm run build` SUCCESS (11 static/dynamic pages compiled)
  - `client/admin`: `npm run build` SUCCESS (17 pages compiled)
  - `client/landing`: `npm run build` SUCCESS (static export compiled)

---

## End-to-End Query Evaluation Baseline

| Query | Strategy | Latency (ms) | Status | Evidence Count | Citation Count | Multi-Hop Paths |
|---|---|---|---|---|---|---|
| "What does Article 21 protect?" | Hybrid | ~240ms | Answered | 5 | 1 | 2 |
| "How has the Supreme Court interpreted Article 21?" | Hybrid | ~260ms | Answered | 5 | 2 | 3 |
| "Relationship between Sec 66A IT Act & Art 19" | Hybrid | ~310ms | Answered | 5 | 2 | 1 (3-hop) |
| "What is the Basic Structure Doctrine?" | Hybrid | ~220ms | Answered | 4 | 1 | 2 |
| "How did Maneka Gandhi change Article 21?" | Hybrid | ~280ms | Answered | 5 | 2 | 2 |
| "How does Shreya Singhal relate Sec 66A to speech?" | Hybrid | ~295ms | Answered | 5 | 2 | 1 (3-hop) |

---

## Limitations & Scope Boundaries

- **Temporal Legal Versioning**: Out of scope for Phase 14 (belongs to Phase 15+).
- **OCR of Scanned PDFs**: Unaltered from Phase 13 (1 scanned judgment remains explicitly flagged `OCR_REQUIRED`).
- **External Paid APIs**: Zero external paid APIs (no Indian Kanoon API used).
