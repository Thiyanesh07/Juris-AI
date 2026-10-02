/**
 * JURIS AI — ADMIN PORTAL API FOUNDATION
 *
 * Portal-local API infrastructure. These files re-implement the shared API
 * contract inline to work with Turbopack (Next.js 16), which cannot resolve
 * imports outside the project root.
 *
 * Canonical shared types live in: client/shared/api/types.ts
 * This file is the admin portal's local copy.
 */

// ── Auth / User ───────────────────────────────────────────────────────────────

export type BackendUserRole = 'user' | 'admin' | 'super_admin';

/**
 * GET /auth/me response — CurrentUserResponse schema.
 * Matches server/api/app/schemas/auth.py::CurrentUserResponse exactly.
 */
export interface AuthUser {
  id: string;
  email: string;
  name: string | null;
  image_url: string | null;
  role: BackendUserRole;
  is_active: boolean;
  last_login_at: string | null;
}

// ── Documents ─────────────────────────────────────────────────────────────────

export type BackendDocumentStatus = 'registered' | 'processing' | 'ready' | 'failed' | 'disabled';
export type BackendDocumentType = 'constitution' | 'act' | 'statute' | 'judgment' | 'rule' | 'regulation' | 'other';

export interface DocumentSummary {
  id: string;
  title: string;
  type: string;
  source: string;
  status: string;
  file_hash: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentDetail extends DocumentSummary {
  source_url: string | null;
  file_path: string | null;
}

export interface PaginatedDocuments {
  items: DocumentSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface DocumentUploadResponse {
  document_id: string;
  message: string;
  status: string;
  duplicate: boolean;
}

export interface ReprocessResponse {
  document_id: string;
  message: string;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  document_version_id: string | null;
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

export interface ProcessingJob {
  id: string;
  document_id: string;
  stage: string;
  status: string;
  error: string | null;
  created_at: string;
  updated_at: string;
}

// ── Health ────────────────────────────────────────────────────────────────────

export interface DatabaseComponent {
  status: 'ok' | 'unreachable';
  error: string | null;
}

export interface HealthResponse {
  status: 'ok' | 'degraded';
  service: 'legalgraph-api';
  version: string;
  components: { database: DatabaseComponent };
}

export interface DatabaseHealthResponse {
  status: 'ok' | 'unavailable';
  database: DatabaseComponent;
}

// ── Evaluation ────────────────────────────────────────────────────────────────

export interface EvaluationRun {
  id: string;
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

// ── Utility ───────────────────────────────────────────────────────────────────

export function normalizeRoleToUppercase(role: BackendUserRole): 'USER' | 'ADMIN' | 'SUPER_ADMIN' {
  switch (role) {
    case 'user': return 'USER';
    case 'admin': return 'ADMIN';
    case 'super_admin': return 'SUPER_ADMIN';
    default: return 'USER';
  }
}

export function normalizeRoleToLowercase(role: string): BackendUserRole {
  switch (role?.toUpperCase()) {
    case 'ADMIN': return 'admin';
    case 'SUPER_ADMIN': return 'super_admin';
    default: return 'user';
  }
}
