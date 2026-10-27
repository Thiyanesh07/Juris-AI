'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { useResearchStore } from '@/context/ResearchStoreContext';
import { ResearchMode } from '@/lib/types';
import { PipelineStatusBanner } from '@/components/research/PipelineStatusBanner';
import { GroundedAnswerTab } from '@/components/research/GroundedAnswerTab';
import { EvidenceInspectorTab } from '@/components/research/EvidenceInspectorTab';
import { KnowledgeGraphTab } from '@/components/research/KnowledgeGraphTab';
import { LegalTimelineTab } from '@/components/research/LegalTimelineTab';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Dialog } from '@/components/ui/Dialog';
import {
  Search,
  Scale,
  BookOpen,
  GitFork,
  Clock,
  AlertTriangle,
  Layers,
  CheckCircle2,
  Bookmark,
  Share2,
  Download,
  RotateCcw,
  Loader2,
  Info,
} from 'lucide-react';

const MODE_OPTIONS: { id: ResearchMode; label: string; description: string }[] = [
  { id: 'COMPREHENSIVE', label: 'Comprehensive', description: 'Full GraphRAG search across Constitution, Statutes, Amendments & Judgments.' },
  { id: 'CONSTITUTIONAL', label: 'Constitutional Law', description: 'Focus on Articles, Fundamental Rights, Amendments & Bench rulings.' },
  { id: 'STATUTORY', label: 'Statutory Interpretation', description: 'Focus on BNS/IPC, Evidence Act, CrPC/BNSS & statutory amendments.' },
  { id: 'CASE_LAW', label: 'Case Law & Precedent', description: 'Focus on ratio decidendi, overruling authorities & binding precedents.' },
];

function ResearchWorkspaceContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get('q') || '';
  const fromId = searchParams.get('from');

  const {
    currentSession,
    pipelineStages,
    pipelineStatus,
    selectedCitationId,
    selectedNodeId,
    activeResultTab,
    startResearch,
    clearResearch,
    saveCurrentResearch,
    openHistorySession,
    setSelectedCitationId,
    setSelectedNodeId,
    setActiveResultTab,
  } = useResearchStore();

  const [queryInput, setQueryInput] = useState(initialQuery);
  const [selectedMode, setSelectedMode] = useState<ResearchMode>('COMPREHENSIVE');
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [exportCopied, setExportCopied] = useState(false);

  // Auto start if query passed in URL
  useEffect(() => {
    if (initialQuery && pipelineStatus === 'IDLE' && !currentSession) {
      startResearch(initialQuery, 'COMPREHENSIVE');
    }
  }, [initialQuery, pipelineStatus, currentSession, startResearch]);

  // Load from history if `from` param present
  useEffect(() => {
    if (fromId && pipelineStatus === 'IDLE') {
      openHistorySession(fromId);
    }
  }, [fromId, pipelineStatus, openHistorySession]);

  const isProcessing = pipelineStatus === 'ANALYZING' || pipelineStatus === 'RUNNING';

  const handleRunResearch = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!queryInput.trim() || isProcessing) return;
    const q = queryInput.trim();
    startResearch(q, selectedMode);
  };

  const handleReset = () => {
    setQueryInput('');
    clearResearch();
  };

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6 pb-20">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#E2E8F0] pb-4">
        <div>
          <h1 className="text-2xl text-[#17253A] flex items-center gap-2">
            <Scale className="h-6 w-6 text-[#1D4E8A]" />
            Legal Research Workspace
          </h1>
          <p className="text-xs font-mono text-[#526176] mt-0.5">
            Indian constitutional and statutory research
          </p>
        </div>

        {currentSession?.result && (
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setExportDialogOpen(true)}
              className="gap-1.5"
            >
              <Download className="h-3.5 w-3.5" /> Export Analysis
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleReset}
              className="gap-1.5 text-[#526176]"
            >
              <RotateCcw className="h-3.5 w-3.5" /> New Research
            </Button>
          </div>
        )}
      </div>

      {/* QUERY INPUT SECTION */}
      <div className="card p-6 space-y-4 shadow-sm border-[#CBD5E0]">
        <form onSubmit={handleRunResearch} className="space-y-4">
          <div className="relative">
            <textarea
              rows={3}
              value={queryInput}
              onChange={e => setQueryInput(e.target.value)}
              placeholder={
                currentSession?.result && pipelineStatus === 'COMPLETE'
                  ? "Ask a follow-up question in this session (e.g., 'What are the exceptions to this rule?')..."
                  : "Enter your legal research query (e.g., 'How has the interpretation of Article 21 evolved through Supreme Court decisions?')..."
              }
              className="research-textarea p-4 text-sm font-sans"
              disabled={isProcessing}
            />
          </div>

          {/* Mode Selection */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-mono font-bold text-[#526176] uppercase tracking-wider mr-1">
                Research Mode:
              </span>
              {MODE_OPTIONS.map(opt => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setSelectedMode(opt.id)}
                  disabled={isProcessing}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                    selectedMode === opt.id
                      ? 'bg-[#1D4E8A] text-white shadow-xs font-bold'
                      : 'bg-[#F0F4F8] text-[#526176] hover:bg-[#E8F0FD] hover:text-[#1D4E8A]'
                  }`}
                  title={opt.description}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            <Button
              type="submit"
              variant="primary"
              size="md"
              disabled={!queryInput.trim() || isProcessing}
              isLoading={isProcessing}
              className="gap-2 shrink-0 px-6 font-semibold"
            >
              <Search className="h-4 w-4" />
              {isProcessing
                ? 'Processing...'
                : currentSession?.result && pipelineStatus === 'COMPLETE'
                ? 'Ask Follow-up'
                : 'Execute Research'}
            </Button>
          </div>
        </form>
      </div>

      {/* PIPELINE STATUS BANNER */}
      {currentSession && pipelineStatus !== 'ERROR' && (
        <PipelineStatusBanner
          stages={pipelineStages}
          status={pipelineStatus}
          query={currentSession.query}
        />
      )}

      {/* ERROR STATE BANNER — shown only on real backend errors */}
      {currentSession && pipelineStatus === 'ERROR' && (
        <div className="card p-5 border-l-4 border-l-red-500 bg-red-50 space-y-2">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-red-600 shrink-0" />
            <div>
              <p className="text-sm font-bold text-red-700 font-sans">Research Request Failed</p>
              <p className="text-xs text-red-600 font-mono mt-0.5">
                {currentSession.errorMessage || 'An unexpected error occurred. Please try again.'}
              </p>
            </div>
          </div>
          <p className="text-xs text-[#526176] font-mono pl-8">
            No answer has been fabricated. Please correct the query or try again.
          </p>
        </div>
      )}

      {/* RESEARCH RESULTS AREA */}
      {currentSession?.result && pipelineStatus === 'COMPLETE' && (
        <div className="space-y-6 animate-fade-in-up">

          {/* Retrieval-First State Notice Banner */}
          {(() => {
            const res = currentSession.result;
            const state = res.infoBannerState;

            if (state === 'supported') {
              return (
                <div className="card p-3.5 border-l-4 border-l-emerald-600 bg-emerald-50/70 flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="h-4 w-4 text-emerald-700 shrink-0" />
                    <div>
                      <p className="text-xs font-bold text-emerald-900 font-sans">
                        Answer supported by retrieved sources
                      </p>
                      <p className="text-[11px] text-emerald-800 font-mono">
                        Directly synthesized from {res.citations.length} verified citation{res.citations.length === 1 ? '' : 's'} across {res.sourcesCount} retrieved source fragment{res.sourcesCount === 1 ? '' : 's'}.
                      </p>
                    </div>
                  </div>
                  <Badge variant="success">Corpus Grounded</Badge>
                </div>
              );
            }

            if (state === 'partial') {
              return (
                <div className="card p-3.5 border-l-4 border-l-amber-500 bg-amber-50/70 flex items-start justify-between gap-3">
                  <div className="flex items-start gap-2.5">
                    <Info className="h-4 w-4 text-amber-700 shrink-0 mt-0.5" />
                    <div>
                      <p className="text-xs font-bold text-amber-900 font-sans">
                        Partial answer — some authority could not be verified
                      </p>
                      <p className="text-[11px] text-amber-800 font-mono mt-0.5">
                        {res.notice || 'The available sources support only a portion of the query. Showing best available retrieved information alongside qualified claims.'}
                      </p>
                      {res.missingAuthorities && res.missingAuthorities.length > 0 && (
                        <p className="text-[11px] text-amber-700 font-mono mt-1">
                          <span className="font-semibold">Unverified:</span> {res.missingAuthorities.join(', ')}
                        </p>
                      )}
                    </div>
                  </div>
                  <Badge variant="warning">Partial Grounding</Badge>
                </div>
              );
            }

            if (state === 'absent') {
              return (
                <div className="card p-3.5 border-l-4 border-l-blue-600 bg-blue-50/70 flex items-start justify-between gap-3">
                  <div className="flex items-start gap-2.5">
                    <Info className="h-4 w-4 text-blue-700 shrink-0 mt-0.5" />
                    <div>
                      <p className="text-xs font-bold text-blue-900 font-sans">
                        Requested authority not found in the indexed corpus
                      </p>
                      <p className="text-[11px] text-blue-800 font-mono mt-0.5">
                        {res.notice || 'The requested authority is not in the currently indexed Juris AI corpus. The answer provides general background and is not verified against matching indexed sources.'}
                      </p>
                      <p className="text-[11px] text-[#526176] font-mono mt-1">
                        Absence from the current index does not prove the authority does not exist in law or elsewhere. Best available retrieved fragments are displayed below.
                      </p>
                    </div>
                  </div>
                  <Badge variant="default">General Background</Badge>
                </div>
              );
            }

            if (state === 'best_available') {
              return (
                <div className="card p-3.5 border-l-4 border-l-slate-500 bg-slate-50 flex items-start justify-between gap-3">
                  <div className="flex items-start gap-2.5">
                    <Layers className="h-4 w-4 text-slate-700 shrink-0 mt-0.5" />
                    <div>
                      <p className="text-xs font-bold text-slate-900 font-sans">
                        Showing the best available retrieved information
                      </p>
                      <p className="text-[11px] text-slate-700 font-mono mt-0.5">
                        {res.notice || 'Retrieved legal material is presented with calibrated ranking and source excerpts for researcher review.'}
                      </p>
                    </div>
                  </div>
                  <Badge variant="default">Best Available</Badge>
                </div>
              );
            }

            if (state === 'timeout') {
              return (
                <div className="card p-3.5 border-l-4 border-l-rose-500 bg-rose-50 flex items-start justify-between gap-3">
                  <div className="flex items-start gap-2.5">
                    <AlertTriangle className="h-4 w-4 text-rose-700 shrink-0 mt-0.5" />
                    <div>
                      <p className="text-xs font-bold text-rose-900 font-sans">
                        Research service timed out — please retry
                      </p>
                      <p className="text-[11px] text-rose-800 font-mono mt-0.5">
                        Downstream LLM or graph evaluation exceeded latency limits. Retrieved evidence before the timeout is preserved below.
                      </p>
                    </div>
                  </div>
                  <Badge variant="error">Timeout</Badge>
                </div>
              );
            }

            return null;
          })()}

          {/* Result Tab Navigation */}
          <div className="flex items-center justify-between border-b border-[#CBD5E0] pb-px">
            <div className="flex items-center gap-1">
              <button
                onClick={() => setActiveResultTab('answer')}
                className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-all cursor-pointer ${
                  activeResultTab === 'answer'
                    ? 'border-[#1D4E8A] text-[#1D4E8A] font-bold bg-white rounded-t-lg'
                    : 'border-transparent text-[#526176] hover:text-[#17253A]'
                }`}
              >
                <BookOpen className="h-4 w-4" />
                Grounded Answer
                <Badge variant="primary">{currentSession.result.citations.length} Citations</Badge>
              </button>

              <button
                onClick={() => setActiveResultTab('evidence')}
                className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-all cursor-pointer ${
                  activeResultTab === 'evidence'
                    ? 'border-[#1D4E8A] text-[#1D4E8A] font-bold bg-white rounded-t-lg'
                    : 'border-transparent text-[#526176] hover:text-[#17253A]'
                }`}
              >
                <Layers className="h-4 w-4" />
                Evidence Fragments
                <Badge variant="default">{currentSession.result.evidence.length}</Badge>
              </button>

              <button
                onClick={() => setActiveResultTab('graph')}
                className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-all cursor-pointer ${
                  activeResultTab === 'graph'
                    ? 'border-[#1D4E8A] text-[#1D4E8A] font-bold bg-white rounded-t-lg'
                    : 'border-transparent text-[#526176] hover:text-[#17253A]'
                }`}
              >
                <GitFork className="h-4 w-4" />
                Knowledge Graph
                <Badge variant="default">{currentSession.result.graphNodes.length} Nodes</Badge>
              </button>

              <button
                onClick={() => setActiveResultTab('timeline')}
                className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-all cursor-pointer ${
                  activeResultTab === 'timeline'
                    ? 'border-[#1D4E8A] text-[#1D4E8A] font-bold bg-white rounded-t-lg'
                    : 'border-transparent text-[#526176] hover:text-[#17253A]'
                }`}
              >
                <Clock className="h-4 w-4" />
                Legal Timeline
              </button>
            </div>
          </div>

          {/* TAB CONTENTS */}
          {activeResultTab === 'answer' && (
            <GroundedAnswerTab
              result={currentSession.result}
              selectedCitationId={selectedCitationId}
              onSelectCitation={setSelectedCitationId}
              onSave={() => saveCurrentResearch()}
              isSaved={currentSession.saved}
            />
          )}

          {activeResultTab === 'evidence' && (
            <EvidenceInspectorTab evidence={currentSession.result.evidence} />
          )}

          {activeResultTab === 'graph' && (
            <KnowledgeGraphTab
              nodes={currentSession.result.graphNodes}
              edges={currentSession.result.graphEdges}
              reasoningSteps={currentSession.result.reasoningSteps}
              graphAvailable={currentSession.result.graphAvailable}
              selectedNodeId={selectedNodeId}
              onSelectNode={setSelectedNodeId}
            />
          )}

          {activeResultTab === 'timeline' && (
            <LegalTimelineTab
              timeline={currentSession.result.timeline}
              timelineAvailable={currentSession.result.timelineAvailable}
            />
          )}
        </div>
      )}

      {/* EXPORT DIALOG */}
      <Dialog
        isOpen={exportDialogOpen}
        onClose={() => setExportDialogOpen(false)}
        title="Export Research Brief"
        description="Copy structured markdown brief grounded with citations."
        footer={
          <>
            <Button variant="secondary" onClick={() => setExportDialogOpen(false)}>
              Close
            </Button>
            <Button
              variant="primary"
              onClick={() => {
                setExportCopied(true);
                setTimeout(() => setExportCopied(false), 2000);
              }}
              className="gap-1.5"
            >
              {exportCopied ? <CheckCircle2 className="h-4 w-4" /> : <Share2 className="h-4 w-4" />}
              {exportCopied ? 'Copied Brief!' : 'Copy Brief to Clipboard'}
            </Button>
          </>
        }
      >
        <div className="bg-[#F8FAFC] p-4 rounded-xl border border-[#CBD5E0] font-mono text-xs text-[#17253A] space-y-2 max-h-60 overflow-y-auto">
          <p className="font-bold text-[#1D4E8A]"># JURIS AI LEGAL RESEARCH BRIEF</p>
          <p className="text-[#718096]">Query: {currentSession?.query}</p>
          <p className="text-[#718096]">Mode: {currentSession?.mode}</p>
          <p className="text-[#718096]">Date: {new Date().toLocaleDateString('en-IN')}</p>
          <hr className="border-[#E2E8F0]" />
          <p className="font-bold">## Answer</p>
          {/* Uses real answer from backend — not mock data */}
          <p>{currentSession?.result?.answer}</p>
          <p className="font-bold">## Cited Sources ({currentSession?.result?.citations.length})</p>
          {currentSession?.result?.citations.map(c => (
            <p key={c.id}>
              [{c.index}] {c.citation}{c.provision ? ` — ${c.provision}` : ''}
            </p>
          ))}
          <hr className="border-[#E2E8F0]" />
          <p className="text-[#718096] text-[10px]">DISCLAIMER: {currentSession?.result?.disclaimer}</p>
        </div>
      </Dialog>
    </div>
  );
}

export default function ResearchWorkspacePage() {
  return (
    <Suspense
      fallback={
        <div className="p-12 text-center text-xs font-mono text-[#718096] flex items-center justify-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin text-[#1D4E8A]" />
          Loading research workspace...
        </div>
      }
    >
      <ResearchWorkspaceContent />
    </Suspense>
  );
}
