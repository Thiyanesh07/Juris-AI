'use client';

import React from 'react';
import { ResearchResult, Citation } from '@/lib/types';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { CheckCircle2, AlertCircle, FileText, ExternalLink, Bookmark, Scale, FileX, Info } from 'lucide-react';
import { formatDate } from '@/lib/utils';

interface AnswerTabProps {
  result: ResearchResult;
  selectedCitationId: string | null;
  onSelectCitation: (id: string | null) => void;
  onSave: () => void;
  isSaved: boolean;
}

export const GroundedAnswerTab: React.FC<AnswerTabProps> = ({
  result,
  selectedCitationId,
  onSelectCitation,
  onSave,
  isSaved,
}) => {
  const selectedCitation = result.citations.find(c => c.id === selectedCitationId);

  // Helper to parse tokens from inside brackets, e.g. "1, 2, 3-5" -> [1, 2, 3, 4, 5]
  const parseCitationIndices = (rawInner: string): number[] => {
    const indices: number[] = [];
    const tokens = rawInner.split(/[,;]/);
    for (const token of tokens) {
      const trimmed = token.trim();
      if (!trimmed) continue;
      const rangeMatch = trimmed.match(/^(\d{1,2})\s*-\s*(\d{1,2})$/);
      if (rangeMatch) {
        const start = parseInt(rangeMatch[1], 10);
        const end = parseInt(rangeMatch[2], 10);
        if (start <= end && end - start <= 20) {
          for (let i = start; i <= end; i++) {
            if (!indices.includes(i)) indices.push(i);
          }
          continue;
        }
      }
      const numMatch = trimmed.match(/^(\d{1,2})$/);
      if (numMatch) {
        const val = parseInt(numMatch[1], 10);
        if (!indices.includes(val)) indices.push(val);
      }
    }
    return indices;
  };

  // Helper to render text with clickable citation markers, supporting grouped markers like [1, 2, 3] or [1-3]
  const renderTextWithCitations = (text: string) => {
    // Match bracketed citation sequences with 1-2 digit numbers, excluding 4-digit years like [1978]
    const groupRegex = /(\[(?:\s*\d{1,2}(?:\s*-\s*\d{1,2})?\s*[,;]?\s*)+\])/g;
    const parts = text.split(groupRegex);

    return parts.map((part, index) => {
      const match = part.match(/^\[((?:\s*\d{1,2}(?:\s*-\s*\d{1,2})?\s*[,;]?\s*)+)\]$/);
      if (match) {
        const indices = parseCitationIndices(match[1]);
        if (indices.length > 0) {
          return (
            <span key={index} className="inline-flex items-center gap-0.5 mx-0.5">
              {indices.map((citationIndex) => {
                const citation = result.citations.find(c => c.index === citationIndex);
                const isSelected = citation && citation.id === selectedCitationId;

                if (citation) {
                  return (
                    <sup key={citationIndex} className="inline-block">
                      <button
                        onClick={() => onSelectCitation(isSelected ? null : citation.id)}
                        className={`citation-marker ${
                          isSelected ? '!bg-[#1D4E8A] !text-white !border-[#132F52]' : ''
                        }`}
                        title={`${citation.caseName || citation.citation}`}
                      >
                        [{citationIndex}]
                      </button>
                    </sup>
                  );
                }

                // Unresolved citation reference (marker in text without matching source in evidence)
                return (
                  <sup key={citationIndex} className="inline-block">
                    <span
                      className="citation-marker !bg-amber-100 !text-amber-800 !border-amber-400 cursor-help"
                      title={`Unresolved reference [${citationIndex}]: source not found in retrieved evidence`}
                    >
                      [{citationIndex}]
                    </span>
                  </sup>
                );
              })}
            </span>
          );
        }
      }
      return <React.Fragment key={index}>{part}</React.Fragment>;
    });
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* MAIN ANSWER PANEL */}
      <div className="lg:col-span-8 space-y-6">
        {/* Answer Card — uses real backend answer field */}
        <div className="card p-6 border-l-4 border-l-[#1D4E8A]">
          <div className="flex items-center justify-between gap-4 mb-3">
            <div className="flex items-center gap-2">
              <Scale className="h-5 w-5 text-[#1D4E8A]" />
              <h2 className="text-xl font-serif text-[#17253A]">Legal Research Answer</h2>
            </div>
            <Button
              variant={isSaved ? 'secondary' : 'primary'}
              size="sm"
              onClick={onSave}
              disabled={isSaved}
              className="gap-1.5 shrink-0"
            >
              <Bookmark className="h-3.5 w-3.5" />
              {isSaved ? 'Saved to Workspace' : 'Save Research'}
            </Button>
          </div>

          {/* Non-blocking Notice Banner for Fallback & Partial Answers */}
          {result.notice && (
            <div
              className={`p-4 rounded-lg mb-4 text-xs font-mono border-l-4 ${
                result.answerStatus === 'general_fallback'
                  ? 'border-l-blue-600 bg-blue-50 text-[#17253A]'
                  : result.answerStatus === 'partial_answer'
                  ? 'border-l-amber-500 bg-amber-50 text-[#17253A]'
                  : 'border-l-slate-400 bg-slate-50 text-[#526176]'
              }`}
            >
              <div className="flex items-start gap-2.5">
                <Info
                  className={`h-4 w-4 shrink-0 mt-0.5 ${
                    result.answerStatus === 'general_fallback'
                      ? 'text-blue-600'
                      : result.answerStatus === 'partial_answer'
                      ? 'text-amber-600'
                      : 'text-slate-500'
                  }`}
                />
                <div className="space-y-1">
                  <p className="font-bold">
                    {result.answerStatus === 'general_fallback'
                      ? 'Corpus Coverage Notice (General Background)'
                      : result.answerStatus === 'partial_answer'
                      ? 'Partial Analysis Notice'
                      : 'Retrieval Notice'}
                  </p>
                  <p className="leading-relaxed">{result.notice}</p>
                  {result.missingAuthorities && result.missingAuthorities.length > 0 && (
                    <p className="text-[11px] text-[#526176]">
                      <span className="font-semibold">Unverified Authorities:</span>{' '}
                      {result.missingAuthorities.join(', ')}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Real backend answer rendered with citation markers */}
          {result.answer ? (
            <div className="legal-answer-body text-base leading-relaxed">
              {result.answer.split('\n\n').map((para, idx) => (
                <p key={idx} className="mb-3 last:mb-0">
                  {renderTextWithCitations(para)}
                </p>
              ))}
            </div>
          ) : (
            <p className="text-[#718096] italic text-sm font-mono">
              No answer was generated for this query.
            </p>
          )}
        </div>

        {/* Structured sections — only rendered if backend returned content */}
        {result.legalFramework ? (
          <div className="card p-6 space-y-3">
            <h3 className="text-lg text-[#17253A] font-serif border-b border-[#E2E8F0] pb-2">
              1. Constitutional &amp; Statutory Framework
            </h3>
            <div className="legal-answer-body">
              {result.legalFramework.split('\n\n').map((para, idx) => (
                <p key={idx}>{renderTextWithCitations(para)}</p>
              ))}
            </div>
          </div>
        ) : null}

        {result.judicialInterpretation ? (
          <div className="card p-6 space-y-3">
            <h3 className="text-lg text-[#17253A] font-serif border-b border-[#E2E8F0] pb-2">
              2. Judicial Interpretation &amp; Landmark Authorities
            </h3>
            <div className="legal-answer-body">
              {result.judicialInterpretation.split('\n\n').map((para, idx) => (
                <p key={idx}>{renderTextWithCitations(para)}</p>
              ))}
            </div>
          </div>
        ) : null}

        {result.developmentOverTime ? (
          <div className="card p-6 space-y-3">
            <h3 className="text-lg text-[#17253A] font-serif border-b border-[#E2E8F0] pb-2">
              3. Evolutionary Legal Analysis
            </h3>
            <div className="legal-answer-body">
              {result.developmentOverTime.split('\n\n').map((para, idx) => (
                <p key={idx}>{renderTextWithCitations(para)}</p>
              ))}
            </div>
          </div>
        ) : null}

        {result.conclusion ? (
          <div className="card p-6 bg-[#F8FAFC] space-y-3 border-[#CBD5E0]">
            <h3 className="text-lg text-[#17253A] font-serif border-b border-[#CBD5E0] pb-2">
              4. Synthesis &amp; Legal Conclusion
            </h3>
            <div className="legal-answer-body">
              <p>{renderTextWithCitations(result.conclusion)}</p>
            </div>
          </div>
        ) : null}

        {/* Disclaimer — always shown from backend */}
        <div className="p-4 rounded-xl bg-[#FFFBEB] border border-[#FDE68A] text-xs font-mono text-[#92660A] leading-relaxed">
          <span className="font-bold">RESEARCH DISCLAIMER: </span>
          {result.disclaimer}
        </div>
      </div>

      {/* CITATIONS & AUTHORITIES SIDE PANEL */}
      <div className="lg:col-span-4 space-y-4">
        {/* Selected Citation Inspector */}
        {selectedCitation ? (
          <div className="card p-5 border-[#1D4E8A] bg-[#F4F8FC] shadow-md animate-fade-in-up">
            <div className="flex items-center justify-between mb-3 border-b border-[#CBD5E0] pb-2">
              <div className="flex items-center gap-2">
                <span className="badge badge-primary font-mono text-xs">[{selectedCitation.index}]</span>
                <span className="text-xs font-mono font-bold text-[#1D4E8A]">Citation Details</span>
              </div>
              <button
                onClick={() => onSelectCitation(null)}
                className="text-xs text-[#718096] hover:text-[#17253A] underline font-mono cursor-pointer"
              >
                Clear
              </button>
            </div>
            <h4 className="text-sm font-bold text-[#17253A] font-sans mb-1">
              {selectedCitation.caseName || selectedCitation.sourceDocumentTitle}
            </h4>
            <p className="text-xs font-mono text-[#526176] mb-3">{selectedCitation.citation}</p>
            <div className="space-y-2 text-xs">
              <div className="bg-white p-3 rounded-lg border border-[#CBD5E0]">
                <p className="font-mono text-[10px] text-[#718096] uppercase font-bold mb-1">Source / Provision</p>
                <p className="text-[#17253A] font-medium">{selectedCitation.provision}</p>
              </div>
              {selectedCitation.excerpt && (
                <div className="bg-white p-3 rounded-lg border border-[#CBD5E0]">
                  <p className="font-mono text-[10px] text-[#718096] uppercase font-bold mb-1">Direct Excerpt</p>
                  <p className="text-[#526176] italic font-serif leading-relaxed">&ldquo;{selectedCitation.excerpt}&rdquo;</p>
                </div>
              )}
              <div className="flex items-center justify-between text-[11px] font-mono text-[#718096] pt-1">
                <span>Location: {selectedCitation.sourceLocation}</span>
                <Badge variant={selectedCitation.status === 'VERIFIED' ? 'success' : 'warning'}>
                  {selectedCitation.status}
                </Badge>
              </div>

              {/* Source Document & PDF Navigation */}
              {selectedCitation.pdfUrl ? (
                <a
                  href={`${selectedCitation.pdfUrl}#page=${selectedCitation.pageStart || 1}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-[11px] text-[#1D4E8A] hover:underline font-mono font-semibold"
                >
                  <FileText className="h-3.5 w-3.5" /> View Source PDF {selectedCitation.pageStart != null ? `(p. ${selectedCitation.pageStart})` : ''}
                </a>
              ) : null}

              {selectedCitation.sourceUrl && (selectedCitation.sourceUrl.startsWith('http://') || selectedCitation.sourceUrl.startsWith('https://')) ? (
                <a
                  href={selectedCitation.sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-[11px] text-[#1D4E8A] hover:underline font-mono"
                >
                  <ExternalLink className="h-3 w-3" /> External Source Link
                </a>
              ) : selectedCitation.sourceUrl ? (
                <div className="text-[11px] font-mono text-[#526176] bg-white p-2 rounded border border-[#CBD5E0]">
                  <span className="font-bold text-[#718096]">Reporter Ref: </span>
                  {selectedCitation.sourceUrl}
                </div>
              ) : !selectedCitation.pdfUrl ? (
                <div className="flex items-center gap-1.5 text-[11px] text-[#718096] font-mono italic">
                  <FileX className="h-3.5 w-3.5 text-[#A0AEC0]" /> Source document not available online
                </div>
              ) : null}
            </div>
          </div>
        ) : (
          <div className="p-4 rounded-xl bg-white border border-[#CBD5E0] text-center text-xs font-mono text-[#718096]">
            Click any <span className="citation-marker font-mono">[1]</span> marker in the text to inspect grounded authority details.
          </div>
        )}

        {/* Citations List */}
        <div className="card p-5 space-y-3">
          <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-2">
            <h3 className="text-sm font-bold text-[#17253A] font-sans flex items-center gap-1.5">
              <FileText className="h-4 w-4 text-[#1D4E8A]" />
              Cited Sources ({result.citations.length})
            </h3>
            <Badge variant={result.citationStatus === 'ALL_VERIFIED' ? 'success' : result.citationStatus === 'PARTIAL' ? 'warning' : 'default'}>
              {result.citationStatus === 'ALL_VERIFIED' ? 'All Verified' : result.citationStatus === 'PARTIAL' ? 'Partial' : 'Unverified'}
            </Badge>
          </div>

          {result.citations.length === 0 ? (
            <p className="text-xs font-mono text-[#718096] text-center py-4">
              No citations were returned for this query.
            </p>
          ) : (
            <div className="space-y-2 max-h-[550px] overflow-y-auto pr-1">
              {result.citations.map(cit => {
                const isSelected = cit.id === selectedCitationId;
                return (
                  <div
                    key={cit.id}
                    onClick={() => onSelectCitation(isSelected ? null : cit.id)}
                    className={`p-3 rounded-lg border transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-[#E8F0FD] border-[#1D4E8A] shadow-sm'
                        : 'bg-white border-[#E2E8F0] hover:border-[#CBD5E0]'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <span className="font-mono text-xs font-bold text-[#1D4E8A]">[{cit.index}]</span>
                      <Badge variant={cit.status === 'VERIFIED' ? 'success' : cit.status === 'NEEDS_REVIEW' ? 'warning' : 'default'}>
                        {cit.status === 'VERIFIED' ? (
                          <CheckCircle2 className="h-2.5 w-2.5" />
                        ) : (
                          <AlertCircle className="h-2.5 w-2.5" />
                        )}
                      </Badge>
                    </div>
                    <p className="text-xs font-semibold text-[#17253A] font-sans line-clamp-1">
                      {cit.caseName || cit.sourceDocumentTitle}
                    </p>
                    <p className="text-[11px] font-mono text-[#526176] truncate mt-0.5">{cit.citation}</p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
