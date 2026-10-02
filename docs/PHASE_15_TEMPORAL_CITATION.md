# Phase 15 — Temporal Legal Reasoning & Citation Grounding Documentation

## 1. Architecture Overview

Phase 15 extends the Phase 14 Hybrid GraphRAG architecture by introducing a clean, provenance-backed temporal legal reasoning layer and structural citation verification.

```
USER QUERY
    │
    ▼
QUERY ANALYSIS Node
 (Regex + Heuristics: extracts target_date, date_range, temporal_operator, referenced_amendment)
    │
    ▼
LEGAL VERSION RESOLUTION Node
 (Resolves entity versions against canonical milestone registry: IN_FORCE, SUPERSEDED, REPEALED, HISTORICAL, UNKNOWN)
    │
    ▼
HYBRID RETRIEVAL Node
 (Parallel InLegalBERT FAISS Dense + Neo4j Cypher Multi-Hop Graph Traversal)
    │
    ▼
TEMPORAL VALIDITY FILTER & FUSION Node
 (Reranks evidence preserving historical context for temporal queries; prevents superseded evidence from masquerading as current law)
    │
    ▼
GROUNDED LLM SYNTHESIS Node
 (Server-side prompt forcing temporal distinction, evidence-bounded reasoning, and explicit date/amendment rules)
    │
    ▼
CITATION EXTRACTION & VERIFICATION Node
 (Regex pattern extraction for SCC, AIR, SCR, SCALE, Article/Section; verifies against raw chunk ID, document ID, page number, and provenance)
    │
    ▼
TEMPORAL GROUNDEDNESS VALIDATION Node
 (Validates citation claims, temporal consistency, and produces structured validation report)
    │
    ▼
FINAL QA RESPONSE
 (Structured JSON with answer, citations, evidence, graph, reasoning steps, temporal metadata, timeline events, & citation validation)
```

---

## 2. Temporal Data Model & Legal Version Resolution

### Data Schema (`app/rag/temporal.py`)
```python
TemporalStatus = Literal[
    "IN_FORCE",
    "SUPERSEDED",
    "REPEALED",
    "NOT_YET_IN_FORCE",
    "HISTORICAL",
    "UNKNOWN",
]

class LegalVersionInfo(BaseModel):
    entity_id: str
    version_label: str
    effective_from: str | None = None
    effective_to: str | None = None
    status: TemporalStatus = "UNKNOWN"
    amendment_id: str | None = None
    amendment_title: str | None = None
    version_source: str = "corpus_registry"
    temporal_confidence: float = 1.0
```

### Version Resolution Rules
- **No Target Date:** Resolves to current `IN_FORCE` version.
- **Explicit Target Date/Year:** Matches against effective date ranges `[effective_from, effective_to]`.
- **Pre-Enactment:** Returns `NOT_YET_IN_FORCE`.
- **Unmapped/Uncertain:** Returns `status="UNKNOWN"` with `temporal_confidence=0.0`. Never manufactures dates or assumes current status without evidence.

---

## 3. Amendment Model & Temporal Graph Traversal

- **Neo4j Relationships:** Leverages `AMENDS`, `MODIFIES`, `SUPERSEDES` relationships established in Phase 13/14.
- **Provenance Preservation:** All amendment traversals retain `source_document_id`, `source_chunk_id`, `page_start`, `page_end`, `evidence_text`, and SHA-256 provenance fingerprints.
- **Bounded Bipartite Traversal:** Default depth 2–3, maximum depth 5, cycle detection enabled.

---

## 4. Temporal Query Analysis

### Supported Temporal Expressions
- **Operators:** `BEFORE`, `AFTER`, `SINCE`, `UNTIL`, `AS_OF`, `HISTORICAL`, `CURRENT_LAW`.
- **Date/Year Extraction:** Parses explicit 4-digit years (e.g., `1978`, `2010`, `2015`).
- **Amendment Identification:** Detects explicit ordinal/named amendments (e.g., `44th Amendment`, `IT Amendment Act 2008`).

---

## 5. Citation Extraction & Verification

### Citation Patterns (`app/rag/citation_verifier.py`)
- **SCC:** `(1978) 1 SCC 248`, `[2015] 5 SCC 1`
- **AIR:** `AIR 1978 SC 597`, `AIR 2015 SC 1523`
- **SCR / SCALE:** `(1978) 2 SCR 621`, `2015 (3) SCALE 1`
- **Provisions:** `Article 21 of the Constitution`, `Section 66A of the IT Act`

### Verification Levels
1. **VERIFIED:** Valid `chunk_id`, `document_id`, page metadata, and matching formal citation or citation ref in chunk text.
2. **PARTIALLY_VERIFIED:** Valid chunk/document IDs with partial textual support.
3. **UNVERIFIED:** Missing provenance, unknown chunk ID, or unsupported claims.
4. **CONTRADICTED:** Citation contradicts chunk text or source document.

---

## 6. Response Schema Extension (`app/schemas/qa.py`)

Added backward-compatible temporal and citation validation fields:

```python
class QATimelineEvent(BaseModel):
    id: str
    year: str
    title: str
    documentType: str
    description: str
    importance: Literal["HIGH", "MEDIUM", "LOW"]

class QATemporalMeta(BaseModel):
    detected: bool = False
    target_date: str | None = None
    target_year: int | None = None
    date_range: dict[str, Any] | None = None
    temporal_operator: str | None = None
    referenced_amendment: str | None = None
    resolution_status: str = "UNKNOWN"
    timeline_events: list[QATimelineEvent] = Field(default_factory=list)

class QACitationValidation(BaseModel):
    verified_count: int = 0
    unverified_count: int = 0
    grounded: bool = True
    warnings: list[str] = Field(default_factory=list)
```

---

## 7. Frontend Integration (`client/user`)

- **Types (`qaApi.ts`):** Added `BackendQATimelineEvent`, `BackendQATemporalMeta`, `BackendQACitationValidation`.
- **Normalizer (`normalizeQA.ts`):** Maps `response.temporal.timeline_events` into `ResearchResult.timeline` and sets `timelineAvailable = timeline.length > 0`.
- **Timeline Tab (`LegalTimelineTab.tsx`):** Renders real chronological amendment & landmark case milestones when temporal metadata is returned, or displays an honest state when unavailable.

---

## 8. Test Baseline Summary

- **Total Backend Tests:** 326 / 326 PASSING.
- **Phase 14 Baseline:** 311 tests passing.
- **Phase 15 Tests Added:** 15 focused tests across:
  - `test_phase15_temporal_query.py` (4 tests)
  - `test_phase15_version_resolution.py` (5 tests)
  - `test_phase15_citation_verification.py` (3 tests)
  - `test_phase15_pipeline_integration.py` (3 tests)
- **Frontend Builds:** `client/user`, `client/admin`, and `client/landing` Next.js production builds passing cleanly.

---

## 9. Status & Implementation Matrix

| Feature | Status | Notes |
|---|---|---|
| Temporal Query Extraction | IMPLEMENTED | Parses years, amendments, and temporal operators |
| Legal Version Resolution | IMPLEMENTED | Supported via milestone registry & date matching |
| Amendment Traversal | IMPLEMENTED | Uses Neo4j AMENDS / MODIFIES relationships |
| Citation Extraction | IMPLEMENTED | Regex matching for SCC, AIR, SCR, SCALE, Provisions |
| Citation Verification | IMPLEMENTED | Verified against chunk ID, document ID, page, & text |
| Timeline UI Integration | IMPLEMENTED | Grounded events rendered in User Portal |
| Phase 16 Scope | NOT IMPLEMENTED | Strictly scoped to Phase 15 requirements |
