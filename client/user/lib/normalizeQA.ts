/**
 * JURIS AI — QA RESPONSE NORMALIZER (Phase 14 Real GraphRAG)
 *
 * Single normalization boundary:
 *   BackendQAAskResponse → ResearchResult
 *
 * Maps real grounded answer, citations, evidence fragments,
 * multi-hop graph nodes & edges, reasoning steps, and query analysis.
 */

import type {
  BackendQAAskResponse,
  BackendHybridEvidence,
  BackendQACitation,
} from './qaApi';

import type {
  ResearchResult,
  Citation,
  EvidenceItem,
  RetrievalMeta,
  GraphNode,
  GraphEdge,
  ReasoningStep,
  EntityType,
  TimelineEvent,
} from './types';

function normalizeEvidence(items: BackendHybridEvidence[]): EvidenceItem[] {
  return items.map((item) => {
    const hasDense = item.evidence_sources.includes('dense');
    const hasGraph = item.evidence_sources.includes('graph');
    const retrievalSource: EvidenceItem['retrievalSource'] =
      hasDense && hasGraph ? 'HYBRID' : hasGraph ? 'GRAPH' : 'VECTOR';

    let location = item.document_title;
    if (item.page_start != null) {
      location += `, p.${item.page_start}`;
      if (item.page_end != null && item.page_end !== item.page_start) {
        location += `–${item.page_end}`;
      }
    }

    return {
      id: `ev_${item.chunk_id}`,
      entityName: item.document_title,
      entityType: 'ACT' as const,
      sourceDocumentTitle: item.document_title,
      sourceDocumentType: 'ACT' as const,
      provision: item.citation_ref ?? `Chunk ${item.chunk_index}`,
      relevanceScore: item.hybrid_score,
      excerpt: item.text,
      retrievalSource,
      denseScore: item.dense_score,
      graphScore: item.graph_score,
      hybridScore: item.hybrid_score,
      rank: item.rank,
      chunkId: item.chunk_id,
      documentId: item.document_id,
      sourceUrl: item.source_url ?? undefined,
      hierarchy: item.hierarchy,
    };
  });
}

function normalizeCitations(citations: BackendQACitation[]): Citation[] {
  return citations.map((cit) => {
    let sourceLocation = cit.document_title;
    if (cit.page_start != null) {
      sourceLocation += `, p.${cit.page_start}`;
      if (cit.page_end != null && cit.page_end !== cit.page_start) {
        sourceLocation += `–${cit.page_end}`;
      }
    }

    const statusMap: Record<string, Citation['status']> = {
      VERIFIED: 'VERIFIED',
      PARTIALLY_VERIFIED: 'NEEDS_REVIEW',
      UNVERIFIED: 'UNVERIFIED',
      CONTRADICTED: 'UNVERIFIED',
    };
    const status = statusMap[cit.verification_status ?? 'UNVERIFIED'] ?? 'UNVERIFIED';

    return {
      id: `cit_${cit.chunk_id}_${cit.marker}`,
      index: cit.marker,
      caseName: undefined,
      court: undefined,
      year: undefined,
      citation: cit.citation_ref ?? cit.document_title,
      documentType: 'ACT' as const,
      provision: cit.citation_ref ?? `Chunk ${cit.chunk_index}`,
      sourceDocumentTitle: cit.document_title,
      sourceLocation,
      excerpt: '',
      status,
      sourceUrl: cit.source_url ?? undefined,
      chunkId: cit.chunk_id,
      documentId: cit.document_id,
      evidenceRank: cit.evidence_rank,
    };
  });
}

export function normalizeQAResponse(
  response: BackendQAAskResponse,
): ResearchResult {
  const citations = normalizeCitations(response.citations);
  const evidence = normalizeEvidence(response.evidence);

  let citationStatus: ResearchResult['citationStatus'] = 'UNVERIFIED';
  if (response.citation_validation) {
    const val = response.citation_validation;
    if (val.total > 0 && val.unverified === 0 && val.verified > 0) {
      citationStatus = 'ALL_VERIFIED';
    } else if (val.verified > 0 || val.partially_verified > 0) {
      citationStatus = 'PARTIAL';
    }
  } else if (citations.some((c) => c.status === 'VERIFIED')) {
    citationStatus = citations.every((c) => c.status === 'VERIFIED') ? 'ALL_VERIFIED' : 'PARTIAL';
  }

  const answer = response.answer ?? '';

  const retrieval: RetrievalMeta = {
    mode: response.retrieval.mode,
    fallback: response.retrieval.fallback ?? undefined,
    fallbackReason: response.retrieval.fallback_reason ?? undefined,
    warnings: response.retrieval.warnings,
    evidenceCount: response.retrieval.evidence_count,
    evidenceDroppedForContext: response.retrieval.evidence_dropped_for_context,
    timingsMs: {
      retrieval: response.timings_ms.retrieval,
      llm: response.timings_ms.llm,
    },
    provider: response.provider,
    model: response.model,
    llmCalled: response.llm_called,
  };

  // Phase 14: Real Knowledge Graph Nodes & Edges from Backend
  const graphNodes: GraphNode[] = (response.graph?.nodes || []).map((n) => ({
    id: n.id,
    label: n.label,
    type: (n.type || 'ACT') as EntityType | 'QUERY' | 'INTERPRETATION',
    x: n.x ?? 380,
    y: n.y ?? 200,
    isQuery: n.isQuery,
    isSeed: n.isSeed,
  }));

  const graphEdges: GraphEdge[] = (response.graph?.edges || []).map((e) => ({
    id: e.id,
    sourceId: e.sourceId,
    targetId: e.targetId,
    label: e.label,
  }));

  const graphAvailable = (response.graph?.available ?? false) && graphNodes.length > 0;

  // Phase 14: Real Structured Reasoning Steps from Backend
  const reasoningSteps: ReasoningStep[] = (response.reasoning_steps || []).map((s) => ({
    step: s.step,
    description: s.description,
    entityName: s.entityName,
    relationLabel: s.relationLabel,
    targetEntityName: s.targetEntityName,
  }));

  const reasoningAvailable = reasoningSteps.length > 0;

  // Phase 15: Real Temporal Timeline Events from Backend
  const timeline: TimelineEvent[] = (response.temporal?.timeline_events || []).map((te) => ({
    id: te.id,
    year: te.year,
    title: te.title,
    documentType: (te.document_type || 'ACT') as unknown as TimelineEvent['documentType'],
    description: te.description,
    importance: (te.importance || 'MEDIUM') as 'HIGH' | 'MEDIUM' | 'LOW',
  }));

  const timelineAvailable = timeline.length > 0;

  return {
    summary: answer,
    answer,
    citations,
    evidence,
    disclaimer: response.disclaimer,
    insufficientEvidence: response.insufficient_evidence,
    status: response.status,
    retrieval,
    sourcesCount: evidence.length,
    citationStatus,

    legalFramework: '',
    judicialInterpretation: '',
    developmentOverTime: '',
    reasoning: '',
    conclusion: '',

    graphNodes,
    graphEdges,
    graphAvailable,

    reasoningSteps,
    reasoningAvailable,

    timeline,
    timelineAvailable,
  };
}
