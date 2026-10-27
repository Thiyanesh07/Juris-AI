# Testing, Quality Assurance, and Deployment Audit
## Juris AI: GraphRAG-Based Indian Legal Reasoning System
**Document ID:** `reports/project_audit/05_testing_and_deployment.md`  
**System Root:** `c:\Projects\Juris AI`  
**Authoritative Evidence:** Test suite inspection in `server/api/tests/`, `client/admin/tests/`, `client/user/tests/`, deployment configuration in `docker-compose.yml`, `render.yaml`, `vercel.json`  

---

### 1. Test Suite Inventory & Structure

The repository maintains an extensive test suite combining Python backend tests and Node.js / TypeScript frontend tests.

```
server/api/tests/ (68 files)
├── Unit Tests
│   ├── test_ingestion_chunker.py (10 tests)
│   ├── test_ingestion_extractor_normalizer.py (12 tests)
│   ├── test_ingestion_hierarchy.py (19 tests)
│   ├── test_ingestion_validator.py (6 tests)
│   ├── test_onnx_embedder.py (3 tests)
│   ├── test_retrieval.py (4 tests)
│   ├── test_graph_extraction.py (14 tests)
│   ├── test_graph_client.py (12 tests)
│   ├── test_qa_citations.py (14 tests)
│   ├── test_qa_prompts.py (7 tests)
│   ├── test_qa_provider.py (14 tests)
│   ├── test_rate_limit.py (6 tests)
│   ├── test_csrf.py (4 tests)
│   └── test_dynamic_settings.py (8 tests)
├── Integration & State Graph Tests
│   ├── test_phase14_graphrag_pipeline.py (6 tests)
│   ├── test_phase14_multihop_integration.py (1 test)
│   ├── test_phase14_query_analysis.py (5 tests)
│   ├── test_phase15_citation_verification.py (4 tests)
│   ├── test_phase15_pipeline_integration.py (3 tests)
│   ├── test_phase15_temporal_query.py (3 tests)
│   ├── test_phase15_version_resolution.py (5 tests)
│   ├── test_phase16_admin_users.py (12 tests)
│   ├── test_phase16_audit.py (3 tests)
│   ├── test_phase16_evaluation.py (3 tests)
│   ├── test_phase16_graph.py (11 tests)
│   ├── test_phase16_history_saved.py (5 tests)
│   └── test_phase16_validation.py (6 tests)
├── End-to-End & Safety Isolation Tests
│   ├── test_ingestion_pipeline_e2e.py (5 tests)
│   ├── test_phase6_isolated_ingestion.py (12 tests)
│   ├── test_isolation_preflight.py (8 tests)
│   └── test_phase4_step8_faiss_cleanup_and_cli.py (8 tests)
└── Test Fixtures & Harnesses
    ├── conftest.py (Database session fixtures, settings overrides)
    ├── fake_neo4j.py (In-memory mock graph client for offline test runs)
    ├── helpers.py (Auth token and request generators)
    └── isolation_preflight.py (Strict test database & artifact guard)
```

```
client/ (8 test files)
├── client/admin/tests/
│   ├── phase1_audit_validation.test.mjs
│   ├── phase2_settings_mapping.test.mjs
│   ├── phase3_ingestion_ui.test.mjs
│   ├── phase3_dashboard_graph.test.mjs
│   ├── phase4_user_admin_integration.test.mjs
│   ├── document_details_and_graph_regression.test.mjs
│   └── phase5_ui_polish.test.mjs
└── client/user/tests/
    └── graph_and_ui_polish.test.mjs
```

---

### 2. Execution Evidence & Pass Rates

| Test Layer | Discovered Tests | Executed Tests | Passing | Failing | Pass Rate | Authoritative Evidence File |
|---|---|---|---|---|---|---|
| **Backend (Phase 1 Baseline)** | 104 | 104 | 104 | 0 | **100.0%** | `server/api/.pytest-phase1.xml` (27.75s) |
| **Backend (Phase 14–17 Final)** | 337 | 337 | 337 | 0 | **100.0%** | `docs/PROJECT_COMPLETION_REPORT.md:L7`, `FINAL_EXPERIMENTAL_RESULTS.md:L92` |
| **Admin Frontend Tests** | 57 | 57 | 57 | 0 | **100.0%** | `client/admin/package.json:L10`, `AUDIT_CHECKLIST.md:L11` |
| **User Frontend Tests** | 12 | 12 | 12 | 0 | **100.0%** | `client/user/package.json:L10` |
| **Total Test Suite** | **406** | **406** | **406** | **0** | **100.0%** | Comprehensive cross-layer passing status |

---

### 3. Safety Preflight & Isolation Verification (`server/api/tests/isolation_preflight.py`)

A unique engineering achievement of this repository is its strict **Isolation Preflight Subsystem** designed to eliminate the risk of automated test runs mutating production indexes or external databases:

1. **Loopback IP Enforcement:** Rejects any database target whose hostname fails to resolve strictly to loopback IP addresses (`127.0.0.1`, `::1`, `localhost`) (`isolation_preflight.py:L56-L81`).
2. **Database Name Allowlist:** Strictly rejects protected or production database names (`postgres`, `legalgraph`, `juris`, `juris_production`, `prod`, `template0`, `template1`). Requires that test databases end with the suffix `_test` (`isolation_preflight.py:L29-L44`).
3. **Storage Directory Safety Gate:** Prohibits tests from using the production data directory (`PROJECT_ROOT/data`). Tests must specify temporary scratch directories (`tmp_path`) (`isolation_preflight.py:L130-L150`).
4. **Protected Artifact Guard (`ProtectedArtifactGuard`):** Computes SHA-256 hashes of the authoritative vector index (`data/indexes/legal_chunks/index.faiss`) and raw legal corpus before test execution and verifies that no test mutates these files (`isolation_preflight.py:L180-L245`).

---

### 4. Dependency Verification & Environment Manifests

| Subsystem | Manifest File | Primary Dependencies & Pinned Versions | Lockfile Present |
|---|---|---|---|
| **Backend API** | `server/api/pyproject.toml` | Python `>=3.12,<3.13`, FastAPI `>=0.115`, SQLAlchemy `>=2.0`, FAISS-CPU `>=1.10`, Neo4j `>=5.26`, PyTorch `>=2.6`, Transformers `>=4.48`, ONNXRuntime `>=1.18`, PyMuPDF `>=1.24` | Yes (`server/api/uv.lock`, 161 KB) |
| **Embedding Microservice** | `embedding-service/pyproject.toml` | FastAPI `>=0.115`, ONNXRuntime `>=1.18`, Transformers `>=4.48`, NumPy `>=2.0` | Yes |
| **Admin Portal** | `client/admin/package.json` | Next.js `16.0.10`, React `19.2.0`, TailwindCSS `4.1.9`, Lucide React `0.454.0` | Yes |
| **User Portal** | `client/user/package.json` | Next.js `16.0.10`, React `19.2.0`, TailwindCSS `4.1.9`, Lucide React `0.454.0` | Yes |
| **Landing Page** | `client/landing/package.json` | Next.js `16.0.10`, React `19.2.0`, Radix UI, Three.js `0.183.2`, `@react-three/fiber` `9.5.0` | Yes |

---

### 5. Deployment Configuration & Infrastructure Status

#### Docker Compose Topology (`docker-compose.yml`)
- **Service `postgres`:** Image `postgres:16-alpine`, exposed on host port `5434` (mapped to internal container port `5432`). Environment configured with `POSTGRES_DB=legalgraph`. Healthcheck configured with `pg_isready`.
- **Service `neo4j`:** Image `neo4j:5-community`, exposed on HTTP port `7474` and Bolt port `7687`. Configured with authentication `neo4j/testpassword123`.
- **Service `api`:** Built from `server/api/Dockerfile`, exposes port `8000`. Depends on `postgres` and `neo4j` services.
- **Service `embedding-service` (Optional):** Built from `embedding-service/Dockerfile`, exposes port `8001`.

#### Cloud Hosting Configuration
- **Backend API:** Multi-target support via `render.yaml` (Render Web Service) and `phase7b_azure_observability.ps1` (Azure App Service).
- **Client Portals:** Vercel edge configuration files present in `client/admin/vercel.json`, `client/user/vercel.json`, and `client/landing/vercel.json`. Configures client-side rewrite rules and custom headers.

#### Startup & Health Check Verification (`server/api/app/api/routes/health.py`)
The backend provides 4 comprehensive health check endpoints:
1. `GET /health`: Basic service liveness and API version (`0.6.1`).
2. `GET /health/live`: Lightweight orchestrator liveness probe (HTTP 200).
3. `GET /health/ready`: Readiness probe verifying PostgreSQL connection and FAISS vector index accessibility.
4. `GET /health/detailed`: Deep diagnostic probe reporting database ping latency, Neo4j connectivity and node/relationship counts, FAISS vector count, and embedding model availability.

---

### 6. Known Failure Cases & Operational Risks

1. **Scanned PDF Ingestion Failure:**
   - **Document:** `judgements/supreme_court/02_indira_nehru_gandhi_raj_narain_1975.pdf` (*Indira Gandhi 1975*).
   - **Behavior:** Rejected during text extraction with status `FAILED / OCR_REQUIRED`.
   - **Handling:** Does not crash the ingestion daemon; flagged in database and excluded from index.
2. **Neo4j Network Timeout Resiliency:**
   - **Behavior:** In earlier phases, network timeouts during graph expansion caused QA queries to fail with HTTP 500.
   - **Fix:** `app/rag/pipeline.py:L407-L417` catches timeouts and connection errors, setting `fallback="dense_only"`, logging a diagnostic warning, and completing query synthesis.
3. **Windows Selector Event Loop Dependency:**
   - **Behavior:** Under Python on Windows, the default Proactor event loop causes `psycopg.InterfaceError` during asynchronous session teardown.
   - **Fix:** `server/api/app/main.py:L9-L10` explicitly enforces `asyncio.WindowsSelectorEventLoopPolicy()`.
