/**
 * JURIS AI — SHARED DOCUMENTS API FUNCTIONS
 *
 * Typed wrappers for backend document endpoints.
 * All endpoints verified in server/api/app/api/routes/documents.py.
 *
 * Authentication:
 *   - Upload / Reprocess: ADMIN or SUPER_ADMIN (require_admin)
 *   - Read endpoints:     any authenticated user (get_current_user)
 *
 * Endpoint inventory:
 *   POST /documents/upload              → DocumentUploadResponse [202] — ADMIN only
 *   GET  /documents                     → PaginatedDocuments — any auth user
 *   GET  /documents/{id}               → DocumentDetail — any auth user
 *   GET  /documents/{id}/chunks        → PaginatedChunks — any auth user
 *   GET  /documents/{id}/jobs          → ProcessingJob[] — any auth user
 *   POST /documents/{id}/reprocess     → ReprocessResponse [202] — ADMIN only
 */

import { apiClient } from './client';
import type {
  DocumentSummary,
  DocumentDetail,
  DocumentUploadResponse,
  ReprocessResponse,
  DocumentChunk,
  PaginatedChunks,
  ProcessingJob,
  PaginatedDocuments,
} from './types';

export interface ListDocumentsParams {
  page?: number;
  page_size?: number;
  status?: string;  // DocumentStatus enum value
}

export interface UploadDocumentParams {
  title: string;
  type?: string;   // DocumentType enum value; defaults to 'OTHER'
  source?: string;
  source_url?: string;
}

/**
 * GET /documents
 *
 * List registered legal documents with optional pagination and status filter.
 * Requires any authenticated user.
 */
export async function listDocuments(
  params: ListDocumentsParams = {},
): Promise<PaginatedDocuments> {
  const qs = new URLSearchParams();
  if (params.page) qs.set('page', String(params.page));
  if (params.page_size) qs.set('page_size', String(params.page_size));
  if (params.status) qs.set('status', params.status);

  const query = qs.toString() ? `?${qs.toString()}` : '';
  return apiClient.get<PaginatedDocuments>(`/documents${query}`);
}

/**
 * GET /documents/{id}
 *
 * Fetch full document details. Requires any authenticated user.
 */
export async function getDocument(id: string): Promise<DocumentDetail> {
  return apiClient.get<DocumentDetail>(`/documents/${id}`);
}

/**
 * GET /documents/{id}/chunks
 *
 * Paginated list of chunks for a document. Requires any authenticated user.
 */
export async function getDocumentChunks(
  id: string,
  page = 1,
  pageSize = 20,
): Promise<PaginatedChunks> {
  return apiClient.get<PaginatedChunks>(
    `/documents/${id}/chunks?page=${page}&page_size=${pageSize}`,
  );
}

/**
 * GET /documents/{id}/jobs
 *
 * Processing job history for a document. Requires any authenticated user.
 */
export async function getDocumentJobs(id: string): Promise<ProcessingJob[]> {
  return apiClient.get<ProcessingJob[]>(`/documents/${id}/jobs`);
}

/**
 * POST /documents/upload
 *
 * Upload a legal PDF and queue it for ingestion. ADMIN only.
 * Returns 202 Accepted immediately; processing runs in the background.
 *
 * @param file     The PDF File object
 * @param params   Document metadata
 */
export async function uploadDocument(
  file: File,
  params: UploadDocumentParams,
): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const qs = new URLSearchParams({ title: params.title });
  if (params.type) qs.set('type', params.type);
  if (params.source) qs.set('source', params.source);
  if (params.source_url) qs.set('source_url', params.source_url);

  // Upload uses multipart/form-data — do NOT set Content-Type
  return apiClient.upload<DocumentUploadResponse>(
    `/documents/upload?${qs.toString()}`,
    formData,
  );
}

/**
 * POST /documents/{id}/reprocess
 *
 * Re-run the full ingestion pipeline using the stored raw PDF. ADMIN only.
 * Returns 202 Accepted immediately.
 */
export async function reprocessDocument(id: string): Promise<ReprocessResponse> {
  return apiClient.post<ReprocessResponse>(`/documents/${id}/reprocess`);
}
