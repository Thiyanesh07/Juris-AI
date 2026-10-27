# Quantitative Metrics & Experimental Evaluation Audit
## Juris AI: GraphRAG-Based Indian Legal Reasoning System
**Document ID:** `reports/project_audit/04_metrics_and_evaluation.md`  
**System Root:** `c:\Projects\Juris AI`  
**Authoritative Evidence:** `FINAL_EXPERIMENTAL_RESULTS.md`, `data/legal_corpus_v1/processed/ingestion_report.json`, `server/data/evaluation/`, `docs/PROJECT_COMPLETION_REPORT.md`  

---

### 1. Conceptual Distinction Between Metric Classes

In academic legal information retrieval, presenting distinct measurement types as interchangeable constitutes a critical methodological flaw. The audit establishes four distinct categories:

1. **Retrieval Quality Against Ground-Truth Relevance Judgments:** Evaluates whether retrieved legal chunks match human-annotated ground-truth legal authorities (Recall@k, Precision@k, MRR).
2. **FAISS Index Agreement Against Exact Search Baseline:** Evaluates whether an approximate index (e.g., IVF or HNSW) retrieves the identical items as brute-force search. In Juris AI, the index is `IndexFlatIP`, meaning **nearest-neighbour search agreement is mathematically 1.0 (100%)** with zero approximation error.
3. **Semantic Similarity Scores:** Raw inner-product cosine scores output by InLegalBERT ($[-1.0, 1.0]$). These reflect token distribution proximity in dense vector space, not legal validity or relevance.
4. **End-to-End Answer Correctness:** Evaluates whether the synthesized answer is factually correct, logically coherent, temporally valid, and properly supported by citations without hallucinations.

---

### 2. Metric Inventory & Verified Measurements

#### Experiment 1: Ingestion & Knowledge Base Construction
- **Dataset:** `legal_corpus_v1` (34 raw Indian legal PDF documents).
- **Execution Evidence:** `data/legal_corpus_v1/processed/ingestion_report.json:L1-L15`.
- **Timestamp:** `2026-10-02T11:23:58.314577+00:00` to `2026-10-02T12:47:20.502065+00:00`.
- **Elapsed Ingestion Duration:** 5,002.19 seconds (~83.37 minutes).

| Measured Metric | Exact Value | Source File / Artifact | Evidence Type |
|---|---|---|---|
| **Discovered Documents** | 34 | `data/legal_corpus_v1/processed/ingestion_report.json:L5` | Direct Record |
| **Successfully Processed Documents** | 33 | `data/legal_corpus_v1/processed/ingestion_report.json:L6` | Direct Record |
| **Failed Documents (Scanned PDF)** | 1 (`indira_gandhi_1975`) | `data/legal_corpus_v1/processed/ingestion_report.json:L156` | Direct Record |
| **Total Pages Extracted** | 5,658 | `data/legal_corpus_v1/processed/ingestion_report.json:L8` | Direct Record |
| **Total Text Chunks Created** | 2,412 | `data/legal_corpus_v1/processed/ingestion_report.json:L9` | Direct Record |
| **Total Raw Legal Entities** | 3,790 | `data/legal_corpus_v1/processed/ingestion_report.json:L10` | Direct Record |
| **Total Raw Legal Relations** | 17,056 | `data/legal_corpus_v1/processed/ingestion_report.json:L11` | Direct Record |
| **FAISS Vectors Persisted** | 2,412 | `data/legal_corpus_v1/processed/ingestion_report.json:L12` | Direct Record |
| **Vector Matrix Dimensions** | 2,412 $\times$ 768 | `data/indexes/legal_chunks/embeddings.npy` (7,409,792 B) | Artifact Calculation |
| **Canonical Neo4j Nodes** | 6,135 | `FINAL_EXPERIMENTAL_RESULTS.md:L30`, `docs/FINAL_ARCHITECTURE.md` | Direct Record |
| **Canonical Neo4j Relationships** | 10,514 | `FINAL_EXPERIMENTAL_RESULTS.md:L31`, `docs/FINAL_ARCHITECTURE.md` | Direct Record |

#### Experiment 2: Comparative Retrieval Benchmark
- **Dataset:** Ground-truth legal queries in `server/data/evaluation/questions.json` (9 canonical queries) with ground-truth citations, entities, and temporal milestones.
- **Evaluated Strategies:**
  - `VECTOR_ONLY`: FAISS dense search using InLegalBERT embeddings ($K=5$) without graph expansion.
  - `GRAPH_ONLY`: Neo4j Cypher multi-hop graph traversal (depth 3) without vector seed scoring.
  - `HYBRID`: Parallel FAISS vector search ($K=10$) + Neo4j Cypher multi-hop traversal (depth 3) blended via Reciprocal Rank Fusion ($w_v = 0.50, w_g = 0.50$) with Research Mode multipliers.
- **Synthesis Model:** `gpt-4o-mini` (API, temperature=0.0) / `gemini-1.5-flash`.
- **Source File:** `docs/PROJECT_COMPLETION_REPORT.md:L30-L35`, `FINAL_EXPERIMENTAL_RESULTS.md:L60-L64`.

| Metric Name | Metric Definition | `VECTOR_ONLY` | `GRAPH_ONLY` | `HYBRID` (Proposed) | Relative Improvement |
|---|---|---|---|---|---|
| **Mean Recall@5** | $\frac{\text{Relevant Chunks Retrieved in Top 5}}{\text{Total Expected Relevant Chunks}}$ | **0.6111** | **0.5556** | **0.8889** | **+45.4%** over vector-only |
| **Mean Precision@5** | $\frac{\text{Relevant Chunks Retrieved in Top 5}}{5}$ | **0.2889** | **0.2444** | **0.4222** | **+46.1%** over vector-only |
| **Mean Reciprocal Rank (MRR)** | $\frac{1}{\|Q\|} \sum_{q=1}^{\|Q\|} \frac{1}{\text{rank}_q}$ | **0.6944** | **0.5833** | **0.9444** | **+36.0%** over vector-only |
| **Citation Verification Rate** | $\frac{\text{Verified Legal Citations}}{\text{Total Generated Legal Citations}}$ | **1.0000** (100%) | **1.0000** (100%) | **1.0000** (100%) | Parity (provenance filter) |
| **Temporal Fact Accuracy** | $\frac{\text{Queries with Valid Historical State}}{\text{Total Temporal Queries}}$ | **0.6667** | **0.5000** | **1.0000** (100%) | **+50.0%** over vector-only |

#### Experiment 3: Observed Query Execution Latencies
- **Source File:** `docs/PHASE_14_HYBRID_GRAPHRAG.md:L92-L99`.
- **Status:** Indicative local development observations (single-query measurements).

| Query Target | Research Category | Observed Latency | Evidence Count | Multi-Hop Paths |
|---|---|---|---|---|
| "What does Article 21 protect?" | `CONSTITUTIONAL` | ~240 ms | 5 chunks | 2 paths |
| "How has the Supreme Court interpreted Article 21?" | `CONSTITUTIONAL` | ~260 ms | 5 chunks | 3 paths |
| "Relationship between Sec 66A IT Act & Art 19" | `STATUTORY` | ~310 ms | 5 chunks | 1 path (3-hop) |
| "What is the Basic Structure Doctrine?" | `CONSTITUTIONAL` | ~220 ms | 4 chunks | 2 paths |
| "How did Maneka Gandhi change Article 21?" | `CASE_LAW` | ~280 ms | 5 chunks | 2 paths |
| "How does Shreya Singhal relate Sec 66A to speech?" | `CASE_LAW` | ~295 ms | 5 chunks | 1 path (3-hop) |

---

### 3. Metric Evaluation Procedures & Formulas

1. **Recall@k:**
   $$\text{Recall}@k(q) = \frac{|\mathcal{R}_q \cap \mathcal{T}_{q, k}|}{|\mathcal{R}_q|}$$
   where $\mathcal{R}_q$ is the set of ground-truth relevant chunks/entities for query $q$, and $\mathcal{T}_{q, k}$ is the set of top-$k$ retrieved chunks.
2. **Precision@k:**
   $$\text{Precision}@k(q) = \frac{|\mathcal{R}_q \cap \mathcal{T}_{q, k}|}{k}$$
3. **Mean Reciprocal Rank (MRR):**
   $$\text{MRR} = \frac{1}{|Q|} \sum_{q=1}^{|Q|} \frac{1}{\min \{r : \text{item at rank } r \in \mathcal{R}_q\} \cup \{\infty\}}$$
4. **Reciprocal Rank Fusion (RRF) Formula:**
   For a candidate chunk $c$ present in dense rank $r_d(c)$ and graph rank $r_g(c)$:
   $$\text{RRF}(c) = \frac{w_v}{k_{\text{rrf}} + r_d(c)} + \frac{w_g}{k_{\text{rrf}} + r_g(c)}$$
   where $k_{\text{rrf}} = 60$, $w_v = 0.50$, $w_g = 0.50$ (`server/api/app/rag/pipeline.py:L267-L274`).

---

### 4. Classification of Existing Results

| Result Identifier | Category | Claim Legality in Report |
|---|---|---|
| 34 PDFs / 2,412 Chunks / 5,658 Pages | **Existing Measured Result** | Permitted as verified dataset fact. |
| 6,135 Nodes / 10,514 Edges | **Existing Measured Result** | Permitted as verified graph size. |
| Hybrid Recall@5 = 0.8889 vs Vector 0.6111 | **Existing Measured Result** | Permitted as verified result on the 9-query benchmark set. Must state $N=9$. |
| Hybrid MRR = 0.9444 vs Vector 0.6944 | **Existing Measured Result** | Permitted as verified result on the 9-query benchmark set. Must state $N=9$. |
| Citation Verification = 100% | **Existing Measured Result** | Permitted as verified result; must explain that verification filter rejects ungrounded citations. |
| Latency ~220ms – ~310ms | **Qualitative Manual Observation** | Permitted only as indicative single-run observation. Must not be called a statistically stable latency benchmark. |
| Tree of Thoughts Performance | **Not found** | **STRICTLY FORBIDDEN**. Must not appear in report. |

---

### 5. Proposed Future Evaluation Plan (For Post-Audit / Final Dissertation)

To extend the project beyond the undergraduate mini-project scope into a full academic publication, the following evaluation plan is recommended:

#### E1. Expanded Legal Query Benchmark Dataset
Construct an expanded, expert-annotated legal benchmark of 50–100 queries:
- **Direct Statutory Queries (25%):** Specific Section/Article definitions (e.g., Section 420 IPC, Article 32).
- **Multi-Hop Judicial Interpretation Queries (35%):** Requiring traversal across statutes and landmark cases (e.g., *Navtej Johar* $\rightarrow$ Section 377 IPC $\rightarrow$ Article 14, 15, 21).
- **Temporal & Amendment Queries (20%):** Comparing statutory wording across amendment acts (e.g., Article 31 pre-44th Amendment vs post-44th Amendment; IPC Section 302 vs BNS Section 103).
- **Unanswerable / Corpus-Out-of-Scope Queries (20%):** Assessing clean abstention rate on topics absent from the 34 source PDFs (e.g., Patent Act, GST Act provisions).

#### E2. Retrieval Baselines for Comparative Study
Evaluate under identical corpus chunks and hardware conditions:
1. **BM25 (Lexical Baseline):** RankBM25 on tokenized chunk texts.
2. **Dense Vector Retrieval (Vector-Only):** InLegalBERT 768d FAISS `IndexFlatIP`.
3. **Graph Traversal (Graph-Only):** Cypher multi-hop traversal without dense seed scoring.
4. **Hybrid RRF (Juris AI Full Pipeline):** InLegalBERT + Neo4j Cypher + RRF.
5. **Cross-Encoder Reranking (Optional Ablation):** Dense + Graph candidates reranked via BAAI bge-reranker.

#### E3. Repeated Latency & Profiling Protocol
- Execute 5 warm-up queries.
- Run 100 repeated queries under concurrency levels $C \in \{1, 5, 10\}$.
- Record:
  - Query embedding latency ($T_{\text{embed}}$).
  - FAISS search latency ($T_{\text{faiss}}$).
  - Neo4j Cypher traversal latency ($T_{\text{graph}}$).
  - Evidence fusion latency ($T_{\text{fusion}}$).
  - LLM synthesis latency ($T_{\text{llm}}$).
  - End-to-end latency ($T_{\text{total}}$).
- Report median (p50), 95th percentile (p95), and 99th percentile (p99).

#### E4. Graph Contribution Ablation Study
Measure the exact marginal delta provided by the knowledge graph:
$$\Delta \text{Recall} = \text{Recall}_{\text{hybrid}} - \text{Recall}_{\text{vector}}$$
Analyze the breakdown: on direct 1-hop queries, $\Delta \text{Recall} \approx 0$; on multi-hop bridge queries (depth $\ge 2$), $\Delta \text{Recall}$ increases significantly (+30% to +50%), empirically validating the GraphRAG hypothesis.
