/**
 * JURIS AI — USER PORTAL QA API (Phase 14 Real GraphRAG)
 *
 * Typed wrappers for:
 *   POST /qa/ask         — hybrid GraphRAG retrieval + LLM answer
 *   POST /retrieval/hybrid — hybrid evidence only
 *
 * Security:
 *   credentials: 'include' is set in the shared apiClient.
 *   No token or API key is stored in the browser.
 */

import { apiFetch, ApiError } from './apiClient';

// ============================================================
// Backend response types — mirror of Pydantic schemas
// ============================================================

export interface BackendGraphEntityContext {
  id: string;
  label: string;
  name: string;
}

export interface BackendGraphContext {
  hops: number;
  seed_chunk_ids: string[];
  entities: BackendGraphEntityContext[];
}

export interface BackendHybridEvidence {
  rank: number;
  chunk_id: string;
  document_id: string;
  document_title: string;
  document_version_id: string | null;
  chunk_index: number;
  text: string;
  page_start: number | null;
  page_end: number | null;
  hierarchy: Record<string, unknown>;
  citation_ref: string | null;
  source_url: string | null;
  pdf_url?: string | null;
  dense_score: number;
  graph_score: number;
  hybrid_score: number;
  dense_rank: number | null;
  graph_rank: number | null;
  dense_matched: boolean;
  evidence_sources: Array<'dense' | 'graph'>;
  graph_context: BackendGraphContext | null;
  score_type?: string | null;
  verification_status?: 'VERIFIED' | 'PARTIALLY_VERIFIED' | 'UNVERIFIED' | 'CONTRADICTED' | null;
}

export interface BackendQACitation {
  marker: number;
  evidence_rank: number;
  chunk_id: string;
  document_id: string;
  document_title: string;
  document_version_id: string | null;
  chunk_index: number;
  citation_ref: string | null;
  page_start: number | null;
  page_end: number | null;
  source_url: string | null;
  pdf_url?: string | null;
  verification_status?: 'VERIFIED' | 'PARTIALLY_VERIFIED' | 'UNVERIFIED' | 'CONTRADICTED';
  confidence?: number;
}

export interface BackendQATimelineEvent {
  id: string;
  year: string;
  title: string;
  document_type: 'CONSTITUTION' | 'ACT' | 'JUDGMENT' | 'AMENDMENT' | 'ORDINANCE' | 'RULE' | 'REGULATION';
  description: string;
  importance: 'HIGH' | 'MEDIUM' | 'LOW';
  effective_date?: string | null;
  status?: string | null;
}

export interface BackendQATemporalMeta {
  detected: boolean;
  target_date?: string | null;
  target_year?: number | null;
  date_range?: Record<string, unknown> | null;
  temporal_operator?: string | null;
  referenced_amendment?: string | null;
  resolution_status: string;
  timeline_events: BackendQATimelineEvent[];
}

export interface BackendQACitationValidation {
  grounded: boolean;
  verified_count: number;
  unverified_count: number;
  warnings: string[];
  total?: number;
  verified?: number;
  partially_verified?: number;
  unverified?: number;
  contradicted?: number;
}

export interface BackendQARetrievalMeta {
  mode: 'hybrid' | 'vector_only' | 'graph_only';
  fallback: 'dense_only' | null;
  fallback_reason: 'neo4j_unavailable' | 'neo4j_timeout' | 'neo4j_query_failed' | null;
  warnings: string[];
  evidence_count: number;
  evidence_dropped_for_context: number;
}

export interface BackendQATimingsMs {
  retrieval: number;
  llm: number;
}

export interface BackendQAGraphNode {
  id: string;
  label: string;
  type: string;
  x?: number;
  y?: number;
  isQuery?: boolean;
  isSeed?: boolean;
}

export interface BackendQAGraphEdge {
  id: string;
  sourceId: string;
  targetId: string;
  label: string;
}

export interface BackendQAGraphData {
  nodes: BackendQAGraphNode[];
  edges: BackendQAGraphEdge[];
  available: boolean;
}

export interface BackendQAReasoningStep {
  step: number;
  description: string;
  entityName?: string;
  relationLabel?: string;
  targetEntityName?: string;
}

export interface BackendQAAskResponse {
  query: string;
  status: 'answered' | 'insufficient_evidence';
  answer: string | null;
  insufficient_evidence: boolean;
  citations: BackendQACitation[];
  evidence: BackendHybridEvidence[];
  graph?: BackendQAGraphData | null;
  reasoning_steps?: BackendQAReasoningStep[];
  query_analysis?: Record<string, unknown> | null;
  temporal?: BackendQATemporalMeta | null;
  citation_validation?: BackendQACitationValidation | null;
  retrieval: BackendQARetrievalMeta;
  provider: string;
  model: string;
  llm_called: boolean;
  timings_ms: BackendQATimingsMs;
  session_id?: string | null;
  disclaimer: string;
  answer_status?: 'full_answer' | 'partial_answer' | 'general_fallback' | 'insufficient_evidence' | 'technical_timeout' | null;
  missing_authorities?: string[];
  gap_type?: 'corpus_document' | 'graph_entities' | 'graph_relationships' | 'metadata' | 'none' | null;
  notice?: string | null;
}

export interface QAAskRequest {
  query: string;
  top_k?: number;
  mode?: 'COMPREHENSIVE' | 'CONSTITUTIONAL' | 'STATUTORY' | 'CASE_LAW';
  retrieval_strategy?: 'hybrid' | 'vector_only' | 'graph_only';
  graph_depth?: number;
  session_id?: string | null;
}

// ============================================================
// History API models (Phase 16)
// ============================================================

export interface BackendCitationSummary {
  id: string;
  citation: string;
  relevance: number | null;
  source_type: string | null;
  document_id: string | null;
  chunk_id?: string | null;
  marker?: number | null;
  page_start?: number | null;
  page_end?: number | null;
  citation_ref?: string | null;
  pdf_url?: string | null;
  document_title?: string | null;
  verification_status?: string | null;
  stable_id?: string | null;
}

export interface BackendAnswerSummary {
  id: string;
  answer: string;
  validation_status: string;
  created_at: string;
  mode?: string;
  citations: BackendCitationSummary[];
  evidence?: BackendHybridEvidence[];
  graph?: BackendQAGraphData | null;
  reasoning_steps?: BackendQAReasoningStep[];
  citation_validation?: BackendQACitationValidation | null;
}

export interface BackendQuerySummary {
  id: string;
  question: string;
  created_at: string;
  answers: BackendAnswerSummary[];
}

export interface BackendHistoryItem {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  mode?: string;
  queries: BackendQuerySummary[];
  saved: boolean;
}

export interface BackendPaginatedHistory {
  items: BackendHistoryItem[];
  total: number;
  page: number;
  page_size: number;
}

// ============================================================
// API functions
// ============================================================

export async function askLegalQuestion(
  request: QAAskRequest,
  signal?: AbortSignal,
): Promise<BackendQAAskResponse> {
  return apiFetch<BackendQAAskResponse>('/qa/ask', {
    method: 'POST',
    body: JSON.stringify(request),
    signal,
  });
}

export async function fetchResearchHistory(
  page = 1,
  pageSize = 20,
  signal?: AbortSignal,
): Promise<BackendPaginatedHistory> {
  return apiFetch<BackendPaginatedHistory>(`/research/history?page=${page}&page_size=${pageSize}`, {
    method: 'GET',
    signal,
  });
}

export async function fetchResearchHistorySession(
  sessionId: string,
  signal?: AbortSignal,
): Promise<BackendHistoryItem> {
  return apiFetch<BackendHistoryItem>(`/research/history/${sessionId}`, {
    method: 'GET',
    signal,
  });
}

export async function deleteResearchHistorySession(
  sessionId: string,
  signal?: AbortSignal,
): Promise<void> {
  return apiFetch<void>(`/research/history/${sessionId}`, {
    method: 'DELETE',
    signal,
  });
}

export { ApiError };
