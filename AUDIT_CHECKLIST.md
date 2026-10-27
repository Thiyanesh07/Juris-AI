# Juris AI — Complete System Audit, Repair and End-to-End Validation Checklist

## Stage 1 — Repository and Architecture Audit
- [x] Backend architecture, routing, schemas, and service layer inspected
- [x] Database schema, models, and migrations inspected
- [x] Vector search (InLegalBERT + FAISS) inspected
- [x] Knowledge graph (Neo4j client, traversal, population) inspected
- [x] Frontend applications (Admin, User, Landing, Shared) inspected
- [x] Baseline test suite executed:
  - Backend: 392 passed, 3 failed (out of 395)
  - Admin Frontend: 57 passed, 0 failed (out of 57)
- [x] Root causes diagnosed and prioritized repair plan established

## Stage 2 — Database and Persistence Diagnostics
- [ ] Ensure Windows Selector event loop policy is applied across backend startup and session creation to prevent `psycopg.InterfaceError` under Windows Proactor loop
- [ ] Verify PostgreSQL schema and tables consistency
- [ ] Fix ID mismatch between PostgreSQL chunk/document records and FAISS vector index metadata
- [ ] Validate Neo4j instance connectivity and establish fallback / local graph resiliency
- [ ] Test application restart recovery of indexes and sessions

## Stage 3 — Document Ingestion Reliability
- [ ] Fix Stage 8 (GRAPH_POPULATION) failure handling and network timeout resiliency
- [ ] Verify complete 8-stage document ingestion pipeline:
  1. Ingestion / PDF validation & checksum
  2. Extraction (PyMuPDF text extraction)
  3. Legal hierarchy chunking
  4. Embedding generation (InLegalBERT ONNX)
  5. FAISS vector index insertion
  6. Legal entity extraction
  7. Relationship extraction & provenance keying
  8. Graph population
- [ ] Verify background job tracking, progress states, and error persistence in `processing_jobs`
- [ ] Fix 3 failing ingestion pipeline unit tests (`tests/test_ingestion_pipeline.py`)
- [ ] Verify file persistence under `data/raw`, `data/processed`, `data/chunks`

## Stage 4 — Knowledge Graph Restoration
- [ ] Verify graph node and edge extraction rules on Indian legal texts
- [ ] Populate knowledge graph with real entities from READY corpus documents
- [ ] Verify Neo4j constraints, indexes, and schema enforcement
- [ ] Test graph traversal, search (`/graph/search`), node detail (`/graph/nodes/{id}`), and neighbors (`/graph/neighbors/{id}`)
- [ ] Test admin graph explorer UI with real nodes and relationships (no mock fallback)
- [ ] Ensure graph statistics endpoint (`/health` and `/graph`) reports accurate counts

## Stage 5 — Semantic Retrieval and GraphRAG Validation
- [ ] Rebuild and align FAISS vector index with PostgreSQL chunk records
- [ ] Verify dense retrieval returns relevant chunks for legal queries
- [ ] Verify bounded 2-hop hybrid graph expansion returns valid bridges
- [ ] Test LLM Legal QA pipeline with real retrieved context
- [ ] Verify citation attribution and prevent hallucinated provisions
- [ ] Test edge cases: empty results, missing graph data, unavailable LLM provider

## Stage 6 — User and Admin Feature Verification
- [ ] Admin Dashboard: metrics, ingestion status, document table, graph stats
- [ ] Admin Document Management: upload, list, detail, chunk inspector, reprocess, archive, restore
- [ ] Admin Ingestion Telemetry: job states, timings, error logs
- [ ] Admin User Management: user list, role modification, deactivation
- [ ] Admin Audit Logs & System Settings: persistent configuration
- [ ] User Portal: legal search, multi-hop GraphRAG QA, research history, saved research

## Stage 7 — Logging, Validation, and Operational Reliability
- [ ] Structured logging for all ingestion stages, errors, and vector/graph operations
- [ ] Detailed health checks (`/health/ready`, `/health/live`, `/health/detailed`)
- [ ] Sanitized error details and security enforcement

## Stage 8 — Automated and End-to-End Testing
- [ ] Unit & integration tests for all repaired components
- [ ] End-to-end test: real legal PDF upload -> ingestion -> FAISS indexing -> graph population -> hybrid search -> QA answer with citations
- [ ] Persistence test across process restarts

## Stage 9 — Deployment Verification
- [ ] Environment variable validation (.env, .env.example)
- [ ] CORS and API endpoint configuration
- [ ] Production build validation (`next build` for admin and user clients)
- [ ] Final evidence-based report
