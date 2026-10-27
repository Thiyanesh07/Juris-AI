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

export function normalizeEvidence(items: BackendHybridEvidence[]): EvidenceItem[] {
  return (items || []).map((item) => {
    const hasDense = item.evidence_sources ? item.evidence_sources.includes('dense') : true;
    const hasGraph = item.evidence_sources ? item.evidence_sources.includes('graph') : false;
    const retrievalSource: EvidenceItem['retrievalSource'] =
      hasDense && hasGraph ? 'HYBRID' : hasGraph ? 'GRAPH' : 'VECTOR';

    let location = item.document_title;
    if (item.page_start != null) {
      location += `, p.${item.page_start}`;
      if (item.page_end != null && item.page_end !== item.page_start) {
        location += `–${item.page_end}`;
      }
    }

    const docTitle = item.document_title || '';
    const citRef = item.citation_ref || '';
    const isJudgment =
      docTitle.includes(' v. ') ||
      docTitle.includes(' v ') ||
      docTitle.includes(' Versus ') ||
      docTitle.toLowerCase().includes('union of india');
    const isConstitution = docTitle.toLowerCase().includes('constitution of india');
    const isAmendment = docTitle.toLowerCase().includes('amendment');
    const isRule = docTitle.toLowerCase().includes('rule') || docTitle.toLowerCase().includes('regulation');

    let entityType: EntityType = 'ACT';
    let docType: EvidenceItem['sourceDocumentType'] = 'ACT';

    if (isJudgment) {
      entityType = 'JUDGMENT';
      docType = 'JUDGMENT';
    } else if (isConstitution) {
      docType = 'CONSTITUTION';
      entityType = /article|art\./i.test(citRef) ? 'ARTICLE' : 'ACT';
    } else if (isAmendment) {
      entityType = 'AMENDMENT';
      docType = 'AMENDMENT';
    } else if (isRule) {
      entityType = 'RULE';
      docType = 'RULE';
    } else if (/section|sec\.|s\./i.test(citRef)) {
      entityType = 'SECTION';
      docType = 'ACT';
    }

    return {
      id: `ev_${item.chunk_id}`,
      entityName: item.document_title,
      entityType,
      sourceDocumentTitle: item.document_title,
      sourceDocumentType: docType,
      provision: item.citation_ref ?? `Chunk ${item.chunk_index}`,
      relevanceScore: item.hybrid_score,
      excerpt: item.text,
      retrievalSource,
      denseScore: item.dense_score,
      graphScore: item.graph_score,
      hybridScore: item.hybrid_score,
      scoreType: item.score_type ?? 'Calibrated Fusion Score',
      verificationStatus: item.verification_status ?? 'UNVERIFIED',
      pageStart: item.page_start,
      pageEnd: item.page_end,
      rank: item.rank,
      chunkId: item.chunk_id,
      documentId: item.document_id,
      sourceUrl: item.source_url ?? undefined,
      pdfUrl: item.pdf_url ?? (item.document_id ? `/api/v1/documents/${item.document_id}/pdf` : undefined),
      hierarchy: item.hierarchy,
    };
  });
}

export function normalizeCitations(
  citations: BackendQACitation[],
  evidenceItems: BackendHybridEvidence[] = []
): Citation[] {
  const evidenceByChunkId = new Map(evidenceItems.map(ev => [ev.chunk_id, ev]));

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

    const docTitle = cit.document_title || '';
    const isJudgment =
      docTitle.includes(' v. ') ||
      docTitle.includes(' v ') ||
      docTitle.includes(' Versus ') ||
      docTitle.toLowerCase().includes('union of india');

    const isConstitution = docTitle.toLowerCase().includes('constitution of india');
    const docType: Citation['documentType'] = isJudgment
      ? 'JUDGMENT'
      : isConstitution
        ? 'CONSTITUTION'
        : 'ACT';

    let displayProvision = cit.citation_ref ?? `Chunk ${cit.chunk_index}`;
    if (isJudgment && cit.citation_ref) {
      displayProvision = `${cit.citation_ref} (in ${docTitle})`;
    }

    const matchingEv = evidenceByChunkId.get(cit.chunk_id);
    const excerpt = matchingEv?.text || '';
    const pdfUrl = cit.pdf_url ?? matchingEv?.pdf_url ?? (cit.document_id ? `/api/v1/documents/${cit.document_id}/pdf` : undefined);

    return {
      id: `cit_${cit.chunk_id}_${cit.marker}`,
      index: cit.marker,
      caseName: isJudgment ? docTitle : undefined,
      court: isJudgment ? 'Supreme Court of India' : undefined,
      year: undefined,
      citation: cit.citation_ref ?? cit.document_title,
      documentType: docType,
      provision: displayProvision,
      sourceDocumentTitle: cit.document_title,
      sourceLocation,
      excerpt,
      status,
      sourceUrl: cit.source_url ?? undefined,
      pdfUrl: pdfUrl ?? undefined,
      pageStart: cit.page_start,
      pageEnd: cit.page_end,
      chunkId: cit.chunk_id,
      documentId: cit.document_id,
      evidenceRank: cit.evidence_rank,
    };
  });
}



import { layoutGraphNodes } from './graphLayout';

export function normalizeGraphNodes(rawNodes: any[]): GraphNode[] {
  const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  return (rawNodes || []).map((n, idx) => {
    const rawType = (n.type || '').toUpperCase();
    let entityType: EntityType | 'QUERY' | 'INTERPRETATION' = 'ACT';
    if (n.isQuery || rawType === 'QUERY') entityType = 'QUERY';
    else if (rawType === 'ARTICLE') entityType = 'ARTICLE';
    else if (rawType === 'SECTION') entityType = 'SECTION';
    else if (rawType === 'JUDGMENT') entityType = 'JUDGMENT';
    else if (rawType === 'AMENDMENT') entityType = 'AMENDMENT';
    else if (rawType === 'COURT') entityType = 'COURT';
    else if (rawType === 'RULE' || rawType === 'REGULATION') entityType = 'RULE';
    else if (rawType === 'PRINCIPLE' || rawType === 'DOCTRINE' || rawType === 'CONCEPT') entityType = 'PRINCIPLE';
    else if (rawType === 'ACT' || rawType === 'STATUTE' || rawType === 'CONSTITUTION') entityType = 'ACT';

    let displayLabel = String(n.label || '').trim();
    if (!displayLabel || UUID_REGEX.test(displayLabel)) {
      displayLabel = entityType === 'ARTICLE'
        ? 'Constitutional Article'
        : entityType === 'SECTION'
        ? 'Statutory Section'
        : entityType === 'JUDGMENT'
        ? 'Judicial Precedent'
        : entityType === 'AMENDMENT'
        ? 'Constitutional Amendment'
        : entityType === 'COURT'
        ? 'Judicial Authority'
        : 'Legal Authority';
    }

    const x = typeof n.x === 'number' && !isNaN(n.x) ? n.x : 500;
    const y = typeof n.y === 'number' && !isNaN(n.y) ? n.y : 300;

    return {
      id: String(n.id || `node_${idx}`),
      label: displayLabel,
      type: entityType,
      x,
      y,
      isQuery: Boolean(n.isQuery),
      isSeed: Boolean(n.isSeed),
    };
  });
}

export function normalizeGraphEdges(rawEdges: any[]): GraphEdge[] {
  return (rawEdges || []).map((e, idx) => ({
    id: String(e.id || `edge_${idx}`),
    sourceId: String(e.sourceId || e.source_id || e.source),
    targetId: String(e.targetId || e.target_id || e.target),
    label: String(e.label || e.type || e.relationship || 'CONNECTS_TO').toUpperCase(),
  }));
}

export function normalizeQAResponse(
  response: BackendQAAskResponse,
): ResearchResult {
  const citations = normalizeCitations(response.citations, response.evidence);
  const evidence = normalizeEvidence(response.evidence);

  let citationStatus: ResearchResult['citationStatus'] = 'UNVERIFIED';
  if (response.citation_validation) {
    const val = response.citation_validation;
    const verifiedCount = val.verified_count ?? val.verified ?? 0;
    const unverifiedCount = val.unverified_count ?? val.unverified ?? 0;
    const isGrounded = val.grounded ?? false;

    // Never treat zero verified citations as ALL_VERIFIED or fully grounded
    if (isGrounded && verifiedCount > 0 && unverifiedCount === 0) {
      citationStatus = 'ALL_VERIFIED';
    } else if (verifiedCount > 0) {
      citationStatus = 'PARTIAL';
    } else {
      citationStatus = 'UNVERIFIED';
    }
  } else if (citations.length > 0 && citations.some((c) => c.status === 'VERIFIED')) {
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

  // Phase 14 / Phase 5: Knowledge Graph with deterministic radial layout
  const rawGraphNodes = normalizeGraphNodes(response.graph?.nodes || []);
  const graphEdges = normalizeGraphEdges(response.graph?.edges || []);
  const graphNodes = layoutGraphNodes(rawGraphNodes, graphEdges);
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
    documentType: ((te as any).documentType || te.document_type || 'ACT') as unknown as TimelineEvent['documentType'],
    description: te.description,
    importance: (te.importance || 'MEDIUM') as 'HIGH' | 'MEDIUM' | 'LOW',
  }));

  const timelineAvailable = timeline.length > 0;

  // Determine user-friendly non-blocking banner state
  let infoBannerState: ResearchResult['infoBannerState'] = 'supported';
  if (response.answer_status === 'technical_timeout') {
    infoBannerState = 'timeout';
  } else if (response.answer_status === 'general_fallback') {
    infoBannerState = 'absent';
  } else if (response.answer_status === 'partial_answer') {
    infoBannerState = 'partial';
  } else if (response.answer_status === 'insufficient_evidence') {
    infoBannerState = evidence.length > 0 ? 'best_available' : 'absent';
  } else if (response.insufficient_evidence) {
    infoBannerState = evidence.length > 0 ? 'best_available' : 'absent';
  } else if (citationStatus === 'PARTIAL' || citationStatus === 'UNVERIFIED') {
    infoBannerState = evidence.length > 0 ? 'partial' : 'supported';
  } else {
    infoBannerState = 'supported';
  }

  return {
    summary: answer,
    answer,
    citations,
    evidence,
    disclaimer: response.disclaimer,
    insufficientEvidence: response.insufficient_evidence,
    status: response.status,
    answerStatus: response.answer_status ?? (response.insufficient_evidence ? 'insufficient_evidence' : 'full_answer'),
    missingAuthorities: response.missing_authorities ?? [],
    gapType: response.gap_type ?? 'none',
    notice: response.notice ?? null,
    infoBannerState,
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
