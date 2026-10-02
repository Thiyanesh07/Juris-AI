/**
 * JURIS AI — ADMIN PORTAL EVALUATION API
 *
 * Typed wrappers for backend evaluation endpoints.
 * Inline implementation for Turbopack (Next.js 16) compatibility.
 * Canonical source: client/shared/api/evaluation.ts
 *
 * Authentication: ADMIN or SUPER_ADMIN only.
 */

import { apiClient } from './apiClient';
import type { EvaluationRun, PaginatedEvaluationRuns } from './apiTypes';

/**
 * GET /evaluation — Paginated list, ADMIN only.
 */
export async function listEvaluationRuns(page = 1, pageSize = 20): Promise<PaginatedEvaluationRuns> {
  return apiClient.get<PaginatedEvaluationRuns>(`/evaluation?page=${page}&page_size=${pageSize}`);
}

/**
 * GET /evaluation/{id} — Single run, ADMIN only.
 */
export async function getEvaluationRun(id: string): Promise<EvaluationRun> {
  return apiClient.get<EvaluationRun>(`/evaluation/${id}`);
}
