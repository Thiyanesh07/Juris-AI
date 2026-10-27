# Report Writer Handoff Context: Technical Grounding Document
## Juris AI: GraphRAG-Based Indian Legal Reasoning System
**Document ID:** `reports/project_audit/10_report_writer_context.md`  
**Intended Recipient:** Subsequent AI Agent or Technical Writer Generating the Final Mini-Project Report  
**System Root:** `c:\Projects\Juris AI`  
**Audit Deliverables Directory:** `reports/project_audit/`  

---

> ### INSTRUCTIONS FOR THE REPORT-WRITING AGENT:
> You are tasked with drafting the complete undergraduate engineering academic report for **Juris AI** (Chapters 1 through 6).
> **STRICT COMPLIANCE MANDATE:** Every architectural description, mathematical equation, metric value, test count, and technical claim in your report MUST originate from this document and the associated audit deliverables in `reports/project_audit/`.
> **DO NOT FABRICATE OR HALLUCINATE** any numbers, accuracy percentages, model names, or algorithmic features.
> If a concept is designated as **STRICTLY PROHIBITED** (such as Tree of Thoughts), you must NOT include it in the report under any circumstance.

---

### 1. Verified Project Identity & Scope

- **Official Project Title:** *Juris AI: A GraphRAG-Based System for Multi-Hop Reasoning Over Indian Constitutional and Statutory Law*
- **Domain:** Artificial Intelligence, Legal Informatics, Natural Language Processing, Information Retrieval, Knowledge Graphs.
- **Academic Level:** Undergraduate Engineering Mini-Project / Capstone Project (B.E. / B.Tech in Computer Science and Engineering).
- **Core Problem Addressed:** Conventional dense retrieval systems fail to answer complex Indian legal queries that require traversing multi-hop statutory and judicial dependencies across disparate documents (e.g., connecting Constitutional Article 19(1)(a) through Supreme Court precedent *Shreya Singhal v. Union of India* to Section 66A of the Information Technology Act, 2000). Furthermore, standard vector search cannot distinguish between current active law and repealed/superseded provisions.
- **Core Technical Solution:** A Hybrid GraphRAG pipeline fusing legal-domain dense vector search (`law-ai/InLegalBERT` in FAISS `IndexFlatIP`) with multi-hop property knowledge graph traversal (Neo4j 5 Community) via Reciprocal Rank Fusion ($k=60$), integrated with deterministic legal version resolution and provenance-backed citation verification.

---

### 2. Verified Technology Stack & Version Matrix

| Subsystem | Component / Library | Verified Version | Purpose in System |
|---|---|---|---|
| **Backend Framework** | FastAPI | `0.115.x` | High-performance asynchronous REST API framework |
| **Language Runtime** | Python | `3.12.x` | Core backend runtime environment |
| **ASGI Server** | Uvicorn | `0.34.x` | Production ASGI web server |
| **Relational ORM** | SQLAlchemy | `2.0.x` (Async) | Asynchronous ORM for PostgreSQL |
| **Relational Driver** | `asyncpg` / `psycopg` | `0.29.x` / `3.2.x` | Non-blocking PostgreSQL database driver |
| **Schema Migrations** | Alembic | `1.13.x` | Version-controlled relational database migrations |
| **Schema Validation** | Pydantic v2 | `2.10.x` | Request/response data contract enforcement |
| **Vector Search Engine** | `faiss-cpu` | `1.10.x` | Exact inner product search (`IndexFlatIP`) |
| **Graph Database** | Neo4j Community | `5.x` | Property graph storing legal entities & triples |
| **Graph Client** | `neo4j` (async driver) | `5.26.x` | Asynchronous Bolt protocol driver |
| **Embedding Model** | `law-ai/InLegalBERT` | Checkpoint (Hugging Face) | 768-dimensional legal domain text encoder |
| **ML Inference Engine** | ONNX Runtime | `1.18.x` | Optimized CPU inference for InLegalBERT embeddings |
| **PDF Extraction** | PyMuPDF (`fitz`) | `1.24.x` | Native PDF block and page text extraction |
| **LLM Provider** | OpenAI / Google GenAI | API (`gpt-4o-mini` / `gemini-1.5-flash`) | Server-side constrained answer synthesis |
| **Frontend Framework** | Next.js | `16.0.10` | React server-side rendering & portal routing |
| **UI Library** | React | `19.2.0` | Client component architecture |
| **Styling Engine** | TailwindCSS | `4.1.9` | Utility-first responsive design tokens |
| **Icons & Visuals** | Lucide React / Three.js | `0.454.0` / `0.183.2` | Interface icons and 3D landing showcase |

---

### 3. Legal Document Ingestion & Corpus Scale

The authoritative legal corpus (`legal_corpus_v1`) comprises **34 raw PDF documents** across 4 legal tiers:
1. **The Constitution of India:** `englishconstitution.pdf` (402 pages, 145 chunks, 1,213 entities).
2. **Major Central Statutory Acts (10 Acts):**
   - Code of Criminal Procedure, 1973 (`crpc_1973`): 289 pages, 168 chunks.
   - Indian Penal Code, 1860 (`ipc_1860`): 140 pages, 52 chunks.
   - Indian Evidence Act, 1872 (`iea_1872`): 54 pages, 20 chunks.
   - Information Technology Act, 2000 (`it_act_2000`): 44 pages, 23 chunks.
   - Right to Information Act, 2005 (`rti_act_2005`): 25 pages, 15 chunks.
   - Protection of Human Rights Act, 1993 (`phra_1993`): 18 pages, 12 chunks.
   - Representation of the People Act, 1951 (`rpa_1951`): 61 pages, 30 chunks.
   - Bharatiya Nyaya Sanhita, 2023 (`bns_2023`): 112 pages, 45 chunks.
   - Bharatiya Nagarik Suraksha Sanhita, 2023 (`bnss_2023`): 282 pages, 119 chunks.
   - Bharatiya Sakshya Adhiniyam, 2023 (`bsa_2023`): 54 pages, 28 chunks.
3. **Constitutional Amendment Acts (4 Amendments):**
   - 42nd Amendment Act, 1976 (`const_amendment_42`): 22 pages, 5 chunks.
   - 44th Amendment Act, 1978 (`const_amendment_44`): 16 pages, 6 chunks.
   - 73rd Amendment Act, 1992 (`const_amendment_73`): 10 pages, 3 chunks.
   - 101st Amendment Act, 2016 (`const_amendment_101`): 7 pages, 3 chunks.
4. **Landmark Supreme Court Judgments (19 Judgments):**
   - *Kesavananda Bharati v. State of Kerala (1973)*: 1,006 pages, 486 chunks (Basic Structure Doctrine).
   - *Maneka Gandhi v. Union of India (1978)*: 110 pages, 74 chunks (Substantive Due Process, Article 21).
   - *Shreya Singhal v. Union of India (2015)*: 41 pages, 24 chunks (Struck down Section 66A IT Act).
   - *K.S. Puttaswamy v. Union of India (Privacy, 2017)*: 547 pages, 196 chunks (Right to Privacy under Article 21).
   - *K.S. Puttaswamy v. Union of India (Aadhaar, 2018)*: 1,448 pages, 483 chunks.
   - *A.K. Gopalan v. State of Madras (1950)*: 112 pages, 81 chunks (Literal procedure established by law).
   - *S.R. Bommai v. Union of India (1994)*: 152 pages, 72 chunks (Federalism, Article 356).
   - *Minerva Mills Ltd. v. Union of India (1980)*: 85 pages, 74 chunks (Harmony between Fundamental Rights and DPSP).
   - *I.R. Coelho v. State of Tamil Nadu (2007)*: 73 pages, 41 chunks (Ninth Schedule judicial review).
   - *Navtej Singh Johar v. Union of India (2018)*: 243 pages, 75 chunks (Decriminalized Section 377 IPC).
   - *Common Cause v. Union of India (2018)*: 173 pages, 69 chunks (Passive euthanasia and living will).
   - Plus *Vishaka (1997)*, *NALSA (2014)*, *Shayara Bano (2017)*, *Romesh Thappar (1950)*, *Bennett Coleman (1973)*, *E.P. Royappa (1974)*, *L. Chandra Kumar (1997)*.
   - *Indira Nehru Gandhi v. Raj Narain (1975)*: 1 document flagged `FAILED / OCR_REQUIRED` (scanned raster image PDF without text layer).

- **Total Ingestion Quantities:**
  - Documents Discovered: **34** | Documents Ingested: **33** | Documents Flagged OCR: **1**
  - Total Pages Processed: **5,658**
  - Total Text Chunks Created: **2,412**
  - Total Raw Entities: **3,790** | Canonical Deduplicated Graph Nodes: **6,135**
  - Total Raw Relationships: **17,056** | Canonical Provenance Edges: **10,514**
  - Total FAISS Vectors Persisted: **2,412** (768-dim float32)

---

### 4. Technical Subsystem Implementation Details

#### 4.1 InLegalBERT Encoding & FAISS Search
- **Text Embedding Formula:** Attention-mask-aware mean pooling over the final hidden states $\mathbf{h}_i$:
  $$\mathbf{u} = \frac{\sum_{i=1}^{L} m_i \mathbf{h}_i}{\sum_{i=1}^{L} m_i}, \quad \mathbf{v} = \frac{\mathbf{u}}{\max(\|\mathbf{u}\|_2, 10^{-12})}$$
- **FAISS Configuration:** `faiss.IndexFlatIP(768)`. Because all embeddings $\mathbf{v}$ are $L_2$-normalized, inner product equals cosine similarity:
  $$\langle \mathbf{q}, \mathbf{d} \rangle = \cos(\mathbf{q}, \mathbf{d})$$
- **Persisted Files:** `index.faiss` (7.41 MB), `embeddings.npy` (7.41 MB), `metadata.json` (17.5 MB).

#### 4.2 Knowledge Graph Schema & Multi-Hop Traversal
- **Graph Engine:** Neo4j 5 Community.
- **Node Labels (14):** `Article`, `Section`, `Act`, `Amendment`, `Judgment`, `Court`, `Doctrine`, `Person`, `Concept`, `Organization`, `Document`, `Chunk`, `Rule`, `Regulation`.
- **Relationships (10):** `AMENDS`, `MODIFIES`, `SUPERSEDES`, `STRUCK_DOWN`, `INTERPRETS`, `DEFINES`, `REFERENCES`, `CITES`, `OVERRULES`, `BELONGS_TO`.
- **Relationship Provenance Attributes:** `provenance_key` (SHA-256 hash), `source_document_id`, `source_chunk_id`, `page_start`, `page_end`, `evidence_text`.
- **Traversal Algorithm:** Parameterized Cypher query traversing up to depth 5 (default 3 hops) with cycle prevention (`ALL(x IN nodes(p) WHERE single(y IN nodes(p) WHERE y = x))`).

#### 4.3 Reciprocal Rank Fusion & Research Modes
- **Fusion Formula:**
  $$\text{Score}(c) = \frac{0.50}{60 + r_{\text{vector}}(c)} + \frac{0.50}{60 + r_{\text{graph}}(c)}$$
- **Research Mode Multipliers:**
  - `CONSTITUTIONAL`: Boosts Constitutional Articles and Bench Judgments by $1.25\times$.
  - `STATUTORY`: Boosts statutory Acts and Sections by $1.25\times$.
  - `CASE_LAW`: Boosts judicial precedents and overruling relationships by $1.30\times$.
  - `COMPREHENSIVE`: Uniform baseline scoring ($1.00\times$).
- **Context Budgeting:** Strict deduplication cap allowing at most 2 chunks per page per document to prevent local text concentration.

#### 4.4 Temporal & Version Resolution Subsystem
- **Status Categories:** `IN_FORCE`, `SUPERSEDED`, `REPEALED`, `NOT_YET_IN_FORCE`, `HISTORICAL`, `UNKNOWN`.
- **Temporal Expressions Handled:** `BEFORE`, `AFTER`, `SINCE`, `UNTIL`, explicit years (e.g., 1978), and amendment mentions.
- **Conservative Date Rule:** If dates are unmapped, status resolves to `UNKNOWN` with confidence `0.0`. Never manufactures dates or assumes current status without evidence.

#### 4.5 Citation Grounding & LLM Self-Correction
- **Verification Rule:** Regex matching across raw chunk texts for standard citations:
  - Supreme Court Cases: `(YYYY) V SCC P`
  - All India Reporter: `AIR YYYY SC P`
  - Supreme Court Reports: `(YYYY) V SCR P`
  - Constitutional / Statutory: `Article N`, `Section N`
- **Self-Correction Feedback Loop:** If LLM generates an invalid or ungrounded citation, the system intercepts the error and re-prompts the model with a diagnostic feedback message (`build_correction_user_message`) up to 2 times. If verification still fails, the system returns a safe, ungrounded abstention message.

---

### 5. Verified Experimental Results for Chapter 4 & 5

#### Retrieval Benchmark Results (9 Canonical Legal Queries)
*Source:* `server/data/evaluation/questions.json`, `docs/PROJECT_COMPLETION_REPORT.md:L30-L35`

| Strategy | Mean Recall@5 | Mean Precision@5 | MRR | Citation Verification Rate | Temporal Fact Accuracy |
|---|---|---|---|---|---|
| `VECTOR_ONLY` (Baseline 1) | 0.6111 | 0.2889 | 0.6944 | 1.0000 | 0.6667 |
| `GRAPH_ONLY` (Baseline 2) | 0.5556 | 0.2444 | 0.5833 | 1.0000 | 0.5000 |
| **`HYBRID` (Proposed System)** | **0.8889** | **0.4222** | **0.9444** | **1.0000** | **1.0000** |

- **Key Statistical Conclusions to State:**
  - Hybrid GraphRAG achieves **+45.4% higher Recall@5** (0.8889 vs 0.6111) than vector-only search.
  - Hybrid GraphRAG achieves **+36.0% higher Mean Reciprocal Rank (MRR)** (0.9444 vs 0.6944), demonstrating that relevant legal authorities appear at Rank 1 in almost all evaluated queries.
  - On temporal reasoning queries, Hybrid GraphRAG achieves **100% accuracy** versus **66.7%** for vector search, demonstrating that vector proximity cannot detect repealed statutory provisions.
  - Both vector and hybrid systems achieve **100% citation verification rate** because ungrounded citations are systematically pruned before user output.

#### Indicative Latency Observations (Local Development Environment)
- Query Embedding: ~15–25 ms (ONNX Runtime, CPU).
- FAISS Search: ~2–5 ms (Exact brute force across 2,412 vectors).
- Neo4j Multi-Hop Traversal (Depth 3): ~40–80 ms.
- Evidence Fusion & Reranking: ~5–10 ms.
- End-to-End Latency: ~220 ms to ~310 ms on representative queries.

#### Test Execution Evidence
- Total Backend Tests: **337 passing out of 337 (100% pass rate)**.
- Discovered Test Files: 68 in `server/api/tests/`.
- Frontend Test Files: 8 in `client/admin/tests/` and `client/user/tests/` (all passing).
- Next.js Client Builds: `client/user`, `client/admin`, and `client/landing` build cleanly with 0 TypeScript/ESLint errors.

---

### 6. Critical Boundaries: Claims to Make vs Claims to Avoid

#### CLAIMS PERMITTED (With Strict Wording Guidance)
1. Permitted to claim that Juris AI introduces an effective Hybrid GraphRAG system combining dense vector search and multi-hop property knowledge graph traversal for Indian Constitutional and Statutory Law.
2. Permitted to claim that the legal knowledge graph indexes 6,135 entities and 10,514 relationships from 33 genuine Indian legal documents (5,658 pages, 2,412 chunks).
3. Permitted to claim that the proposed hybrid retrieval engine outperformed vector-only and graph-only baselines on an empirical pilot benchmark of 9 canonical legal queries.
4. Permitted to claim that the system provides temporal legal version resolution, citation provenance verification, and automated LLM self-correction.
5. Permitted to claim that the backend implementation is validated by 337 passing automated tests and runs in a containerized Docker Compose environment.

#### CLAIMS STRICTLY FORBIDDEN (Do NOT Include in Any Chapter)
1. **Tree of Thoughts (ToT):** DO NOT claim that Juris AI uses Tree of Thoughts. Grep verification confirms zero code or execution evidence. Frame the pipeline as a *deterministic state-graph orchestration pipeline*.
2. **Universal State-of-the-Art:** DO NOT claim state-of-the-art across the entirety of Indian jurisprudence. State that it demonstrated marked improvement on the evaluated 34-document corpus.
3. **Unsupervised LLM Extraction:** DO NOT claim knowledge graphs were built autonomously by an LLM. State that extraction is performed via deterministic regex, domain heuristics, and canonical ID mapping.
4. **Custom Model Training:** DO NOT claim that InLegalBERT was trained or fine-tuned in this project. State that the pre-trained `law-ai/InLegalBERT` checkpoint was integrated.
5. **Universal PDF Ingestion:** DO NOT claim that all 34 PDFs were ingested without issues. Explicitly document that 1 scanned PDF (*Indira Gandhi 1975*) was flagged `FAILED / OCR_REQUIRED`.

---

### 7. Cross-References to Audit Deliverables

When drafting specific chapters, consult the following deliverables:
- **For Chapter 1 (Introduction & Problem Statement):** See [01_executive_summary.md](file:///c:/Projects/Juris%20AI/reports/project_audit/01_executive_summary.md) and [06_academic_contributions_and_limitations.md](file:///c:/Projects/Juris%20AI/reports/project_audit/06_academic_contributions_and_limitations.md).
- **For Chapter 2 (Literature Review & Related Work):** See [06_academic_contributions_and_limitations.md](file:///c:/Projects/Juris%20AI/reports/project_audit/06_academic_contributions_and_limitations.md).
- **For Chapter 3 (System Architecture & Methodology):** See [02_architecture_and_dataflow.md](file:///c:/Projects/Juris%20AI/reports/project_audit/02_architecture_and_dataflow.md) and [07_report_figures_and_tables.md](file:///c:/Projects/Juris%20AI/reports/project_audit/07_report_figures_and_tables.md) (Figures 1–6).
- **For Chapter 4 (Implementation & Engineering Details):** See [03_feature_implementation_matrix.md](file:///c:/Projects/Juris%20AI/reports/project_audit/03_feature_implementation_matrix.md) and [05_testing_and_deployment.md](file:///c:/Projects/Juris%20AI/reports/project_audit/05_testing_and_deployment.md).
- **For Chapter 5 (Results, Benchmarking & Discussion):** See [04_metrics_and_evaluation.md](file:///c:/Projects/Juris%20AI/reports/project_audit/04_metrics_and_evaluation.md) and [07_report_figures_and_tables.md](file:///c:/Projects/Juris%20AI/reports/project_audit/07_report_figures_and_tables.md) (Tables 1–5).
- **For Chapter 6 (Conclusion & Future Work):** See [06_academic_contributions_and_limitations.md](file:///c:/Projects/Juris%20AI/reports/project_audit/06_academic_contributions_and_limitations.md) and [09_missing_evidence_and_next_steps.md](file:///c:/Projects/Juris%20AI/reports/project_audit/09_missing_evidence_and_next_steps.md).
