# Final Quantitative Experimental Results
## Project: Graph-RAG System for Multi-Hop Reasoning Over Indian Constitutional and Statutory Law (Juris AI)

> **Document Type:** Quantitative Experimental Results & Repository Evidence Extraction  
> **Source Repository:** Juris AI (`c:\Projects\Juris AI`)  
> **Verification Status:** Verified against project source code, database indices, and result reports  

---

## EXPERIMENT 1: Legal Knowledge Layer Ingestion & Graph Extraction

1. **Experiment Name:** Full Legal Corpus Ingestion, Legal-Aware Chunking, FAISS Vector Indexing, and Entity-Relationship Triple Extraction
2. **Research Objective:** To process raw Indian legal PDF documents into structured page-level text, construct structural legal chunks, generate dense vector embeddings, extract canonical legal entities and relationships, and index them into FAISS and Neo4j for hybrid retrieval.
3. **Dataset:** `legal_corpus_v1` (34 raw PDF documents across 4 categories: Constitution, Central Acts/Codes, Constitutional Amendment Acts, Supreme Court Judgments).
4. **Number of Queries / Examples:** 34 raw PDF documents, 5,658 pages, 2,412 text chunks.
5. **Baseline Configuration:** N/A (Data ingestion & knowledge base construction pipeline).
6. **Proposed-System Configuration:** PyMuPDF text extractor (`fitz`), structural legal chunker (target: 2000 chars, max: 4000 chars, overlap: 200 chars), InLegalBERT vector embedder (768d, L2-normalized), Regex & normalized legal entity/relationship extractor, FAISS `IndexFlatIP` vector indexer, Neo4j 5 property graph store.
7. **Model:** `law-ai/InLegalBERT` (768-dimensional dense embeddings).
8. **Retrieval Parameters:** Chunk target size: 2000 characters; Chunk max size: 4000 characters; Chunk overlap: 200 characters; Vector dimension: 768 float32.
9. **Evaluation Metrics:** Total pages extracted, total chunks created, raw legal entities extracted, raw legal relationships extracted, FAISS vectors persisted, elapsed execution time (seconds).
10. **Exact Numerical Results:**
    - Documents Discovered: 34
    - Documents Successfully Processed: 33
    - Documents Failed / Flagged OCR Required: 1 (`indira_nehru_gandhi_1975`)
    - Total Pages Extracted: 5,658
    - Total Chunks Created: 2,412
    - Total Raw Entities Extracted: 3,790
    - Total Raw Relationships Extracted: 17,056
    - FAISS Vectors Persisted: 2,412
    - Post-Deduplication Canonical Graph Nodes: 6,135
    - Post-Deduplication Canonical Graph Edges: 10,514
11. **Per-Query / Per-Document Results:** Available per document in [data/legal_corpus_v1/processed/ingestion_report.json](file:///c:/Projects/Juris%20AI/data/legal_corpus_v1/processed/ingestion_report.json). (See Table A for complete document-level statistics).
12. **Failed Cases:**
    - Document ID: `indira_gandhi_1975` (`judgements/supreme_court/02_indira_nehru_gandhi_raj_narain_1975.pdf`)
    - Status: `FAILED / OCR_REQUIRED`
    - Error Message: `"Text extraction failed because the PDF is image-only; OCR is deferred: PDF appears to be image-only / scanned. OCR is not supported; please upload a text-layer PDF."`
    - Output: Pages: 0, Chunks: 0, Entities: 0, Relationships: 0.
13. **Statistical Analysis:** N/A
14. **Runtime / Performance Measurements:**
    - Start Timestamp: `2026-10-02T11:23:58.314577+00:00`
    - Completion Timestamp: `2026-10-02T12:47:20.502065+00:00`
    - Elapsed Time: `5002.19` seconds (~83.37 minutes)
15. **Result File Path:** [data/legal_corpus_v1/processed/ingestion_report.json](file:///c:/Projects/Juris%20AI/data/legal_corpus_v1/processed/ingestion_report.json), [data/legal_corpus_v1/processed/ingestion_report.md](file:///c:/Projects/Juris%20AI/data/legal_corpus_v1/processed/ingestion_report.md)

---

## EXPERIMENT 2: End-to-End Legal Retrieval Strategy Benchmark

1. **Experiment Name:** Comparative Evaluation of Vector-Only, Graph-Only, and Hybrid GraphRAG Retrieval Strategies
2. **Research Objective:** To evaluate and compare the retrieval quality, citation verification accuracy, and temporal fact accuracy of dense vector retrieval (`VECTOR_ONLY`), multi-hop graph traversal (`GRAPH_ONLY`), and hybrid Reciprocal Rank Fusion retrieval (`HYBRID`) across canonical Indian legal research queries.
3. **Dataset:** Ground-truth evaluation dataset located in [server/data/evaluation/](file:///c:/Projects/Juris%20AI/server/data/evaluation/).
4. **Number of Queries / Examples:** 9 canonical ground-truth queries (`eval_q01` through `eval_q09`) spanning Constitutional, Statutory, Case Law, and Temporal categories.
5. **Baseline Configurations:**
   - `VECTOR_ONLY`: FAISS dense search using InLegalBERT embeddings ($K=5$) without graph expansion.
   - `GRAPH_ONLY`: Neo4j Cypher multi-hop graph traversal (depth 3) without vector seed scoring.
6. **Proposed-System Configuration (`HYBRID`):** Parallel FAISS vector search ($K=10$) + Neo4j Cypher multi-hop graph traversal (depth 3), Reciprocal Rank Fusion ($w_v = 0.50, w_g = 0.50$), Research Mode score boosting (`CONSTITUTIONAL` 1.25x, `STATUTORY` 1.25x, `CASE_LAW` 1.30x), temporal filtering, and context budgeting (max 2 chunks/page).
7. **Model:** `law-ai/InLegalBERT` (768d) for embeddings; `gpt-4o-mini` (API, temperature=0.0) for QA synthesis.
8. **Retrieval Parameters:** `top_k` = 5; `qa_max_evidence` = 5; `qa_max_context_chars` = 12000; `graph_max_hops` = 3; `graph_max_nodes` = 100.
9. **Evaluation Metrics:** Mean Recall@5, Mean Precision@5, Mean Reciprocal Rank (MRR), Citation Verification Rate, Temporal Fact Accuracy.
10. **Exact Numerical Results:**
    - `VECTOR_ONLY`: Mean Recall@5 = 0.6111, Mean Precision@5 = 0.2889, MRR = 0.6944, Citation Verification Rate = 1.0000, Temporal Fact Accuracy = 0.6667
    - `GRAPH_ONLY`: Mean Recall@5 = 0.5556, Mean Precision@5 = 0.2444, MRR = 0.5833, Citation Verification Rate = 1.0000, Temporal Fact Accuracy = 0.5000
    - `HYBRID`: Mean Recall@5 = 0.8889, Mean Precision@5 = 0.4222, MRR = 0.9444, Citation Verification Rate = 1.0000, Temporal Fact Accuracy = 1.0000
11. **Per-Query Results:**
    - Ground-truth evaluation dataset definition: [server/data/evaluation/questions.json](file:///c:/Projects/Juris%20AI/server/data/evaluation/questions.json) (See Table C & Table F for per-query expected items).
12. **Failed Cases:**
    - Queries involving un-indexed scanned PDF *Indira Gandhi (1975)* return 0 chunks from that specific document.
13. **Statistical Analysis:** Not recorded in repository files.
14. **Runtime / Performance Measurements:** Per-query execution latencies recorded in [docs/PHASE_14_HYBRID_GRAPHRAG.md](file:///c:/Projects/Juris%20AI/docs/PHASE_14_HYBRID_GRAPHRAG.md#L92-L99):
    - "What does Article 21 protect?": ~240ms
    - "How has the Supreme Court interpreted Article 21?": ~260ms
    - "Relationship between Sec 66A IT Act & Art 19": ~310ms
    - "What is the Basic Structure Doctrine?": ~220ms
    - "How did Maneka Gandhi change Article 21?": ~280ms
    - "How does Shreya Singhal relate Sec 66A to speech?": ~295ms
15. **Result File Path:** [docs/PROJECT_COMPLETION_REPORT.md](file:///c:/Projects/Juris%20AI/docs/PROJECT_COMPLETION_REPORT.md#L30-L35), [server/api/app/services/evaluation_runner.py](file:///c:/Projects/Juris%20AI/server/api/app/services/evaluation_runner.py)

---

## EXPERIMENT 3: Automated Test Suite Verification

1. **Experiment Name:** Backend Test Suite Execution Matrix
2. **Research Objective:** To verify system integrity, API route functionality, database migrations, graph traversal, ingestion pipeline, citation verification, and temporal reasoning across unit and integration tests.
3. **Dataset:** Test fixtures, synthetic legal chunks, and mock/live database sessions in `server/api/tests/`.
4. **Number of Queries / Examples:** 337 total test cases across 43 test files.
5. **Baseline Configuration:** N/A
6. **Proposed-System Configuration:** Executed via `pytest` (`uv run pytest`) using `asyncio` test runner and `httpx` async test client.
7. **Model:** Local test fixtures & `fake_neo4j` mock client.
8. **Retrieval Parameters:** N/A
9. **Evaluation Metrics:** Total tests passed, total tests failed, pass rate percentage.
10. **Exact Numerical Results:**
    - Total Backend Tests: 337
    - Passed Tests: 337
    - Failed Tests: 0
    - Pass Rate: 100.0%
11. **Per-Query Results:** Breakdown by test file:
    - `test_ingestion_*.py`: 24 tests passed
    - `test_graph_*.py`: 38 tests passed
    - `test_retrieval.py`: 18 tests passed
    - `test_qa_*.py`: 35 tests passed
    - `test_phase14_*.py`: 12 tests passed
    - `test_phase15_*.py`: 15 tests passed
    - `test_phase16_*.py`: 11 tests passed
    - `test_api_*.py` & `test_auth.py`: 184 tests passed
12. **Failed Cases:** None (0 failures).
13. **Statistical Analysis:** N/A
14. **Runtime / Performance Measurements:** Test suite executes in < 30 seconds.
15. **Result File Path:** [docs/PROJECT_COMPLETION_REPORT.md](file:///c:/Projects/Juris%20AI/docs/PROJECT_COMPLETION_REPORT.md#L7), [server/api/.pytest-phase1.xml](file:///c:/Projects/Juris%20AI/server/api/.pytest-phase1.xml)

---

# VERIFIED EXPERIMENTAL EVIDENCE TABLES

---

### TABLE A — Dataset Statistics

*Source File:* [data/legal_corpus_v1/processed/ingestion_report.json](file:///c:/Projects/Juris%20AI/data/legal_corpus_v1/processed/ingestion_report.json)

| Metric / Parameter | Quantity / Value |
|---|---|
| Ingestion Pipeline Started At | `2026-10-02T11:23:58.314577+00:00` |
| Ingestion Pipeline Completed At | `2026-10-02T12:47:20.502065+00:00` |
| Total Elapsed Seconds | `5002.19` |
| Total Documents Discovered | `34` |
| Total Documents Successfully Processed | `33` |
| Total Documents Failed / Flagged OCR | `1` |
| Total Pages Extracted | `5658` |
| Total Text Chunks Created | `2412` |
| Total Raw Entities Extracted | `3790` |
| Total Raw Relationships Extracted | `17056` |
| FAISS Vectors Persisted | `2412` |
| Post-Deduplication Canonical Graph Nodes | `6135` |
| Post-Deduplication Canonical Graph Edges | `10514` |

#### Detailed Per-Document Breakdown (`legal_corpus_v1`)

| Document ID | Status | Pages | Chunks | Entities | Relationships |
|---|---|---|---|---|---|
| `constitution_of_india` | SUCCESS | 402 | 145 | 1213 | 298 |
| `crpc_1973` | SUCCESS | 289 | 168 | 1892 | 1002 |
| `iea_1872` | SUCCESS | 54 | 20 | 238 | 125 |
| `ipc_1860` | SUCCESS | 140 | 52 | 268 | 110 |
| `phra_1993` | SUCCESS | 18 | 12 | 126 | 57 |
| `rpa_1951` | SUCCESS | 61 | 30 | 304 | 184 |
| `bnss_2023` | SUCCESS | 282 | 119 | 847 | 725 |
| `bns_2023` | SUCCESS | 112 | 45 | 139 | 105 |
| `bsa_2023` | SUCCESS | 54 | 28 | 110 | 77 |
| `it_act_2000` | SUCCESS | 44 | 23 | 183 | 135 |
| `rti_act_2005` | SUCCESS | 25 | 15 | 69 | 49 |
| `const_amendment_44` | SUCCESS | 16 | 6 | 95 | 81 |
| `const_amendment_42` | SUCCESS | 22 | 5 | 145 | 125 |
| `const_amendment_101` | SUCCESS | 7 | 3 | 26 | 24 |
| `const_amendment_73` | SUCCESS | 10 | 3 | 13 | 10 |
| `kesavananda_bharati_1973` | SUCCESS | 1006 | 486 | 3887 | 5538 |
| `indira_gandhi_1975` | FAILED / OCR_REQUIRED | 0 | 0 | 0 | 0 |
| `minerva_mills_1980` | SUCCESS | 85 | 74 | 533 | 771 |
| `ir_coelho_2007` | SUCCESS | 73 | 41 | 300 | 384 |
| `l_chandra_kumar_1997` | SUCCESS | 28 | 19 | 197 | 251 |
| `ep_royappa_1974` | SUCCESS | 31 | 5 | 28 | 28 |
| `maneka_gandhi_1978` | SUCCESS | 110 | 74 | 482 | 571 |
| `shayara_bano_2017` | SUCCESS | 5 | 1 | 2 | 0 |
| `romesh_thappar_1950` | SUCCESS | 8 | 6 | 72 | 72 |
| `bennett_coleman_1973` | SUCCESS | 17 | 13 | 83 | 83 |
| `shreya_singhal_2015` | SUCCESS | 41 | 24 | 237 | 229 |
| `ak_gopalan_1950` | SUCCESS | 112 | 81 | 679 | 809 |
| `puttaswamy_privacy_2017` | SUCCESS | 547 | 196 | 831 | 853 |
| `common_cause_2018` | SUCCESS | 173 | 69 | 448 | 395 |
| `sr_bommai_1994` | SUCCESS | 152 | 72 | 562 | 841 |
| `vishaka_1997` | SUCCESS | 8 | 7 | 30 | 34 |
| `nalsa_2014` | SUCCESS | 35 | 12 | 95 | 101 |
| `navtej_johar_2018` | SUCCESS | 243 | 75 | 423 | 385 |
| `puttaswamy_aadhaar_2018` | SUCCESS | 1448 | 483 | 2742 | 2604 |

---

### TABLE B — Baseline vs Proposed System

*Source File:* [docs/PROJECT_COMPLETION_REPORT.md](file:///c:/Projects/Juris%20AI/docs/PROJECT_COMPLETION_REPORT.md#L30-L35)

| System / Strategy | Mean Recall@5 | Mean Precision@5 | Mean Reciprocal Rank (MRR) | Citation Verification Rate | Temporal Fact Accuracy |
|---|---|---|---|---|---|
| `VECTOR_ONLY` (Baseline 1) | 0.6111 | 0.2889 | 0.6944 | 1.0000 | 0.6667 |
| `GRAPH_ONLY` (Baseline 2) | 0.5556 | 0.2444 | 0.5833 | 1.0000 | 0.5000 |
| `HYBRID` (Proposed System) | 0.8889 | 0.4222 | 0.9444 | 1.0000 | 1.0000 |

---

### TABLE C — Retrieval Performance

*Source File:* [docs/PHASE_14_HYBRID_GRAPHRAG.md](file:///c:/Projects/Juris%20AI/docs/PHASE_14_HYBRID_GRAPHRAG.md#L92-L99)

| Sample Evaluation Query | Retrieval Strategy | Latency (ms) | Status | Evidence Count | Citation Count | Multi-Hop Paths |
|---|---|---|---|---|---|---|
| "What does Article 21 protect?" | Hybrid | ~240ms | Answered | 5 | 1 | 2 |
| "How has the Supreme Court interpreted Article 21?" | Hybrid | ~260ms | Answered | 5 | 2 | 3 |
| "Relationship between Sec 66A IT Act & Art 19" | Hybrid | ~310ms | Answered | 5 | 2 | 1 (3-hop) |
| "What is the Basic Structure Doctrine?" | Hybrid | ~220ms | Answered | 4 | 1 | 2 |
| "How did Maneka Gandhi change Article 21?" | Hybrid | ~280ms | Answered | 5 | 2 | 2 |
| "How does Shreya Singhal relate Sec 66A to speech?" | Hybrid | ~295ms | Answered | 5 | 2 | 1 (3-hop) |

---

### TABLE D — Multi-Hop Performance

*Source File:* [docs/PHASE_14_HYBRID_GRAPHRAG.md](file:///c:/Projects/Juris%20AI/docs/PHASE_14_HYBRID_GRAPHRAG.md#L96)

| Multi-Hop Query Target | Anchor Entities | Intermediary Bridge Entity | Final Target Entity | Max Depth | Discovered Paths | Status |
|---|---|---|---|---|---|---|
| Relationship between Sec 66A IT Act & Art 19 | `Section 66A` (IT Act, 2000), `Article 19` (Constitution) | `Shreya Singhal v. Union of India` (2015) | `Section 66A` (Struck Down) | 3 | 1 (3-hop) | Answered |
| Relationship between Sec 66A & Freedom of Speech | `Section 66A`, `Article 19(1)(a)` | `Shreya Singhal v. Union of India` (2015) | `Article 19(1)(a)` | 3 | 1 (3-hop) | Answered |
| Article 21 Judicial Interpretation Expansion | `Article 21` (Constitution), `A.K. Gopalan` (1950) | `Maneka Gandhi v. Union of India` (1978) | `Article 21` (Expanded Scope) | 3 | 3 | Answered |

---

### TABLE E — Temporal Reasoning Performance

*Source File:* [server/data/evaluation/questions.json](file:///c:/Projects/Juris%20AI/server/data/evaluation/questions.json), [docs/PROJECT_COMPLETION_REPORT.md](file:///c:/Projects/Juris%20AI/docs/PROJECT_COMPLETION_REPORT.md#L30-L35)

| Strategy | Temporal Query Accuracy (Target Year / Operator / Version Resolution) |
|---|---|
| `VECTOR_ONLY` | 0.6667 |
| `GRAPH_ONLY` | 0.5000 |
| `HYBRID` | 1.0000 |

---

### TABLE F — Citation Grounding Performance

*Source File:* [docs/PROJECT_COMPLETION_REPORT.md](file:///c:/Projects/Juris%20AI/docs/PROJECT_COMPLETION_REPORT.md#L30-L35)

| Strategy | Total Citations Generated Across Queries | Total Verified Citations | Citation Verification Rate |
|---|---|---|---|
| `VECTOR_ONLY` | Variable per query | Verified against chunk provenance | 1.0000 |
| `GRAPH_ONLY` | Variable per query | Verified against chunk provenance | 1.0000 |
| `HYBRID` | Variable per query | Verified against chunk provenance | 1.0000 |

---

### TABLE G — Ablation Study

*Source File:* [docs/PROJECT_COMPLETION_REPORT.md](file:///c:/Projects/Juris%20AI/docs/PROJECT_COMPLETION_REPORT.md#L30-L35)

| Variant | Component Included | Component Removed | Mean Recall@5 | Mean Precision@5 | MRR | Temporal Fact Accuracy |
|---|---|---|---|---|---|---|
| Full `HYBRID` System | FAISS Dense Vector + Neo4j Graph RRF | None | 0.8889 | 0.4222 | 0.9444 | 1.0000 |
| `VECTOR_ONLY` Ablation | FAISS Dense Vector Retrieval | Neo4j Graph Expansion | 0.6111 | 0.2889 | 0.6944 | 0.6667 |
| `GRAPH_ONLY` Ablation | Neo4j Cypher Multi-Hop Graph | FAISS Dense Vector Search | 0.5556 | 0.2444 | 0.5833 | 0.5000 |

---

### TABLE H — Error Analysis

*Source File:* [data/legal_corpus_v1/processed/ingestion_report.json](file:///c:/Projects/Juris%20AI/data/legal_corpus_v1/processed/ingestion_report.json#L193-L202), [docs/PROJECT_COMPLETION_REPORT.md](file:///c:/Projects/Juris%20AI/docs/PROJECT_COMPLETION_REPORT.md#L49-L55)

| Document ID / Query Target | Category | Error / Symptom Description | System Behavior / Handling |
|---|---|---|---|
| `indira_gandhi_1975` (`02_indira_nehru_gandhi_raj_narain_1975.pdf`) | Ingestion / Text Extraction | Scanned raster image PDF without embedded text stream | Extractor flags `FAILED / OCR_REQUIRED`; 0 pages, 0 chunks, 0 entities inserted into index |
| Numerical Section Queries (e.g. IT Act Sec 66 vs Sec 66A) | Dense Retrieval Noise | InLegalBERT token embeddings share high cosine similarity for numerical section strings | Graph node filtering matches canonical entity ID (`section:it_act_2000:66a`) to remove non-exact sections |
| Foundational Articles (e.g. Article 21) at Depth > 3 | Graph Traversal Noise | High node degree of Article 21 attracts unrelated precedent nodes | Bounded graph depth cap (default 3, max 5) and candidate node limit (100) applied |
| Unindexed Amendments | Temporal Resolution | Effective date range missing from milestone registry | Resolves to `status="UNKNOWN"` with `temporal_confidence=0.0`; does not manufacture dates |
