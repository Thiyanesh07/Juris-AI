// ============================================================
// JURIS AI — USER PORTAL DOMAIN TYPES
// ============================================================

export type ResearchMode = 'COMPREHENSIVE' | 'STATUTORY' | 'CONSTITUTIONAL' | 'CASE_LAW';

/**
 * ResearchStatus — Phase 12 states correspond to real observable operations:
 *   IDLE        — no active session
 *   SUBMITTING  — request being sent to backend
 *   PROCESSING  — backend executing hybrid retrieval + LLM
 *   COMPLETE    — backend responded successfully
 *   ERROR       — backend returned an error or network failed
 *
 * NOTE: 'ANALYZING' and 'RUNNING' retained for backward-compat with pipeline
 * banner display but map to SUBMITTING/PROCESSING in the new flow.
 */
export type ResearchStatus = 'IDLE' | 'ANALYZING' | 'RUNNING' | 'COMPLETE' | 'ERROR';
export type CitationStatus = 'VERIFIED' | 'NEEDS_REVIEW' | 'UNVERIFIED';
export type RetrievalSource = 'VECTOR' | 'GRAPH' | 'HYBRID';
export type EntityType = 'ARTICLE' | 'SECTION' | 'ACT' | 'JUDGMENT' | 'AMENDMENT' | 'RULE' | 'COURT' | 'PRINCIPLE';
export type DocumentType = 'CONSTITUTION' | 'ACT' | 'JUDGMENT' | 'AMENDMENT' | 'ORDINANCE' | 'RULE' | 'REGULATION';

// Pipeline Stages
export interface PipelineStage {
  id: string;
  label: string;
  description: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETE';
  durationMs?: number;
}

// ============================================================
// Backend retrieval metadata (Phase 12 — real data)
// ============================================================
export interface RetrievalTimingsMs {
  retrieval: number;
  llm: number;
}

export interface RetrievalMeta {
  mode: 'hybrid' | 'vector_only' | 'graph_only';
  fallback?: 'dense_only';
  fallbackReason?: 'neo4j_unavailable' | 'neo4j_timeout' | 'neo4j_query_failed';
  warnings: string[];
  evidenceCount: number;
  evidenceDroppedForContext: number;
  timingsMs: RetrievalTimingsMs;
  provider: string;
  model: string;
  llmCalled: boolean;
}

// ============================================================
// Evidence Item
// Phase 12: mapped from BackendHybridEvidence
// Fields not available from backend are marked optional/undefined
// ============================================================
export interface EvidenceItem {
  id: string;
  // entityName: derived from document_title (backend has no separate entity name)
  entityName: string;
  // entityType: backend doesn't classify; 'ACT' used as neutral fallback
  entityType: EntityType;
  sourceDocumentTitle: string;
  sourceDocumentType: DocumentType;
  // provision: citation_ref if available, else "Chunk N"
  provision: string;
  // relevanceScore: mapped from hybrid_score
  relevanceScore: number;
  excerpt: string;
  retrievalSource: RetrievalSource;
  // year: NOT available from backend
  year?: number;

  // Phase 12 additions — real backend scores
  denseScore?: number;
  graphScore?: number;
  hybridScore?: number;
  rank?: number;
  chunkId?: string;
  documentId?: string;
  sourceUrl?: string;
  hierarchy?: Record<string, unknown>;
}

// ============================================================
// Citation
// Phase 12: mapped from BackendQACitation
// Fields not available from backend are marked optional/undefined
// ============================================================
export interface Citation {
  id: string;
  index: number;
  // caseName: NOT in backend schema
  caseName?: string;
  // court: NOT in backend schema
  court?: string;
  // year: NOT in backend schema
  year?: number;
  // citation: citation_ref if available, else document_title
  citation: string;
  documentType: DocumentType;
  // provision: citation_ref if available, else "Chunk N"
  provision: string;
  sourceDocumentTitle: string;
  sourceLocation: string;
  // excerpt: NOT in QACitation schema (text is in the evidence item)
  excerpt: string;
  // status: backend does not verify citations in legal sense → always UNVERIFIED
  status: CitationStatus;
  sourceUrl?: string;
  chunkId?: string;
  documentId?: string;
  evidenceRank?: number;
}

// ============================================================
// Reasoning Steps
// Phase 12: NOT available from backend — no structured reasoning metadata returned
// ============================================================
export interface ReasoningStep {
  step: number;
  description: string;
  entityName?: string;
  relationLabel?: string;
  targetEntityName?: string;
}

// ============================================================
// Graph types
// Phase 12: NOT available from backend — no graph HTTP endpoints exposed
// ============================================================
export interface GraphNode {
  id: string;
  label: string;
  type: EntityType | 'QUERY' | 'INTERPRETATION';
  x: number;
  y: number;
  isQuery?: boolean;
  isSeed?: boolean;
}

export interface GraphEdge {
  id: string;
  sourceId: string;
  targetId: string;
  label: string;
}

// ============================================================
// Timeline
// Phase 12: NOT available from backend — no timeline endpoint
// ============================================================
export interface TimelineEvent {
  id: string;
  year: string;
  title: string;
  documentType: DocumentType;
  description: string;
  importance: 'HIGH' | 'MEDIUM' | 'LOW';
}

// ============================================================
// ResearchResult
// Phase 12: extended to accurately reflect what the backend provides
// ============================================================
export interface ResearchResult {
  // === Real backend data ===

  /** The full LLM-generated answer string from QAAskResponse.answer */
  answer: string;

  /** Mapped to answer — used by GroundedAnswerTab.summary rendering */
  summary: string;

  citations: Citation[];
  evidence: EvidenceItem[];
  disclaimer: string;
  sourcesCount: number;
  citationStatus: 'ALL_VERIFIED' | 'PARTIAL' | 'UNVERIFIED';

  /** True when backend returned status: 'insufficient_evidence' */
  insufficientEvidence: boolean;
  status: 'answered' | 'insufficient_evidence';

  /** Retrieval and timing metadata from backend */
  retrieval?: RetrievalMeta;

  // === Structured sections (NOT from backend) ===
  // Backend returns a single answer string, not structured sections.
  // These are preserved empty for backward compatibility with GroundedAnswerTab.
  legalFramework: string;
  judicialInterpretation: string;
  developmentOverTime: string;
  reasoning: string;
  conclusion: string;

  // === Graph — NOT available from backend ===
  graphNodes: GraphNode[];
  graphEdges: GraphEdge[];
  /** False = no graph data returned by backend; tab shows unavailable state */
  graphAvailable: boolean;

  // === Reasoning steps — NOT available from backend ===
  reasoningSteps: ReasoningStep[];
  reasoningAvailable: boolean;

  // === Timeline — NOT available from backend ===
  timeline: TimelineEvent[];
  timelineAvailable: boolean;
}

// ============================================================
// ResearchSession
// ============================================================
export interface ResearchSession {
  id: string;
  query: string;
  mode: ResearchMode;
  createdAt: string;
  completedAt?: string;
  status: ResearchStatus;
  result?: ResearchResult;
  saved: boolean;
  savedTitle?: string;
  tags?: string[];
  /** Error message when status === 'ERROR' */
  errorMessage?: string;
}

// ============================================================
// History — local only, no backend persistence in Phase 12
// ============================================================
export interface ResearchHistoryRecord {
  id: string;
  query: string;
  mode: ResearchMode;
  createdAt: string;
  sourcesCount: number;
  citationStatus: 'ALL_VERIFIED' | 'PARTIAL' | 'UNVERIFIED';
  saved: boolean;
}

// ============================================================
// Saved Research — local only, no backend persistence in Phase 12
// ============================================================
export interface SavedResearch {
  id: string;
  title: string;
  query: string;
  summary: string;
  mode: ResearchMode;
  savedAt: string;
  authorities: string[];
  tags: string[];
}

// ============================================================
// User Profile
// ============================================================
export interface UserProfile {
  id: string;
  name: string;
  email: string;
  role: string;
  organization: string;
  preferredMode: ResearchMode;
  language: string;
  timezone: string;
  avatarUrl?: string;
  notificationsEnabled: boolean;
  joinedAt: string;
}
