/**
 * JURIS AI — SHARED BACKEND TYPES
 *
 * TypeScript types that correspond exactly to the backend response schemas
 * discovered during the Phase 11 audit. These are the canonical types for
 * all data structures that cross the network boundary.
 *
 * DO NOT invent types for endpoints that do not exist.
 * DO NOT put UI-only types here; keep them in their respective portal lib/types.ts.
 *
 * Source of truth: server/api/app/schemas/ and server/api/app/models/enums.py
 */

// ── Auth / User ───────────────────────────────────────────────────────────────

/**
 * Lowercase role strings as returned by the backend.
 * The backend uses StrEnum: UserRole.USER = "user", etc.
 * Note: admin portal lib/types.ts uses uppercase — convert with normalizeRole().
 */
export type BackendUserRole = 'user' | 'admin' | 'super_admin';

/**
 * GET /auth/me response — CurrentUserResponse schema.
 * Matches app/schemas/auth.py::CurrentUserResponse exactly.
 */
export interface AuthUser {
  id: string;               // UUID as string
  email: string;
  name: string | null;
  image_url: string | null;
  role: BackendUserRole;    // lowercase: "user" | "admin" | "super_admin"
  is_active: boolean;
  last_login_at: string | null;  // ISO datetime or null
}

// ── Documents ─────────────────────────────────────────────────────────────────

/**
 * Backend document status values (lowercase, from DocumentStatus StrEnum).
 */
export type BackendDocumentStatus =
  | 'registered'
  | 'processing'
  | 'ready'
  | 'failed'
  | 'disabled';

/**
 * Backend document type values (lowercase, from DocumentType StrEnum).
 */
export type BackendDocumentType =
  | 'constitution'
  | 'act'
  | 'statute'
  | 'judgment'
  | 'rule'
  | 'regulation'
  | 'other';

/**
 * GET /documents — DocumentSummary schema.
 * Matches app/schemas/documents.py::DocumentSummary.
 */
export interface DocumentSummary {
  id: string;          // UUID
  title: string;
  type: string;        // BackendDocumentType
  source: string;
  status: string;      // BackendDocumentStatus
  file_hash: string | null;
  created_at: string;  // ISO datetime
  updated_at: string;
}

/**
 * GET /documents/{id} — DocumentDetail schema.
 */
export interface DocumentDetail extends DocumentSummary {
  source_url: string | null;
  file_path: string | null;
}

/**
 * Paginated documents response.
 */
export interface PaginatedDocuments {
  items: DocumentSummary[];
  total: number;
  page: number;
  page_size: number;
}

/**
 * POST /documents/upload — DocumentUploadResponse schema.
 */
export interface DocumentUploadResponse {
  document_id: string;  // UUID
  message: string;
  status: string;
  duplicate: boolean;
}

/**
 * POST /documents/{id}/reprocess — ReprocessResponse schema.
 */
export interface ReprocessResponse {
  document_id: string;  // UUID
  message: string;
}

/**
 * GET /documents/{id}/chunks — ChunkSchema.
 */
export interface DocumentChunk {
  id: string;                  // UUID
  document_id: string;         // UUID
  document_version_id: string | null;  // UUID or null
  chunk_index: number;
  char_count: number;
  page_start: number | null;
  page_end: number | null;
  hierarchy: Record<string, unknown>;
  citation_ref: string | null;
  text: string;
  created_at: string;
}

export interface PaginatedChunks {
  items: DocumentChunk[];
  total: number;
  page: number;
  page_size: number;
}

/**
 * GET /documents/{id}/jobs — ProcessingJobSchema.
 */
export interface ProcessingJob {
  id: string;          // UUID
  document_id: string; // UUID
  stage: string;       // ProcessingJobStage enum value
  status: string;      // ProcessingJobStatus enum value
  error: string | null;
  created_at: string;
  updated_at: string;
}

// ── Health ────────────────────────────────────────────────────────────────────

/**
 * GET /health — HealthResponse schema.
 */
export interface DatabaseComponent {
  status: 'ok' | 'unreachable';
  error: string | null;
}

export interface HealthResponse {
  status: 'ok' | 'degraded';
  service: 'legalgraph-api';
  version: string;
  components: {
    database: DatabaseComponent;
  };
}

/**
 * GET /health/database — DatabaseHealthResponse schema.
 */
export interface DatabaseHealthResponse {
  status: 'ok' | 'unavailable';
  database: DatabaseComponent;
}

// ── Retrieval ─────────────────────────────────────────────────────────────────

/**
 * POST /retrieval/search — RetrievalRequest.
 */
export interface RetrievalRequest {
  query: string;
  top_k?: number | null;
}

/**
 * POST /retrieval/search — RetrievalResponse evidence item.
 */
export interface RetrievalEvidence {
  rank: number;
  score: number;
  chunk_id: string;           // UUID
  document_id: string;        // UUID
  document_version_id: string | null;  // UUID or null
  chunk_index: number;
  text: string;
  page_start: number | null;
  page_end: number | null;
  hierarchy: Record<string, unknown>;
  citation_ref: string | null;
  source_url: string | null;
  document_title: string;
}

/**
 * POST /retrieval/search — RetrievalResponse.
 */
export interface RetrievalResponse {
  query: string;
  results: RetrievalEvidence[];
  score_type: string;
}

// ── Hybrid Retrieval ──────────────────────────────────────────────────────────

/**
 * POST /retrieval/hybrid — HybridRetrievalRequest.
 */
export interface HybridRetrievalRequest {
  query: string;
  top_k?: number | null;
}

/**
 * Graph entity context embedded in hybrid evidence.
 */
export interface HybridGraphEntityContext {
  id: string;
  label: string;
  name: string;
}

/**
 * Graph context embedded in hybrid evidence.
 */
export interface HybridGraphContext {
  hops: number;
  seed_chunk_ids: string[];
  entities: HybridGraphEntityContext[];
}

/**
 * Individual hybrid evidence item.
 */
export interface HybridEvidence {
  rank: number;
  chunk_id: string;           // UUID
  document_id: string;        // UUID
  document_title: string;
  document_version_id: string | null;
  chunk_index: number;
  text: string;
  page_start: number | null;
  page_end: number | null;
  hierarchy: Record<string, unknown>;
  citation_ref: string | null;
  source_url: string | null;
  dense_score: number;
  graph_score: number;
  hybrid_score: number;
  dense_rank: number | null;
  graph_rank: number | null;
  dense_matched: boolean;
  evidence_sources: Array<'dense' | 'graph'>;
  graph_context: HybridGraphContext | null;
}

/**
 * POST /retrieval/hybrid — HybridRetrievalResponse.
 */
export interface HybridRetrievalResponse {
  query: string;
  mode: 'hybrid';
  fallback: 'dense_only' | null;
  fallback_reason:
    | 'neo4j_unavailable'
    | 'neo4j_timeout'
    | 'neo4j_query_failed'
    | null;
  weights: { vector: number; graph: number };
  score_type: string;
  warnings: string[];
  results: HybridEvidence[];
}

// ── QA ────────────────────────────────────────────────────────────────────────

/**
 * POST /qa/ask — QAAskRequest.
 */
export interface QAAskRequest {
  query: string;
  top_k?: number | null;
}

/**
 * QA citation item.
 */
export interface QACitation {
  marker: number;
  evidence_rank: number;
  chunk_id: string;           // UUID
  document_id: string;        // UUID
  document_title: string;
  document_version_id: string | null;
  chunk_index: number;
  citation_ref: string | null;
  page_start: number | null;
  page_end: number | null;
  source_url: string | null;
}

/**
 * QA retrieval metadata.
 */
export interface QARetrievalMeta {
  mode: 'hybrid';
  fallback: 'dense_only' | null;
  fallback_reason:
    | 'neo4j_unavailable'
    | 'neo4j_timeout'
    | 'neo4j_query_failed'
    | null;
  warnings: string[];
  evidence_count: number;
  evidence_dropped_for_context: number;
}

/**
 * POST /qa/ask — QAAskResponse.
 */
export interface QAAskResponse {
  query: string;
  status: 'answered' | 'insufficient_evidence';
  answer: string | null;
  insufficient_evidence: boolean;
  citations: QACitation[];
  evidence: HybridEvidence[];
  retrieval: QARetrievalMeta;
  provider: string;
  model: string;
  llm_called: boolean;
  timings_ms: { retrieval: number; llm: number };
  disclaimer: string;
}

// ── Evaluation ────────────────────────────────────────────────────────────────

/**
 * GET /evaluation — EvaluationRunSchema.
 */
export interface EvaluationRun {
  id: string;          // UUID
  name: string;
  configuration: Record<string, unknown> | null;
  results: Record<string, unknown> | null;
  created_at: string;
}

export interface PaginatedEvaluationRuns {
  items: EvaluationRun[];
  total: number;
  page: number;
  page_size: number;
}

// ── Shared Pagination ─────────────────────────────────────────────────────────

/**
 * Generic paginated response shape (convenience alias).
 */
export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

// ── Utility ───────────────────────────────────────────────────────────────────

/**
 * Convert a backend lowercase role to the uppercase variant used by the admin portal.
 */
export function normalizeRoleToUppercase(role: BackendUserRole): 'USER' | 'ADMIN' | 'SUPER_ADMIN' {
  switch (role) {
    case 'user': return 'USER';
    case 'admin': return 'ADMIN';
    case 'super_admin': return 'SUPER_ADMIN';
    default: return 'USER';
  }
}

/**
 * Convert an uppercase frontend role to the lowercase backend variant.
 */
export function normalizeRoleToLowercase(role: string): BackendUserRole {
  switch (role?.toUpperCase()) {
    case 'ADMIN': return 'admin';
    case 'SUPER_ADMIN': return 'super_admin';
    default: return 'user';
  }
}
