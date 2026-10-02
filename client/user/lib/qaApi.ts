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
  dense_score: number;
  graph_score: number;
  hybrid_score: number;
  dense_rank: number | null;
  graph_rank: number | null;
  dense_matched: boolean;
  evidence_sources: Array<'dense' | 'graph'>;
  graph_context: BackendGraphContext | null;
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
  total: number;
  verified: number;
  partially_verified: number;
  unverified: number;
  contradicted: number;
  warnings: string[];
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
  disclaimer: string;
}

export interface QAAskRequest {
  query: string;
  top_k?: number;
  mode?: 'COMPREHENSIVE' | 'CONSTITUTIONAL' | 'STATUTORY' | 'CASE_LAW';
  retrieval_strategy?: 'hybrid' | 'vector_only' | 'graph_only';
  graph_depth?: number;
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

export { ApiError };
