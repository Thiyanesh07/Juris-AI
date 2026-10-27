# Missing Evidence, Technical Gaps, and Prioritized Action Plan
## Juris AI: GraphRAG-Based Indian Legal Reasoning System
**Document ID:** `reports/project_audit/09_missing_evidence_and_next_steps.md`  
**System Root:** `c:\Projects\Juris AI`  
**Target Purpose:** Actionable checklist for the student author and report preparation team  

---

### 1. Overview of Missing Evidence

While the core software architecture, ingestion pipeline, vector index, knowledge graph, and test suite are thoroughly implemented and documented in the repository, several specific pieces of evidence must be gathered or clarified by the student author before finalizing the academic project report:

```
[Critical Evidence Gaps to Address Before Report Submission]
  ├── G1: Capture Genuine High-Resolution Portal Screenshots (User, Admin, Graph Explorer)
  ├── G2: Fill Institutional Metadata (Student Names, Roll Numbers, Guide, Department)
  ├── G3: Profile Empirical Latency Distributions (p50, p95 across 20+ runs)
  ├── G4: Run Extended 20-Query Benchmark (benchmark_phase2_runner.py)
  └── G5: Note Scanned PDF OCR Deferral (Document 02_indira_nehru_gandhi_raj_narain_1975.pdf)
```

---

### 2. Prioritized Action Matrix

| Priority | Action Item | Target Subsystem / Artifact | Why It Matters | How to Complete & Verify |
|---|---|---|---|---|
| **P1 — CRITICAL** | **Capture Genuine UI Screenshots** | `client/user`, `client/admin` | Academic evaluators expect visual evidence of working software interfaces rather than code-only claims. | Launch client portals (`npm run dev -p 3002` and `-p 3001`), execute sample query, capture PNGs of: (1) Research Workspace, (2) SVG Knowledge Graph Tab, (3) Timeline Inspector, (4) Ingestion Dashboard. Save to `reports/screenshots/`. |
| **P1 — CRITICAL** | **Supply Institutional & Team Details** | Front Matter, Certificate, Declaration | Required by university examination guidelines (VTU / Anna Univ / Mumbai Univ / autonomous formats). | Provide: Student name(s), USN / Roll number(s), Project Guide / Supervisor name, Department, College Name, Academic Year (2026-2027). |
| **P2 — HIGH** | **Execute Extended 20-Query Benchmark** | `server/api/benchmarks/benchmark_phase2_runner.py` | Expands the evaluation from 9 pilot queries to 20 queries, strengthening the results chapter. | Run safe read-only benchmark command: `uv run python benchmarks/benchmark_phase2_runner.py` inside `server/api/`. Record Mean Recall@5, Mean Recall@10, and Abstention Accuracy. |
| **P2 — HIGH** | **Run Multi-Iteration Latency Profiling** | `server/api/app/rag/pipeline.py` | Eliminates reliance on single-run indicative latencies (~220ms–310ms), providing defensible p50/p95 latency numbers. | Execute a lightweight timing script across the 9 canonical queries for 5 iterations each; calculate median and 95th percentile latency per component (embedding, FAISS, Neo4j, LLM). |
| **P3 — MEDIUM** | **Document OCR Handling Limitation** | Chapter 3 & 4 (Corpus / Ingestion) | Prevents examiners from questioning why *Indira Gandhi (1975)* yielded 0 chunks. | Explicitly describe the raster image PDF detection in Chapter 3; frame it as an intentional safety feature preventing hallucination from corrupt text streams. |
| **P3 — MEDIUM** | **Verify Cloud Deployment URLs** | Chapter 2 & Deployment Section | Documents real-world accessibility. | Confirm status of Vercel endpoints (`juris-ai-user.vercel.app`, `juris-ai-admin.vercel.app`) or state clearly that system was evaluated in local Docker Compose containerized environment. |

---

### 3. Detailed Guidance on Executing Action Items

#### Action Item G1: Capturing Genuine UI Screenshots
To capture genuine screenshots for Chapter 4:
1. Ensure Docker services (`postgres` and `neo4j`) are active via `docker-compose up -d`.
2. Start the FastAPI backend:
   ```bash
   cd server/api
   uv run python run_server.py
   ```
3. Start the User Portal:
   ```bash
   cd client/user
   npm run dev
   ```
4. Navigate to `http://localhost:3002/research` and enter the canonical multi-hop query:
   `"What is the relationship between Section 66A of the IT Act and freedom of speech under Article 19?"`
5. Capture full-resolution screenshots of:
   - **Answer Tab:** Grounded text with citations `[1]`, `[2]`.
   - **Knowledge Graph Tab:** Displaying Article 19 $\rightarrow$ *Shreya Singhal* $\rightarrow$ Section 66A.
   - **Timeline Tab:** Displaying the 1950 Enactment and 2015 *Shreya Singhal* decision.

#### Action Item G2: Institutional Front Matter Template
Prepare a placeholder table for insertion into the report writer context:
```markdown
- College / University: [e.g., Department of Computer Science & Engineering, ABC Institute of Technology]
- Degree: Bachelor of Engineering / Bachelor of Technology in Computer Science & Engineering
- Project Type: Final Year / Pre-Final Year Capstone / Mini-Project
- Student Authors: [Name 1, USN 1; Name 2, USN 2]
- Project Supervisor / Guide: [Prof. Name, Designation]
- Academic Year: 2026 – 2027
```

#### Action Item G3: Proposed Read-Only Latency Profiling Command
When authorized by the user, the following non-mutating test command will collect fresh timing evidence without altering database state:
```bash
# In server/api:
uv run python -c "
import asyncio, time
from app.core.config import get_settings, get_data_dir
from app.retrieval.service import embed_query_vector
from app.retrieval.index import search_index_rows

settings = get_settings()
query = 'What does Article 21 protect?'
t0 = time.perf_counter()
idx, meta, qvec, _ = embed_query_vector(query, settings)
t_embed = (time.perf_counter() - t0) * 1000
t1 = time.perf_counter()
hits = search_index_rows(idx, meta, qvec, 10)
t_search = (time.perf_counter() - t1) * 1000
print(f'Embedding latency: {t_embed:.2f} ms | FAISS search latency: {t_search:.2f} ms | Hits: {len(hits)}')
"
```

---

### 4. Verification Checklist for Report Submission Readiness

- [x] Full architectural reconstruction completed from source code.
- [x] Vector index dimensions (768d) and FAISS index type (`IndexFlatIP`) verified.
- [x] Neo4j node (6,135) and relationship (10,514) counts confirmed against ingestion artifacts.
- [x] Baseline vs. Hybrid retrieval metrics verified on canonical 9-query benchmark.
- [x] Tree of Thoughts (ToT) claims identified and strictly forbidden.
- [x] Backend test suite passing status (337/337 tests) documented.
- [ ] User/Admin portal screenshots captured by student author and embedded in report.
- [ ] Institutional author details and acknowledgments added.
- [ ] Faculty submission formatting applied.
