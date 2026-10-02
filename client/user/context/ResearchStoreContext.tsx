'use client';

/**
 * JURIS AI — ResearchStoreContext (Phase 12 — Real Backend Integration)
 *
 * Replaces all mock/simulated pipeline timers with real POST /qa/ask calls.
 *
 * Flow:
 *   User submits query
 *       ↓
 *   startResearch() — sets ANALYZING state, fires POST /qa/ask
 *       ↓
 *   Backend: hybrid retrieval (FAISS + Neo4j) + LLM synthesis
 *       ↓
 *   Real QAAskResponse received
 *       ↓
 *   normalizeQAResponse() — single normalization boundary
 *       ↓
 *   ResearchResult → currentSession.result
 *       ↓
 *   UI tabs (GroundedAnswerTab, EvidenceInspectorTab, etc.)
 *
 * Pipeline stages:
 *   The backend executes as a single synchronous operation.
 *   We cannot observe individual backend stages.
 *   Stages map to: SUBMITTING → PROCESSING → COMPLETE
 *   Stage labels are semantically honest — no fabricated timings.
 *
 * Query modes:
 *   Backend does NOT accept a mode parameter.
 *   Mode is stored in ResearchSession for UI display only.
 *   All queries use the same POST /qa/ask endpoint.
 *
 * History / Saved Research:
 *   Local/in-memory only. No backend persistence exists (Phase 12).
 *   Pre-seeded mock history records are removed — history starts empty
 *   and accumulates from real queries within the session.
 *   Saved research is also local/in-memory.
 *
 * Security:
 *   apiClient uses credentials:'include' — session cookie only.
 *   No token or API key stored in browser.
 *   401 responses redirect to login.
 *
 * Cancellation:
 *   AbortController is used. If the user starts a new query while one
 *   is running, the previous request is aborted client-side.
 *   The backend does not support server-side cancellation; client-side
 *   abort prevents the response from being processed.
 */

import React, { createContext, useContext, useState, useCallback, useRef } from 'react';
import {
  ResearchSession,
  ResearchMode,
  ResearchStatus,
  PipelineStage,
  ResearchHistoryRecord,
  SavedResearch,
} from '@/lib/types';
import { askLegalQuestion, ApiError } from '@/lib/qaApi';
import { normalizeQAResponse } from '@/lib/normalizeQA';

// ============================================================
// Pipeline stages — semantically honest mapping to backend states
// ============================================================
// The backend executes as a single synchronous HTTP call.
// We map observable client-side states to stages:
//   Stage 1: Submitting query (client → server)
//   Stage 2: Retrieving evidence (backend: FAISS + Neo4j hybrid)
//   Stage 3: Generating answer (backend: LLM synthesis)
//   Stage 4: Validating citations (backend: citation grounding)
// Stage 5-8 are shown during backend processing as RUNNING/PENDING
// until the real response arrives.

const PIPELINE_STAGES: PipelineStage[] = [
  {
    id: 'submit',
    label: 'Submit Query',
    description: 'Sending authenticated request to Juris AI backend.',
    status: 'PENDING',
  },
  {
    id: 'retrieve',
    label: 'Retrieve Evidence',
    description: 'Backend running hybrid FAISS vector + Neo4j graph retrieval.',
    status: 'PENDING',
  },
  {
    id: 'fuse',
    label: 'Fuse Evidence',
    description: 'Backend scoring and ranking evidence with hybrid weights.',
    status: 'PENDING',
  },
  {
    id: 'generate',
    label: 'Generate Answer',
    description: 'LLM synthesising a grounded legal analysis from retrieved evidence.',
    status: 'PENDING',
  },
  {
    id: 'cite',
    label: 'Ground Citations',
    description: 'Backend mapping LLM citation markers to source chunks.',
    status: 'PENDING',
  },
  {
    id: 'validate',
    label: 'Validate Output',
    description: 'Backend verifying citation indices and output structure.',
    status: 'PENDING',
  },
  {
    id: 'normalize',
    label: 'Normalize Result',
    description: 'Mapping backend response to research result structure.',
    status: 'PENDING',
  },
  {
    id: 'render',
    label: 'Render Analysis',
    description: 'Populating research workspace with grounded answer and evidence.',
    status: 'PENDING',
  },
];

// Stage groups that map to backend processing phases:
// SUBMITTING = stage 0 running (submit)
// PROCESSING = stages 1-5 running sequentially (retrieve, fuse, generate, cite, validate)
// NORMALIZING = stage 6 running (normalize)
// COMPLETE = stage 7 running then complete (render)
const BACKEND_PROCESSING_STAGES = [1, 2, 3, 4, 5]; // shown while HTTP request is in flight

interface ResearchStoreContextType {
  currentSession: ResearchSession | null;
  pipelineStages: PipelineStage[];
  pipelineStatus: ResearchStatus;
  history: ResearchHistoryRecord[];
  savedResearch: SavedResearch[];
  selectedCitationId: string | null;
  selectedNodeId: string | null;
  activeResultTab: 'answer' | 'evidence' | 'graph' | 'timeline';
  startResearch: (query: string, mode: ResearchMode) => void;
  clearResearch: () => void;
  saveCurrentResearch: (title?: string) => void;
  removeSavedResearch: (id: string) => void;
  renameSavedResearch: (id: string, title: string) => void;
  openHistorySession: (id: string) => void;
  setSelectedCitationId: (id: string | null) => void;
  setSelectedNodeId: (id: string | null) => void;
  setActiveResultTab: (tab: 'answer' | 'evidence' | 'graph' | 'timeline') => void;
}

const ResearchStoreContext = createContext<ResearchStoreContextType | undefined>(undefined);

function freshStages(): PipelineStage[] {
  return PIPELINE_STAGES.map(s => ({ ...s, status: 'PENDING' as const }));
}

function stagesWithRunning(stages: PipelineStage[], runningIdx: number): PipelineStage[] {
  return stages.map((s, i) => ({
    ...s,
    status: i < runningIdx ? 'COMPLETE' : i === runningIdx ? 'RUNNING' : 'PENDING',
  }));
}

function allComplete(stages: PipelineStage[]): PipelineStage[] {
  return stages.map(s => ({ ...s, status: 'COMPLETE' as const }));
}

function stagesWithError(stages: PipelineStage[], failedIdx: number): PipelineStage[] {
  return stages.map((s, i) => ({
    ...s,
    status: i < failedIdx ? 'COMPLETE' : 'PENDING',
  }));
}

/** Convert ApiError to a user-friendly message */
function userMessageFromError(err: unknown): string {
  if (err instanceof ApiError) {
    switch (err.code) {
      case 'UNAUTHORIZED':
        return 'Your session has expired. Please sign in again.';
      case 'FORBIDDEN':
        return 'You do not have permission to run legal queries.';
      case 'VALIDATION_ERROR':
        return typeof err.detail === 'string'
          ? `Query validation failed: ${err.detail}`
          : `Query validation failed: ${(err.detail as string[]).join(', ')}`;
      case 'RATE_LIMITED':
        return 'Too many requests. Please wait a moment before submitting another query.';
      case 'SERVICE_UNAVAILABLE':
        return 'A backend service is temporarily unavailable (embedding, vector index, or PostgreSQL). Please try again shortly.';
      case 'SERVER_ERROR':
        return 'The server encountered an unexpected error. Please try again.';
      case 'NETWORK_ERROR':
        return 'Cannot reach the Juris AI backend. Check your network connection.';
      default:
        return err.userMessage;
    }
  }
  if (err instanceof Error && err.name === 'AbortError') {
    return 'Research was cancelled.';
  }
  return 'An unexpected error occurred. Please try again.';
}

export const ResearchStoreProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentSession, setCurrentSession] = useState<ResearchSession | null>(null);
  const [pipelineStages, setPipelineStages] = useState<PipelineStage[]>(freshStages());
  const [pipelineStatus, setPipelineStatus] = useState<ResearchStatus>('IDLE');

  // History: local/in-memory only — no backend persistence in Phase 12
  const [history, setHistory] = useState<ResearchHistoryRecord[]>([]);
  // Saved research: local/in-memory only — no backend persistence in Phase 12
  const [savedResearch, setSavedResearch] = useState<SavedResearch[]>([]);
  const [selectedCitationId, setSelectedCitationId] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [activeResultTab, setActiveResultTab] = useState<'answer' | 'evidence' | 'graph' | 'timeline'>('answer');

  // AbortController ref — cancel previous request if new one starts
  const abortControllerRef = useRef<AbortController | null>(null);

  const startResearch = useCallback(async (query: string, mode: ResearchMode) => {
    const trimmedQuery = query.trim();
    if (!trimmedQuery) return; // frontend validation — no empty queries

    // Cancel any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    // Reset state
    const stages = freshStages();
    setPipelineStages(stages);
    setPipelineStatus('ANALYZING');
    setSelectedCitationId(null);
    setSelectedNodeId(null);
    setActiveResultTab('answer');

    const sessionId = `sess_${Date.now()}`;
    const createdAt = new Date().toISOString();

    const newSession: ResearchSession = {
      id: sessionId,
      query: trimmedQuery,
      mode,
      createdAt,
      status: 'ANALYZING',
      saved: false,
    };
    setCurrentSession(newSession);

    // Stage 0 — SUBMITTING
    setPipelineStages(stagesWithRunning(freshStages(), 0));

    try {
      // Advance to stage 1 (retrieve) while waiting for backend
      // Small async tick to let React render the SUBMITTING state
      await new Promise<void>(resolve => setTimeout(resolve, 50));
      setPipelineStages(stagesWithRunning(freshStages(), 1));
      setPipelineStatus('RUNNING');

      // === REAL BACKEND CALL ===
      const response = await askLegalQuestion(
        { query: trimmedQuery, mode },
        controller.signal,
      );

      // Advance to normalize stage
      setPipelineStages(stagesWithRunning(freshStages(), 6));

      // Normalize response — single boundary
      const result = normalizeQAResponse(response);

      // Advance to render stage
      setPipelineStages(stagesWithRunning(freshStages(), 7));

      // Final — complete
      const completedAt = new Date().toISOString();
      setPipelineStages(allComplete(freshStages()));
      setPipelineStatus('COMPLETE');

      setCurrentSession({
        id: sessionId,
        query: trimmedQuery,
        mode,
        createdAt,
        completedAt,
        status: 'COMPLETE',
        result,
        saved: false,
      });

      // Add to local history
      const histRecord: ResearchHistoryRecord = {
        id: sessionId,
        query: trimmedQuery,
        mode,
        createdAt,
        sourcesCount: result.sourcesCount,
        citationStatus: result.citationStatus,
        saved: false,
      };
      setHistory(prev => [histRecord, ...prev]);

    } catch (err) {
      // Do not render a result on error
      const errorMessage = userMessageFromError(err);
      const isAbort = err instanceof Error && err.name === 'AbortError';

      if (isAbort) {
        // Silently reset — the user started a new query
        return;
      }

      // Mark the failed stage — we were in retrieval phase (stage 1-5)
      setPipelineStages(stagesWithError(freshStages(), 1));
      setPipelineStatus('ERROR');

      setCurrentSession({
        id: sessionId,
        query: trimmedQuery,
        mode,
        createdAt,
        status: 'ERROR',
        saved: false,
        errorMessage,
      });

      // If 401 — redirect to login (don't show error state)
      if (err instanceof ApiError && err.code === 'UNAUTHORIZED') {
        window.location.href = '/login';
      }
    }
  }, []);

  const clearResearch = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setCurrentSession(null);
    setPipelineStages(freshStages());
    setPipelineStatus('IDLE');
    setSelectedCitationId(null);
    setSelectedNodeId(null);
  }, []);

  const saveCurrentResearch = useCallback((title?: string) => {
    if (!currentSession?.result) return;
    const saved: SavedResearch = {
      id: `saved_${Date.now()}`,
      title: title || `Research: ${currentSession.query.substring(0, 50)}…`,
      query: currentSession.query,
      // Use the real answer as summary, truncated
      summary: (currentSession.result.answer || '').substring(0, 200) + '…',
      mode: currentSession.mode,
      savedAt: new Date().toISOString(),
      // Use real citation data — citation_ref or document_title
      authorities: currentSession.result.citations
        .slice(0, 3)
        .map(c => c.caseName || c.citation),
      tags: ['Research', currentSession.mode],
    };
    setSavedResearch(prev => [saved, ...prev]);
    setCurrentSession(prev => prev ? { ...prev, saved: true, savedTitle: saved.title } : prev);
    setHistory(prev => prev.map(h => h.id === currentSession.id ? { ...h, saved: true } : h));
  }, [currentSession]);

  const removeSavedResearch = useCallback((id: string) => {
    setSavedResearch(prev => prev.filter(s => s.id !== id));
  }, []);

  const renameSavedResearch = useCallback((id: string, title: string) => {
    setSavedResearch(prev => prev.map(s => s.id === id ? { ...s, title } : s));
  }, []);

  const openHistorySession = useCallback((id: string) => {
    // History sessions are in-memory only.
    // We can restore the session state from the history record but
    // we do NOT have the full ResearchResult stored in history.
    // Show a limited placeholder — the user must re-run the query for full results.
    const histRecord = history.find(h => h.id === id);
    if (!histRecord) return;

    // Only restore metadata — not a full result
    const session: ResearchSession = {
      id: histRecord.id,
      query: histRecord.query,
      mode: histRecord.mode,
      createdAt: histRecord.createdAt,
      status: 'IDLE',
      saved: histRecord.saved,
    };
    setCurrentSession(session);
    setPipelineStatus('IDLE');
    setPipelineStages(freshStages());
    setActiveResultTab('answer');
  }, [history]);

  return (
    <ResearchStoreContext.Provider
      value={{
        currentSession,
        pipelineStages,
        pipelineStatus,
        history,
        savedResearch,
        selectedCitationId,
        selectedNodeId,
        activeResultTab,
        startResearch,
        clearResearch,
        saveCurrentResearch,
        removeSavedResearch,
        renameSavedResearch,
        openHistorySession,
        setSelectedCitationId,
        setSelectedNodeId,
        setActiveResultTab,
      }}
    >
      {children}
    </ResearchStoreContext.Provider>
  );
};

export const useResearchStore = () => {
  const ctx = useContext(ResearchStoreContext);
  if (!ctx) throw new Error('useResearchStore must be used within ResearchStoreProvider');
  return ctx;
};
