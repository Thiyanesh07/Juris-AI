/**
 * JURIS AI — SHARED RESEARCH (QA) API FUNCTIONS
 *
 * Typed wrappers for backend QA and retrieval endpoints.
 * All endpoints verified in:
 *   server/api/app/api/routes/qa.py
 *   server/api/app/api/routes/retrieval.py
 *
 * Authentication: all endpoints require any authenticated user.
 *
 * Endpoint inventory:
 *   POST /qa/ask               → QAAskResponse — primary research endpoint
 *   POST /retrieval/search     → RetrievalResponse — dense vector search
 *   POST /retrieval/hybrid     → HybridRetrievalResponse — hybrid dense+graph
 *   POST /retrieval/rebuild    → { ... } — ADMIN only; rebuild FAISS index
 *
 * NOTE: These are the API CONTRACT LAYER for Phase 11.
 * The full research workflow integration (multi-hop reasoning, citation validation,
 * etc.) is deferred to later phases.
 */

import { apiClient } from './client';
import type {
  QAAskRequest,
  QAAskResponse,
  RetrievalRequest,
  RetrievalResponse,
  HybridRetrievalRequest,
  HybridRetrievalResponse,
} from './types';

/**
 * POST /qa/ask
 *
 * Submit a legal research question. The backend performs hybrid retrieval,
 * then calls the LLM to produce a grounded, cited answer.
 *
 * This is the primary research endpoint for the user portal.
 *
 * Request:  { query: string, top_k?: number }
 * Response: QAAskResponse (answer, citations, evidence, timings, etc.)
 *
 * Error codes:
 *   422 — query too long or top_k out of range
 *   503 — LLM provider or retrieval service unavailable
 *   504 — LLM provider timed out
 */
export async function submitLegalQuery(request: QAAskRequest): Promise<QAAskResponse> {
  return apiClient.post<QAAskResponse>('/qa/ask', request);
}

/**
 * POST /retrieval/search
 *
 * Dense vector search only (no graph). Returns ranked evidence chunks
 * without an LLM-synthesized answer.
 *
 * Request:  { query: string, top_k?: number }
 * Response: RetrievalResponse (query, results, score_type)
 */
export async function denseSearch(request: RetrievalRequest): Promise<RetrievalResponse> {
  return apiClient.post<RetrievalResponse>('/retrieval/search', request);
}

/**
 * POST /retrieval/hybrid
 *
 * Hybrid dense + graph search. Returns evidence with both vector and graph
 * scoring, plus graph context (entity neighborhoods).
 *
 * Request:  { query: string, top_k?: number }
 * Response: HybridRetrievalResponse
 */
export async function hybridSearch(request: HybridRetrievalRequest): Promise<HybridRetrievalResponse> {
  return apiClient.post<HybridRetrievalResponse>('/retrieval/hybrid', request);
}

/**
 * POST /retrieval/rebuild   [ADMIN only]
 *
 * Rebuild the FAISS dense vector index from all embeddings in PostgreSQL.
 * This is an admin maintenance operation.
 *
 * Returns a summary of the rebuild operation (untyped — backend returns
 * an ad-hoc dict). Throws ApiError on 403 if not admin, 503 if service down.
 */
export async function rebuildVectorIndex(): Promise<Record<string, unknown>> {
  return apiClient.post<Record<string, unknown>>('/retrieval/rebuild');
}
