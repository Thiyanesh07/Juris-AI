# Phase 16 — Admin Backend, Persistence & Evaluation Documentation

## 1. Architecture Overview

Phase 16 establishes PostgreSQL as the authoritative store for administrative metadata, user RBAC, human-in-the-loop validation queue items, append-only operational audit logs, system configuration sections, user research history, and saved research session bookmarks. It also introduces a reproducible benchmarking and evaluation framework comparing `VECTOR_ONLY`, `GRAPH_ONLY`, and `HYBRID` retrieval strategies.

```
+-------------------------------------------------------------------+
|                        FRONTEND CLIENTS                           |
|       User Portal (/user)               Admin Portal (/admin)     |
+-------------------------------------------------------------------+
                                  │
                                  ▼  HTTP REST (HttpOnly Session Auth)
+-------------------------------------------------------------------+
|                       FASTAPI BACKEND SYSTEM                      |
|                                                                   |
|   /auth               /admin/users          /validation           |
|   /audit              /settings             /graph (read-only)    |
|   /research/history   /research/saved       /evaluation           |
+-------------------------------------------------------------------+
           │                                          │
           ▼ (SQLAlchemy Async)                       ▼ (Cypher / FAISS)
+-------------------------+               +-------------------------+
|     POSTGRESQL DB       |               |    NEO4J & FAISS INDEX  |
|  - Users & Roles        |               |  - Provenance-Backed    |
|  - Documents & Chunks   |               |    Legal Entities       |
|  - Validation Items     |               |  - Multi-Hop Triples    |
|  - System Events/Audit  |               |  - Vector Index (768d)  |
|  - System Settings      |               +-------------------------+
|  - Research Sessions    |
|  - Evaluation Runs      |
+-------------------------+
```

---

## 2. PostgreSQL Models & Alembic Migration

### Data Models (`app/models/`)
- `User`: Roles (`user`, `admin`, `super_admin`), `is_active`, `last_login_at`, email/password authentication.
- `ValidationItem`: Entity/triple human-in-the-loop validation (`item_type`, `status`, `confidence`, `proposed_payload`, `evidence_text`, `reviewer_id`, `decision_timestamp`, `rejection_note`).
- `SystemEvent`: Append-only audit and operational events (`event_type`, `actor_id`, `event_metadata`).
- `SystemSetting`: Configuration section settings (`section`, `config_json`, `updated_by_id`).
- `ResearchSession`, `ResearchQuery`, `ResearchAnswer`: Structured user research thread history.
- `SavedResearch`: User research bookmarks linking users to research sessions.
- `EvaluationRun`: Versioned benchmark evaluation run results (`name`, `configuration`, `results`).

### Migration Script
- `alembic/versions/20261002_phase16_models.py` (Revision ID: `d8e9f0a1b2c3`): Adds `system_settings` and `validation_items` tables with indices and foreign key constraints.

---

## 3. Server-Side Security & RBAC Enforcement

- **SUPER_ADMIN:** Exclusive permissions to provision new administrators (`POST /admin/admins`), promote users to admin roles, and modify administrative configurations. Super Admin accounts cannot be disabled or demoted via ordinary admin endpoints.
- **ADMIN:** Read/update access for non-super-admin users, document management, validation queue review, audit log access, system settings management, read-only graph inspection, and triggering evaluation benchmark runs.
- **USER:** Restricted to own profile (`GET /users/me`), own research history (`/research/history`), own saved bookmarks (`/research/saved`), and QA query execution (`/qa/ask`). Admin APIs strictly enforce HTTP 403 Forbidden for non-admin users.

---

## 4. Administrative Features

### A. Validation Queue Backend (`/validation`)
- Endpoints: `GET /validation`, `GET /validation/{id}`, `POST /validation/{id}/approve`, `POST /validation/{id}/reject`, `POST /validation/bulk-approve`.
- Persists decision timestamps, reviewer user IDs, and optional rejection reasons. Logs `VALIDATION.APPROVE` or `VALIDATION.REJECT` audit events.

### B. Audit Log Persistence (`/audit`)
- Endpoints: `GET /audit`, `GET /audit/{id}`.
- Append-only event tracking for `AUTHENTICATION`, `USER_MANAGEMENT`, `ADMIN_MANAGEMENT`, `DOCUMENT`, `INGESTION`, `KNOWLEDGE_GRAPH`, `VALIDATION`, `SETTINGS`, and `SECURITY`. Includes actor ID, target resource, result status, severity, IP address, user agent, and before/after state diffs.

### C. System Settings (`/settings`)
- Endpoints: `GET /settings`, `GET /settings/{section}`, `PUT /settings/{section}`.
- Categories: `GENERAL`, `AI_LLM`, `EMBEDDINGS`, `RETRIEVAL`, `INGESTION`, `KNOWLEDGE_GRAPH`, `SECURITY`.
- Security: Automatically masks API keys, secrets, passwords, and tokens (`********`) before returning JSON payloads to client. Logs `SETTINGS.UPDATE` audit events.

### D. Knowledge Graph Admin API (`/graph`)
- Endpoints: `GET /graph/search`, `GET /graph/nodes/{id}`, `GET /graph/neighbors/{id}`, `GET /graph/subgraph`.
- Read-only Neo4j Cypher querying. Strictly bounds multi-hop traversal depth (default 3, maximum 5).

---

## 5. Reproducible Benchmarking & Evaluation Framework

### Benchmark Dataset (`server/data/evaluation/`)
- `questions.json`: 9 representative legal queries spanning Constitutional, Statutory, Case Law, and Temporal domains.
- `expected_citations.json`: Ground-truth legal citations.
- `expected_entities.json`: Canonical legal entity IDs.
- `expected_relationships.json`: Expected entity-relationship triples.
- `expected_temporal_facts.json`: Historical date boundaries and temporal milestones.

### Evaluated Strategies
1. `vector_only` (Dense vector retrieval via InLegalBERT FAISS).
2. `graph_only` (Neo4j Cypher multi-hop graph traversal).
3. `hybrid` (Reciprocal Rank Fusion of Dense + Graph evidence).

### Evaluated Metrics
- **Recall@K & Precision@K:** Proportion of ground-truth entities and citations retrieved.
- **Mean Reciprocal Rank (MRR):** Reciprocal rank of the first relevant chunk.
- **Citation Verification Rate:** Proportion of generated citations verified against raw chunk provenance.
- **Temporal Fact Accuracy:** Date extraction and version resolution accuracy.

### Benchmark Run Execution (`POST /evaluation/run`)
- Executes automated evaluation across specified strategies and saves structured JSON metric payloads into PostgreSQL `evaluation_runs`.

---

## 6. Verification Summary

- **Total Backend Tests:** **337 / 337 PASSING** (326 Phase 15 baseline + 11 new Phase 16 tests).
- **Frontend Next.js Builds:**
  - `client/user`: `npm run build` — SUCCESS
  - `client/admin`: `npm run build` — SUCCESS
  - `client/landing`: `npm run build` — SUCCESS
- **Alembic Migrations:** Database migration `d8e9f0a1b2c3` verified up and down.
- **Phase 17 Exclusions:** Confirmed. No deployment, containerization, or final release hardening initiated.
