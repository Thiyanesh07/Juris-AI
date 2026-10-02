/**
 * JURIS AI — SHARED EVALUATION API FUNCTIONS
 *
 * Typed wrappers for backend evaluation endpoints.
 * All endpoints verified in server/api/app/api/routes/evaluation.py.
 *
 * Authentication: ADMIN or SUPER_ADMIN only.
 *
 * Endpoint inventory:
 *   GET /evaluation             → PaginatedEvaluationRuns — ADMIN only
 *   GET /evaluation/{id}       → EvaluationRun — ADMIN only
 */

import { apiClient } from './client';
import type { EvaluationRun, PaginatedEvaluationRuns } from './types';

/**
 * GET /evaluation
 *
 * Paginated list of evaluation runs, newest first. ADMIN only.
 */
export async function listEvaluationRuns(
  page = 1,
  pageSize = 20,
): Promise<PaginatedEvaluationRuns> {
  return apiClient.get<PaginatedEvaluationRuns>(
    `/evaluation?page=${page}&page_size=${pageSize}`,
  );
}

/**
 * GET /evaluation/{id}
 *
 * Fetch a single evaluation run. ADMIN only.
 */
export async function getEvaluationRun(id: string): Promise<EvaluationRun> {
  return apiClient.get<EvaluationRun>(`/evaluation/${id}`);
}
