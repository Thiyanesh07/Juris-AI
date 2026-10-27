# Scientific Research Paper Figures & Tables Specification
## Project: Graph-RAG System for Multi-Hop Reasoning Over Indian Constitutional and Statutory Law (Juris AI)

> **Document Type:** Publication Figures & Tables Blueprint  
> **Source Repository:** Juris AI (`c:\Projects\Juris AI`)  
> **Based On:** Actual Implemented System & [RESEARCH_CONTENT.md](file:///c:/Projects/Juris%20AI/RESEARCH_CONTENT.md)  
> **Verification Status:** 337 / 337 Backend Tests Passing | Next.js 16 Client Builds Verified  

---

# PART I — SCIENTIFIC RESEARCH PAPER FIGURES

---

### Figure 1 — Overall System Architecture
- **Figure Title:** Figure 1: Three-Tier Architecture of Juris AI for Multi-Hop Legal Intelligence
- **What It Should Show:** The modular, three-tier enterprise architecture of Juris AI, illustrating the separation of frontend client portals, the server-side FastAPI application backend, and persistent storage engines (relational, property graph, and vector index).
- **Exact Components / Data to Include:**
  - **Client Layer:** Next.js 16 User Portal (`:3002`), Admin Portal (`:3001`), Landing Page (`:3000`).
  - **Backend API Layer:** FastAPI (`:8000`), Session & RBAC Auth Middleware, Query Analysis Router, GraphRAG QA Engine.
  - **Persistence & Knowledge Layer:** PostgreSQL 16 DB (Users, Audit, Validation, Settings, Sessions), Neo4j 5 DB (6,135 Nodes, 10,514 Edges), FAISS Vector Index (2,412 InLegalBERT 768d Chunks).
  - **Data Flow Connections:** HTTP REST with HttpOnly cookies between client and API; Async SQLAlchemy to Postgres; Bolt protocol (`bolt://localhost:7688`) to Neo4j; in-memory/file search to FAISS (`index.faiss`).
- **Source Files / Code:** [docs/FINAL_ARCHITECTURE.md](file:///c:/Projects/Juris%20AI/docs/FINAL_ARCHITECTURE.md#L7-L55), [docker-compose.yml](file:///c:/Projects/Juris%20AI/docker-compose.yml), [server/api/app/main.py](file:///c:/Projects/Juris%20AI/server/api/app/main.py).
- **Status:** **EXISTING (Mermaid format)** in `docs/FINAL_ARCHITECTURE.md`. Needs vector graphic / high-resolution rendering for publication.

---

### Figure 2 — Knowledge Graph Schema & Ontology
- **Figure Title:** Figure 2: Property Knowledge Graph Schema for Indian Constitutional & Statutory Law
- **What It Should Show:** The formal entity-relationship ontology of the Neo4j property graph, displaying all 14 node entity types, 10 canonical relationship types, and attached metadata properties.
- **Exact Components / Data to Include:**
  - **Node Entity Types (14 Labels):** `Article`, `Section`, `Act`, `Amendment`, `Judgment`, `Court`, `Doctrine`, `Person`, `Concept`, `Organization`, `Document`, `Chunk`, `Rule`, `Regulation`.
  - **Canonical Relationships (10 Types):** `AMENDS`, `MODIFIES`, `SUPERSEDES`, `STRUCK_DOWN`, `INTERPRETS`, `DEFINES`, `REFERENCES`, `CITES`, `OVERRULES`, `BELONGS_TO`.
  - **Node Property Schema:** `id` (Canonical PK), `name`, `label`, `document_id`, `created_at`.
  - **Relationship Property Schema:** `provenance_key`, `source_document_id`, `source_chunk_id`, `page_start`, `page_end`, `evidence_text`, `confidence`, `extraction_method`.
- **Source Files / Code:** [server/api/app/graph/extraction.py](file:///c:/Projects/Juris%20AI/server/api/app/graph/extraction.py), [server/api/app/graph/client.py](file:///c:/Projects/Juris%20AI/server/api/app/graph/client.py), [docs/PHASE_13_LEGAL_KNOWLEDGE_LAYER.md](file:///c:/Projects/Juris%20AI/docs/PHASE_13_LEGAL_KNOWLEDGE_LAYER.md#L112-L148).
- **Status:** **NEEDS GENERATION** (Requires schema graph diagram generated from ontology definitions in `app/graph/extraction.py`).

---

### Figure 3 — End-to-End Query Processing Pipeline
- **Figure Title:** Figure 3: Deterministic State-Graph QA Pipeline Execution Flow
- **What It Should Show:** The sequential 8-stage execution flow of a user query through the backend state-graph pipeline from query ingestion to grounded response output.
- **Exact Components / Data to Include:**
  - **Stage 1:** Query Analysis Node (`analyze_query` in `app/rag/query_analysis.py`).
  - **Stage 2:** Temporal Analysis & Version Resolution Node (`resolve_legal_version` in `app/rag/temporal.py`).
  - **Stage 3:** Parallel Vector Retrieval (`FAISS`) & Multi-Hop Graph Traversal (`Neo4j`).
  - **Stage 4:** Evidence Fusion & Reranking Node (`fuse_and_rank_evidence` in `app/rag/evidence_fusion.py`).
  - **Stage 5:** Grounded Context Construction Node (`prepare_evidence_for_prompt` in `app/qa/prompts.py`).
  - **Stage 6:** Server-Side LLM Synthesis Node (`generate` in `app/qa/provider.py`).
  - **Stage 7:** Citation Verification Node (`verify_citation_grounding` in `app/rag/citation_verifier.py`).
  - **Stage 8:** Groundedness & Temporal Validation Node (`validate_response_groundedness` in `app/rag/validation.py`).
- **Source Files / Code:** [server/api/app/rag/pipeline.py](file:///c:/Projects/Juris%20AI/server/api/app/rag/pipeline.py#L173-L552), [docs/FINAL_ARCHITECTURE.md](file:///c:/Projects/Juris%20AI/docs/FINAL_ARCHITECTURE.md#L27-L36).
- **Status:** **NEEDS GENERATION** (Detailed flowchart specification defined in `docs/FINAL_ARCHITECTURE.md`; publication figure needs rendering).

---

### Figure 4 — Hybrid Graph + Vector Retrieval Workflow
- **Figure Title:** Figure 4: Parallel Retrieval, Reciprocal Rank Fusion (RRF), and Mode-Based Reranking
- **What It Should Show:** The detailed inner mechanics of the hybrid retrieval stage, showing how dense vector candidates and graph traversal candidate nodes run concurrently, are scored via RRF, boosted by Research Mode, and deduplicated.
- **Exact Components / Data to Include:**
  - **Dense Branch:** Query string $\rightarrow$ InLegalBERT 768d vector $\rightarrow$ FAISS `IndexFlatIP.search()` $\rightarrow$ Dense Candidate List with `dense_score`.
  - **Graph Branch:** Seed Entity IDs $\rightarrow$ Neo4j Cypher Async Multi-Hop Query $\rightarrow$ Entity & Relationship Path Expansion $\rightarrow$ Graph Candidate Chunks with `graph_score`.
  - **Fusion Engine:** RRF Scoring formula: $\text{Hybrid\_Score} = 0.50 \cdot S_{\text{vector}} + 0.50 \cdot S_{\text{graph}}$.
  - **Research Mode Multipliers:** `CONSTITUTIONAL` (1.25x), `STATUTORY` (1.25x), `CASE_LAW` (1.30x).
  - **Deduplication:** Max 2 chunks per page per document context budgeting filter.
- **Source Files / Code:** [server/api/app/rag/evidence_fusion.py](file:///c:/Projects/Juris%20AI/server/api/app/rag/evidence_fusion.py#L60-L215), [server/api/app/retrieval/hybrid.py](file:///c:/Projects/Juris%20AI/server/api/app/retrieval/hybrid.py).
- **Status:** **EXISTING (Text Flowchart)** in `docs/PHASE_14_HYBRID_GRAPHRAG.md`. Needs high-resolution publication diagram.

---

### Figure 5 — Multi-Hop Reasoning Workflow & Bridge Entity Discovery
- **Figure Title:** Figure 5: Multi-Hop Legal Graph Traversal for Cross-Statutory Precedent Reasoning
- **What It Should Show:** An actual multi-hop traversal graph trace from the system demonstrating how disjoint legal concepts are connected through intermediate landmark judgment nodes.
- **Exact Components / Data to Include:**
  - **Node 1:** `article:constitution_of_india:19` (Freedom of Speech and Expression).
  - **Edge 1:** `INTERPRETED_BY` / `APPLIED_IN`.
  - **Bridge Node 2:** `judgment:shreya_singhal` (*Shreya Singhal v. Union of India (2015)*).
  - **Edge 2:** `STRUCK_DOWN` (Reason: Unconstitutional overbreadth).
  - **Node 3:** `section:it_act_2000:66a` (Section 66A, Information Technology Act, 2000).
  - **Reasoning Step Log:** Step 1 (Entity Detection) $\rightarrow$ Step 2 (FAISS Seed Retrieval) $\rightarrow$ Step 3 (Neo4j Depth-3 Traversal) $\rightarrow$ Step 4 (Evidence Aggregation).
- **Source Files / Code:** [server/api/app/graph/traversal.py](file:///c:/Projects/Juris%20AI/server/api/app/graph/traversal.py), [server/api/tests/test_phase14_multihop_integration.py](file:///c:/Projects/Juris%20AI/server/api/tests/test_phase14_multihop_integration.py).
- **Status:** **NEEDS GENERATION** (Requires visual graph rendering of the verified test execution trace in `test_phase14_multihop_integration.py`).

---

### Figure 6 — Agent & Reasoning System Architecture
- **Figure Title:** Figure 6: Modular Component Interaction & Self-Correction Feedback Loop
- **What It Should Show:** The interaction between modular reasoning components, showing request/response dependencies, prompt construction, and automated self-correction loops when citation validation fails.
- **Exact Components / Data to Include:**
  - **Components:** Query Analyzer, Version Resolver, Evidence Fuser, LLM Provider, Citation Verifier, Groundedness Validator.
  - **Feedback Loop:** `parse_llm_output()` $\rightarrow$ `validate_llm_citations()` $\rightarrow$ If `CitationValidationError` occurs $\rightarrow$ Issue `build_correction_user_message()` to LLM Provider (Max 2 attempts).
- **Source Files / Code:** [server/api/app/qa/service.py](file:///c:/Projects/Juris%20AI/server/api/app/qa/service.py), [server/api/app/qa/citations.py](file:///c:/Projects/Juris%20AI/server/api/app/qa/citations.py#L75-L130), [server/api/app/rag/pipeline.py](file:///c:/Projects/Juris%20AI/server/api/app/rag/pipeline.py#L460-L486).
- **Status:** **NEEDS GENERATION** (Needs component interaction & feedback loop diagram).

---

### Figure 7 — Temporal & Amendment Reasoning Workflow
- **Figure Title:** Figure 7: Temporal Legal Version Resolution and Timeline Generation Workflow
- **What It Should Show:** The temporal query processing pipeline, showing how target years/amendments are extracted, matched against milestone date ranges, and converted into grounded chronological timeline events.
- **Exact Components / Data to Include:**
  - **Inputs:** Temporal Query (e.g. "What did Article 21 mean before the 44th Amendment in 1978?").
  - **Query Analysis:** `is_temporal=True`, `target_year=1978`, `temporal_operator="BEFORE"`, `referenced_amendment="44th Amendment"`.
  - **Version Resolution:** Matches `article:constitution_of_india:21` against `[effective_from="1950", effective_to="1978"]` $\rightarrow$ Status: `HISTORICAL`.
  - **Timeline Generator:** Grounded events array (`evt_const_1950`, `evt_gopalan_1950`, `evt_maneka_1978`, `evt_amd44_1978`).
  - **Prompt Header Injection:** Injects `[TEMPORAL REQUIREMENT: Distinguish historical law from current law]`.
- **Source Files / Code:** [server/api/app/rag/temporal.py](file:///c:/Projects/Juris%20AI/server/api/app/rag/temporal.py), [server/api/app/rag/pipeline.py](file:///c:/Projects/Juris%20AI/server/api/app/rag/pipeline.py#L76-L170).
- **Status:** **EXISTING (Text Flowchart)** in `docs/PHASE_15_TEMPORAL_CITATION.md`. Publication figure needs generation.

---

### Figure 8 — Citation & Evidence Validation Workflow
- **Figure Title:** Figure 8: Automated Formal Citation Pattern Matching and Provenance Verification
- **What It Should Show:** The structural citation verification flow, extracting citations from LLM text responses via regex and validating them against underlying chunk provenance metadata.
- **Exact Components / Data to Include:**
  - **LLM Text Output:** Text containing markers `[1]`, `[2]` and formal citations (e.g. `(2015) 5 SCC 1`).
  - **Regex Extraction:** Patterns for SCC, AIR, SCR, SCALE, Article, Section.
  - **Provenance Matcher:** Checks marker rank against `prepared_evidence` array $\rightarrow$ Validates `chunk_id`, `document_id`, page bounds, and textual presence.
  - **Classification States:** `VERIFIED`, `PARTIALLY_VERIFIED`, `UNVERIFIED`, `CONTRADICTED`.
  - **Output Report:** `QACitationValidation` payload returned to UI.
- **Source Files / Code:** [server/api/app/rag/citation_verifier.py](file:///c:/Projects/Juris%20AI/server/api/app/rag/citation_verifier.py), [server/api/app/qa/citations.py](file:///c:/Projects/Juris%20AI/server/api/app/qa/citations.py).
- **Status:** **NEEDS GENERATION** (Workflow diagram needs rendering).

---

### Figure 9 — Experimental Results Visualization
- **Figure Title:** Figure 9: Benchmark Performance Comparison across Retrieval Strategies
- **What It Should Show:** Grouped bar chart comparing `VECTOR_ONLY`, `GRAPH_ONLY`, and `HYBRID` strategies across five evaluation metrics.
- **Exact Components / Data to Include:**
  - **X-Axis:** Retrieval Strategies (`VECTOR_ONLY`, `GRAPH_ONLY`, `HYBRID`).
  - **Y-Axis Metrics:** Mean Recall@5, Mean Precision@5, Mean Reciprocal Rank (MRR), Citation Verification Rate, Temporal Fact Accuracy.
  - **Data Values:**
    - `VECTOR_ONLY`: Recall@5 = 0.6111, Precision@5 = 0.2889, MRR = 0.6944, Citation Rate = 1.0000, Temporal Acc = 0.6667.
    - `GRAPH_ONLY`: Recall@5 = 0.5556, Precision@5 = 0.2444, MRR = 0.5833, Citation Rate = 1.0000, Temporal Acc = 0.5000.
    - `HYBRID`: Recall@5 = 0.8889, Precision@5 = 0.4222, MRR = 0.9444, Citation Rate = 1.0000, Temporal Acc = 1.0000.
- **Source Files / Code:** [docs/PROJECT_COMPLETION_REPORT.md](file:///c:/Projects/Juris%20AI/docs/PROJECT_COMPLETION_REPORT.md#L30-L35), [server/api/app/services/evaluation_runner.py](file:///c:/Projects/Juris%20AI/server/api/app/services/evaluation_runner.py).
- **Status:** **NEEDS GENERATION** (Data available in report table; bar chart graphic needs generation).

---

### Figure 10 — Ablation Results Visualization
- **Figure Title:** Figure 10: Performance Degradation Under Retrieval Component Ablations
- **What It Should Show:** Percentage performance drop resulting from removing Knowledge Graph expansion or Vector retrieval components relative to the full Hybrid system.
- **Exact Components / Data to Include:**
  - **Full Hybrid Baseline:** Recall@5 = 0.8889 (100%), MRR = 0.9444 (100%), Temporal Acc = 1.0000 (100%).
  - **Ablation 1 (Vector-Only / No Graph):** Recall@5 drops by -27.78%; MRR drops by -25.00%; Temporal Acc drops by -33.33%.
  - **Ablation 2 (Graph-Only / No Vector):** Recall@5 drops by -33.33%; MRR drops by -36.11%; Temporal Acc drops by -50.00%.
- **Source Files / Code:** [docs/PROJECT_COMPLETION_REPORT.md](file:///c:/Projects/Juris%20AI/docs/PROJECT_COMPLETION_REPORT.md), [RESEARCH_CONTENT.md](file:///c:/Projects/Juris%20AI/RESEARCH_CONTENT.md#L15).
- **Status:** **NEEDS GENERATION** (Ablation waterfall / drop chart graphic needs generation).

---

# PART II — SCIENTIFIC RESEARCH PAPER TABLES

---

### Table 1 — Primary Legal Corpus & Dataset Breakdown (`legal_corpus_v1`)
- **Table Title:** Table 1: Ingestion & Structural Breakdown of the Legal Corpus (`legal_corpus_v1`)
- **Columns:** `Corpus Category`, `Document ID`, `Document Title / Description`, `Status`, `Extracted Pages`, `Text Chunks`, `Extracted Entities`, `Extracted Relations`
- **Rows & Exact Values:**

| Corpus Category | Document ID | Document Title / Description | Status | Extracted Pages | Text Chunks | Extracted Entities | Extracted Relations |
|---|---|---|---|---|---|---|---|
| **Constitution** | `constitution_of_india` | Constitution of India | SUCCESS | 402 | 145 | 1,213 | 298 |
| **Statutes & Codes** | `crpc_1973` | Code of Criminal Procedure, 1973 | SUCCESS | 289 | 168 | 1,892 | 1,002 |
| | `iea_1872` | Indian Evidence Act, 1872 | SUCCESS | 54 | 20 | 238 | 125 |
| | `ipc_1860` | Indian Penal Code, 1860 | SUCCESS | 140 | 52 | 268 | 110 |
| | `phra_1993` | Protection of Human Rights Act, 1993 | SUCCESS | 18 | 12 | 126 | 57 |
| | `rpa_1951` | Representation of the People Act, 1951 | SUCCESS | 61 | 30 | 304 | 184 |
| | `bnss_2023` | Bharatiya Nagarik Suraksha Sanhita, 2023 | SUCCESS | 282 | 119 | 847 | 725 |
| | `bns_2023` | Bharatiya Nyaya Sanhita, 2023 | SUCCESS | 112 | 45 | 139 | 105 |
| | `bsa_2023` | Bharatiya Sakshya Adhiniyam, 2023 | SUCCESS | 54 | 28 | 110 | 77 |
| | `it_act_2000` | Information Technology Act, 2000 | SUCCESS | 44 | 23 | 183 | 135 |
| | `rti_act_2005` | Right to Information Act, 2005 | SUCCESS | 25 | 15 | 69 | 49 |
| **Amendments** | `const_amendment_44` | 44th Constitutional Amendment Act, 1978 | SUCCESS | 16 | 6 | 95 | 81 |
| | `const_amendment_42` | 42nd Constitutional Amendment Act, 1976 | SUCCESS | 22 | 5 | 145 | 125 |
| | `const_amendment_101` | 101st Constitutional Amendment Act, 2016 | SUCCESS | 7 | 3 | 26 | 24 |
| | `const_amendment_73` | 73rd Constitutional Amendment Act, 1992 | SUCCESS | 10 | 3 | 13 | 10 |
| **Judgments** | `kesavananda_bharati_1973` | Kesavananda Bharati v. State of Kerala | SUCCESS | 1,006 | 486 | 3,887 | 5,538 |
| | `indira_gandhi_1975` | Indira Nehru Gandhi v. Raj Narain | OCR_REQUIRED | 0 | 0 | 0 | 0 |
| | `minerva_mills_1980` | Minerva Mills Ltd. v. Union of India | SUCCESS | 85 | 74 | 533 | 771 |
| | `ir_coelho_2007` | I.R. Coelho v. State of Tamil Nadu | SUCCESS | 73 | 41 | 300 | 384 |
| | `l_chandra_kumar_1997` | L. Chandra Kumar v. Union of India | SUCCESS | 28 | 19 | 197 | 251 |
| | `ep_royappa_1974` | E.P. Royappa v. State of Tamil Nadu | SUCCESS | 31 | 5 | 28 | 28 |
| | `maneka_gandhi_1978` | Maneka Gandhi v. Union of India | SUCCESS | 110 | 74 | 482 | 571 |
| | `shayara_bano_2017` | Shayara Bano v. Union of India | SUCCESS | 5 | 1 | 2 | 0 |
| | `romesh_thappar_1950` | Romesh Thappar v. State of Madras | SUCCESS | 8 | 6 | 72 | 72 |
| | `bennett_coleman_1973` | Bennett Coleman & Co. v. Union of India | SUCCESS | 17 | 13 | 83 | 83 |
| | `shreya_singhal_2015` | Shreya Singhal v. Union of India | SUCCESS | 41 | 24 | 237 | 229 |
| | `ak_gopalan_1950` | A.K. Gopalan v. State of Madras | SUCCESS | 112 | 81 | 679 | 809 |
| | `puttaswamy_privacy_2017` | K.S. Puttaswamy v. UOI (Right to Privacy) | SUCCESS | 547 | 196 | 831 | 853 |
| | `common_cause_2018` | Common Cause v. Union of India | SUCCESS | 173 | 69 | 448 | 395 |
| | `sr_bommai_1994` | S.R. Bommai v. Union of India | SUCCESS | 152 | 72 | 562 | 841 |
| | `vishaka_1997` | Vishaka v. State of Rajasthan | SUCCESS | 8 | 7 | 30 | 34 |
| | `nalsa_2014` | National Legal Services Authority v. UOI | SUCCESS | 35 | 12 | 95 | 101 |
| | `navtej_johar_2018` | Navtej Singh Johar v. Union of India | SUCCESS | 243 | 75 | 423 | 385 |
| | `puttaswamy_aadhaar_2018` | K.S. Puttaswamy v. UOI (Aadhaar) | SUCCESS | 1,448 | 483 | 2,742 | 2,604 |
| **TOTALS** | **34 Documents** | **Corpus Summary** | **33 Success / 1 Failed** | **5,658** | **2,412** | **3,790 (Raw)** | **17,056 (Raw)** |

- **Source of Values:** [data/legal_corpus_v1/processed/ingestion_report.md](file:///c:/Projects/Juris%20AI/data/legal_corpus_v1/processed/ingestion_report.md#L17-L52).

---

### Table 2 — Knowledge Graph Node & Edge Schema Statistics
- **Table Title:** Table 2: Entity Node Types and Canonical Relationship Types in Knowledge Graph
- **Columns:** `Element Category`, `Label / Type Name`, `Description / Semantics`, `Property Attributes`, `Count`
- **Rows & Exact Values:**

| Element Category | Label / Type Name | Description / Semantics | Property Attributes | Count |
|---|---|---|---|---|
| **Node Labels** | `Article` | Constitutional Article | `id`, `name`, `document_id`, `created_at` | -- |
| | `Section` | Statutory Act Section | `id`, `name`, `document_id`, `created_at` | -- |
| | `Act` | Central Legislation / Statute | `id`, `name`, `year`, `jurisdiction` | -- |
| | `Amendment` | Constitutional Amendment Act | `id`, `title`, `year` | -- |
| | `Judgment` | Supreme Court / High Court Ruling | `id`, `title`, `year`, `citation` | -- |
| | `Court` | Judicial Forum | `id`, `name`, `jurisdiction` | -- |
| | `Doctrine` | Established Legal Principle | `id`, `name` | -- |
| | `Person` | Judge / Petitioner / Respondent | `id`, `name` | -- |
| | `Concept` | Legal Term / Precedent Subject | `id`, `name` | -- |
| | `Chunk` | Supporting Vector Text Chunk | `id`, `text`, `page_start`, `page_end` | -- |
| | *Other Labels* | `Rule`, `Regulation`, `Organization`, `Document` | Various | -- |
| | **TOTAL NODES** | **Canonical Legal Entities** | **Graph Database Total** | **6,135** |
| **Edge Relationships** | `AMENDS` | Amendment modifies Article or Act | `provenance_key`, `page_start`, `confidence` | -- |
| | `MODIFIES` | Alters existing legal provision | `provenance_key`, `page_start`, `confidence` | -- |
| | `SUPERSEDES` | Replaces prior statutory text | `provenance_key`, `page_start`, `confidence` | -- |
| | `STRUCK_DOWN` | Invalidated by Supreme Court | `provenance_key`, `page_start`, `confidence` | -- |
| | `INTERPRETS` | Judicial interpretation of provision | `provenance_key`, `page_start`, `confidence` | -- |
| | `DEFINES` | Statutory definition of concept | `provenance_key`, `page_start`, `confidence` | -- |
| | `REFERENCES` / `CITES` | Legal citation of act/judgment | `provenance_key`, `page_start`, `confidence` | -- |
| | `OVERRULES` | Express overruling of precedent | `provenance_key`, `page_start`, `confidence` | -- |
| | `BELONGS_TO` | Structural containment | `provenance_key`, `page_start`, `confidence` | -- |
| | **TOTAL EDGES** | **Provenance-Backed Triples** | **Graph Database Total** | **10,514** |

- **Source of Values:** [docs/PROJECT_COMPLETION_REPORT.md](file:///c:/Projects/Juris%20AI/docs/PROJECT_COMPLETION_REPORT.md#L40-L44), [server/api/app/graph/extraction.py](file:///c:/Projects/Juris%20AI/server/api/app/graph/extraction.py).

---

### Table 3 — System Technology & Computational Environment Configuration
- **Table Title:** Table 3: System Technology Stack and Environment Specification
- **Columns:** `Subsystem`, `Component / Library`, `Version Specification`, `Configuration Parameter / Setting`
- **Rows & Exact Values:**

| Subsystem | Component / Library | Version Specification | Configuration Parameter / Setting |
|---|---|---|---|
| **Runtime** | Python | `>=3.12, <3.13` | CPython 64-bit |
| **API Framework** | FastAPI | `>=0.115, <1.0` | Async ASGI Engine (Uvicorn 0.34) |
| **Relational Database** | PostgreSQL | `16-alpine` | AsyncPG driver 0.29, Connection Pool: 5 (Max Overflow: 10) |
| **Graph Database** | Neo4j | `5-community` | Bolt Protocol (`bolt://localhost:7688`), APOC Plugin |
| **Vector Index Engine** | FAISS | `faiss-cpu >=1.10, <2.0` | Index Flat Inner Product (`faiss.IndexFlatIP`) |
| **PDF Extraction** | PyMuPDF | `fitz >=1.24, <2.0` | Block & page-level extraction |
| **Deep Learning Framework** | PyTorch / Transformers | Torch 2.6, Transformers 4.48 | CPU execution, batch size 16 |
| **Frontend Framework** | Next.js / React | Next.js 16.0.10, React 19.2.0 | TypeScript 5, Turbopack, TailwindCSS 4.1.9 |
| **Containerization** | Docker / Docker Compose | Compose file version `3.8` | Profiles: `infra`, `app` |

- **Source of Values:** [server/api/pyproject.toml](file:///c:/Projects/Juris%20AI/server/api/pyproject.toml), [docker-compose.yml](file:///c:/Projects/Juris%20AI/docker-compose.yml), [client/user/package.json](file:///c:/Projects/Juris%20AI/client/user/package.json).

---

### Table 4 — Model & Algorithm Configuration
- **Table Title:** Table 4: Machine Learning Model Hyperparameters and Retrieval Settings
- **Columns:** `Model / Algorithm`, `Provider / Source`, `Dimensions / Parameters`, `Max Sequence Length`, `Temperature`, `Key Setting / Hyperparameter`
- **Rows & Exact Values:**

| Model / Algorithm | Provider / Source | Dimensions / Parameters | Max Sequence Length | Temperature | Key Setting / Hyperparameter |
|---|---|---|---|---|---|
| **InLegalBERT** | HuggingFace (`law-ai/InLegalBERT`) | 768-dim embeddings (~110M params) | 512 tokens | N/A | Attention-mask mean pooling; L2-normalization |
| **FAISS IndexFlatIP** | Meta AI / FAISS CPU | 768-dim vector space | N/A | N/A | Cosine similarity via inner product on normalized vectors |
| **Neo4j Cypher Traverser** | Neo4j 5 Graph Engine | 6,135 nodes / 10,514 edges | N/A | N/A | Default depth: 3 hops; Max depth: 5 hops; Node cap: 100 |
| **Reciprocal Rank Fusion** | Custom Algorithm (`evidence_fusion.py`) | Weights: $w_v = 0.50, w_g = 0.50$ | N/A | N/A | Mode boosts: Constitutional (1.25x), Case Law (1.30x) |
| **gpt-4o-mini** | OpenAI-compatible API | Server-side LLM | 800 output tokens | `0.0` (Strict) | Evidence-only strict prompt grounding; Context cap: 12k chars |

- **Source of Values:** [server/api/app/core/config.py](file:///c:/Projects/Juris%20AI/server/api/app/core/config.py#L102-L135), [server/api/app/rag/evidence_fusion.py](file:///c:/Projects/Juris%20AI/server/api/app/rag/evidence_fusion.py#L37-L57).

---

### Table 5 — Baseline Comparison & Main Benchmark Results
- **Table Title:** Table 5: Benchmark Evaluation Comparison Across Retrieval Strategies
- **Columns:** `Retrieval Strategy`, `Mean Recall@5`, `Mean Precision@5`, `Mean Reciprocal Rank (MRR)`, `Citation Verification Rate`, `Temporal Fact Accuracy`
- **Rows & Exact Values:**

| Retrieval Strategy | Mean Recall@5 | Mean Precision@5 | Mean Reciprocal Rank (MRR) | Citation Verification Rate | Temporal Fact Accuracy |
|---|---|---|---|---|---|
| `VECTOR_ONLY` | 0.6111 | 0.2889 | 0.6944 | 1.0000 | 0.6667 |
| `GRAPH_ONLY` | 0.5556 | 0.2444 | 0.5833 | 1.0000 | 0.5000 |
| **`HYBRID` (Proposed)** | **0.8889** | **0.4222** | **0.9444** | **1.0000** | **1.0000** |

- **Source of Values:** [docs/PROJECT_COMPLETION_REPORT.md](file:///c:/Projects/Juris%20AI/docs/PROJECT_COMPLETION_REPORT.md#L30-L35), [server/api/app/services/evaluation_runner.py](file:///c:/Projects/Juris%20AI/server/api/app/services/evaluation_runner.py).

---

### Table 6 — Ground-Truth Evaluation Query Dataset Inventory
- **Table Title:** Table 6: Canonical Ground-Truth Evaluation Benchmark Dataset (`server/data/evaluation/questions.json`)
- **Columns:** `Query ID`, `Query Text`, `Category`, `Is Temporal`, `Target Year`, `Expected Canonical Entities`, `Expected Citations`
- **Rows & Exact Values:**

| Query ID | Query Text | Category | Is Temporal | Target Year | Expected Canonical Entities | Expected Citations |
|---|---|---|---|---|---|---|
| `eval_q01` | What does Article 21 protect? | CONSTITUTIONAL | False | N/A | `article:constitution_of_india:21`, `concept:life_and_personal_liberty` | `Article 21` |
| `eval_q02` | How has the Supreme Court interpreted Article 21? | CONSTITUTIONAL | False | N/A | `article:constitution_of_india:21`, `judgment:maneka_gandhi` | `Article 21`, `(1978) 1 SCC 248` |
| `eval_q03` | Relationship between Sec 66A IT Act and Art 19 freedom of speech | STATUTORY | False | N/A | `section:it_act_2000:66a`, `article:constitution_of_india:19`, `judgment:shreya_singhal` | `Section 66A`, `Article 19`, `(2015) 5 SCC 1` |
| `eval_q04` | What is the Basic Structure Doctrine? | CONSTITUTIONAL | False | N/A | `judgment:kesavananda_bharati`, `concept:basic_structure` | `AIR 1973 SC 1461` |
| `eval_q05` | How did Maneka Gandhi change the interpretation of Article 21? | CASE_LAW | True | 1978 | `judgment:maneka_gandhi`, `article:constitution_of_india:21` | `(1978) 1 SCC 248` |
| `eval_q06` | How does Shreya Singhal relate Section 66A to freedom of speech? | CASE_LAW | False | N/A | `judgment:shreya_singhal`, `section:it_act_2000:66a`, `article:constitution_of_india:19` | `(2015) 5 SCC 1` |
| `eval_q07` | What did Article 21 mean before the 44th Amendment? | TEMPORAL | True | 1978 | `article:constitution_of_india:21`, `amendment:const_amendment_44` | `44th Constitutional Amendment` |
| `eval_q08` | What changed after the 44th Constitutional Amendment? | TEMPORAL | True | N/A | `amendment:const_amendment_44`, `article:constitution_of_india:21`, `article:constitution_of_india:19` | `44th Constitutional Amendment` |
| `eval_q09` | What was the legal position in 1978? | TEMPORAL | True | 1978 | `article:constitution_of_india:21`, `judgment:maneka_gandhi` | `1978` |

- **Source of Values:** [server/data/evaluation/questions.json](file:///c:/Projects/Juris%20AI/server/data/evaluation/questions.json).

---

### Table 7 — End-to-End Latency & Performance Breakdown
- **Table Title:** Table 7: System Response Latencies and Execution Performance Across Sample Queries
- **Columns:** `Sample Benchmark Query`, `Retrieval Strategy`, `Response Latency (ms)`, `Evidence Count`, `Citation Count`, `Multi-Hop Paths Discovered`, `Status`
- **Rows & Exact Values:**

| Sample Benchmark Query | Retrieval Strategy | Response Latency (ms) | Evidence Count | Citation Count | Multi-Hop Paths Discovered | Status |
|---|---|---|---|---|---|---|
| "What does Article 21 protect?" | Hybrid | ~240 ms | 5 | 1 | 2 | Answered |
| "How has the Supreme Court interpreted Article 21?" | Hybrid | ~260 ms | 5 | 2 | 3 | Answered |
| "Relationship between Sec 66A IT Act & Art 19" | Hybrid | ~310 ms | 5 | 2 | 1 (3-hop) | Answered |
| "What is the Basic Structure Doctrine?" | Hybrid | ~220 ms | 4 | 1 | 2 | Answered |
| "How did Maneka Gandhi change Article 21?" | Hybrid | ~280 ms | 5 | 2 | 2 | Answered |
| "How does Shreya Singhal relate Sec 66A to speech?" | Hybrid | ~295 ms | 5 | 2 | 1 (3-hop) | Answered |

- **Source of Values:** [docs/PHASE_14_HYBRID_GRAPHRAG.md](file:///c:/Projects/Juris%20AI/docs/PHASE_14_HYBRID_GRAPHRAG.md#L92-L99).

---

### Table 8 — Retrieval Strategy Ablation Study Matrix
- **Table Title:** Table 8: Ablation Results Demonstrating Contribution of Graph and Vector Components
- **Columns:** `Component Variant`, `Ablation Description`, `Mean Recall@5`, `Recall Delta (%)`, `MRR`, `MRR Delta (%)`, `Temporal Accuracy`
- **Rows & Exact Values:**

| Component Variant | Ablation Description | Mean Recall@5 | Recall Delta (%) | MRR | MRR Delta (%) | Temporal Accuracy |
|---|---|---|---|---|---|---|
| **Full `HYBRID` System** | Proposed Dense + Graph RRF System | **0.8889** | **Base** | **0.9444** | **Base** | **1.0000** |
| `VECTOR_ONLY` | Removes Neo4j Cypher Multi-Hop Graph Traversal | 0.6111 | -27.78% | 0.6944 | -25.00% | 0.6667 |
| `GRAPH_ONLY` | Removes InLegalBERT FAISS Dense Search | 0.5556 | -33.33% | 0.5833 | -36.11% | 0.5000 |

- **Source of Values:** Calculated directly from baseline benchmark execution results in [docs/PROJECT_COMPLETION_REPORT.md](file:///c:/Projects/Juris%20AI/docs/PROJECT_COMPLETION_REPORT.md#L30-L35).

---

### Table 9 — Categorized Error Analysis & System Limitations
- **Table Title:** Table 9: Taxonomy of Real System Failures and Behavioral Boundaries
- **Columns:** `Error Category`, `Specific Document / Query`, `Root Cause`, `Observed Symptom`, `System Mitigation / Handling`
- **Rows & Exact Values:**

| Error Category | Specific Document / Query | Root Cause | Observed Symptom | System Mitigation / Handling |
|---|---|---|---|---|
| **OCR Dependency** | `02_indira_nehru_gandhi_raj_narain_1975.pdf` | Scanned raster image PDF without embedded text stream | PyMuPDF returns 0 text characters | Explicitly marked `FAILED / OCR_REQUIRED` in ingestion report; empty chunks rejected |
| **Numerical Section Confusion** | Statutory Queries on IT Act (Sec 66 vs 66A) | Dense token embeddings share high cosine similarity | Vector search ranks Section 66 above Section 66A | Knowledge graph entity ID matching filters out non-exact statutory sections |
| **Over-Expansion Noise** | Deep multi-hop queries on Article 21 (depth > 3) | High node degree of foundational constitutional articles | Graph traversal pulls distant unrelated precedents | Traversal depth default bounded to 3; candidate nodes capped at 100 |
| **Unmapped Temporal Status** | Queries on obscure un-indexed amendments | Amendment not present in 4 indexed amendment PDFs | `resolve_legal_version()` cannot verify effective date range | Returns `status="UNKNOWN"` with `temporal_confidence=0.0`; does NOT fabricate dates |

- **Source of Values:** [docs/PROJECT_COMPLETION_REPORT.md](file:///c:/Projects/Juris%20AI/docs/PROJECT_COMPLETION_REPORT.md#L49-L55), [data/legal_corpus_v1/processed/ingestion_report.md](file:///c:/Projects/Juris%20AI/data/legal_corpus_v1/processed/ingestion_report.md#L35).

---

### Table 10 — Test Suite Coverage & Verification Matrix
- **Table Title:** Table 10: Backend Unit, Integration, and Phase Verification Suite Execution Matrix
- **Columns:** `Test Category / Phase`, `Target Subsystem / Module`, `Test File`, `Tests Passed`, `Pass Rate`
- **Rows & Exact Values:**

| Test Category / Phase | Target Subsystem / Module | Test File | Tests Passed | Pass Rate |
|---|---|---|---|---|
| **Ingestion & Hierarchy** | Extractor, Chunker, Hierarchy | `test_ingestion_*.py` | 24 tests | 100% |
| **Graph Extraction & DB** | Extraction, Population, Client | `test_graph_*.py` | 38 tests | 100% |
| **Retrieval & Embeddings** | FAISS Search, Embeddings | `test_retrieval.py` | 18 tests | 100% |
| **QA Engine & Prompts** | QA Service, Prompts, Provider | `test_qa_*.py` | 35 tests | 100% |
| **Phase 14 GraphRAG** | RRF Fusion, Multi-Hop | `test_phase14_*.py` | 12 tests | 100% |
| **Phase 15 Temporal & Citation** | Version Resolution, Verifier | `test_phase15_*.py` | 15 tests | 100% |
| **Phase 16 Admin & Persistence** | Validation, Audit, Settings | `test_phase16_*.py` | 11 tests | 100% |
| **API Endpoints & Auth** | FastAPI Routes, Cookies, RBAC | `test_api_*.py`, `test_auth.py` | 184 tests | 100% |
| **TOTAL VERIFIED SUITE** | **Complete Backend System** | **337 Test Files** | **337 / 337** | **100.0%** |

- **Source of Values:** [docs/PROJECT_COMPLETION_REPORT.md](file:///c:/Projects/Juris%20AI/docs/PROJECT_COMPLETION_REPORT.md#L7), [server/api/tests/](file:///c:/Projects/Juris%20AI/server/api/tests/).
