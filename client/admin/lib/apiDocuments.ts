/**
 * JURIS AI — ADMIN PORTAL DOCUMENTS API
 *
 * Typed wrappers for backend document endpoints.
 * Inline implementation for Turbopack (Next.js 16) compatibility.
 * Canonical source: client/shared/api/documents.ts
 *
 * Authentication:
 *   - Upload / Reprocess: ADMIN or SUPER_ADMIN (require_admin)
 *   - Read endpoints:     any authenticated user
 */

import { apiClient } from './apiClient';
import type {
  DocumentSummary,
  DocumentDetail,
  DocumentUploadResponse,
  ReprocessResponse,
  DocumentChunk,
  PaginatedChunks,
  ProcessingJob,
  PaginatedDocuments,
} from './apiTypes';

export interface ListDocumentsParams {
  page?: number;
  page_size?: number;
  status?: string;
}

export interface UploadDocumentParams {
  title: string;
  type?: string;
  source?: string;
  source_url?: string;
}

/**
 * GET /documents — List with pagination and status filter.
 */
export async function listDocuments(params: ListDocumentsParams = {}): Promise<PaginatedDocuments> {
  const qs = new URLSearchParams();
  if (params.page) qs.set('page', String(params.page));
  if (params.page_size) qs.set('page_size', String(params.page_size));
  if (params.status) qs.set('status', params.status);
  const query = qs.toString() ? `?${qs.toString()}` : '';
  return apiClient.get<PaginatedDocuments>(`/documents${query}`);
}

/**
 * GET /documents/{id} — Full document details.
 */
export async function getDocument(id: string): Promise<DocumentDetail> {
  return apiClient.get<DocumentDetail>(`/documents/${id}`);
}

/**
 * GET /documents/{id}/chunks — Paginated chunks.
 */
export async function getDocumentChunks(id: string, page = 1, pageSize = 20): Promise<PaginatedChunks> {
  return apiClient.get<PaginatedChunks>(`/documents/${id}/chunks?page=${page}&page_size=${pageSize}`);
}

/**
 * GET /documents/{id}/jobs — Processing job history.
 */
export async function getDocumentJobs(id: string): Promise<ProcessingJob[]> {
  return apiClient.get<ProcessingJob[]>(`/documents/${id}/jobs`);
}

/**
 * POST /documents/upload — Upload a legal PDF (ADMIN only).
 */
export async function uploadDocument(file: File, params: UploadDocumentParams): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const qs = new URLSearchParams({ title: params.title });
  if (params.type) qs.set('type', params.type);
  if (params.source) qs.set('source', params.source);
  if (params.source_url) qs.set('source_url', params.source_url);
  return apiClient.upload<DocumentUploadResponse>(`/documents/upload?${qs.toString()}`, formData);
}

/**
 * POST /documents/{id}/reprocess — Re-run ingestion (ADMIN only).
 */
export async function reprocessDocument(id: string): Promise<ReprocessResponse> {
  return apiClient.post<ReprocessResponse>(`/documents/${id}/reprocess`);
}
