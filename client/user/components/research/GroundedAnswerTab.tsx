'use client';

import React from 'react';
import { ResearchResult, Citation } from '@/lib/types';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { CheckCircle2, AlertCircle, FileText, ExternalLink, Bookmark, Scale } from 'lucide-react';
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

  // Helper to render text with clickable citation markers [1], [2] etc.
  const renderTextWithCitations = (text: string) => {
    const parts = text.split(/(\[\d+\])/g);
    return parts.map((part, index) => {
      const match = part.match(/^\[(\d+)\]$/);
      if (match) {
        const citationIndex = parseInt(match[1], 10);
        const citation = result.citations.find(c => c.index === citationIndex);
        const isSelected = citation && citation.id === selectedCitationId;

        return (
          <sup key={index} className="mx-0.5 inline-block">
            <button
              onClick={() => citation && onSelectCitation(isSelected ? null : citation.id)}
              className={`citation-marker ${
                isSelected ? '!bg-[#1D4E8A] !text-white !border-[#132F52]' : ''
              }`}
              title={citation ? `${citation.caseName || citation.citation}` : `Citation ${citationIndex}`}
            >
              [{citationIndex}]
            </button>
          </sup>
        );
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
                  <p className="text-[#526176] italic font-serif leading-relaxed">"{selectedCitation.excerpt}"</p>
                </div>
              )}
              <div className="flex items-center justify-between text-[11px] font-mono text-[#718096] pt-1">
                <span>Location: {selectedCitation.sourceLocation}</span>
                <Badge variant="warning">
                  {selectedCitation.status}
                </Badge>
              </div>
              {selectedCitation.sourceUrl && (
                <a
                  href={selectedCitation.sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-[11px] text-[#1D4E8A] hover:underline font-mono"
                >
                  <ExternalLink className="h-3 w-3" /> Source URL
                </a>
              )}
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
            <Badge variant="warning">
              {result.citationStatus === 'ALL_VERIFIED' ? 'All Verified' : 'Unverified'}
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
                      <Badge variant="warning">
                        <AlertCircle className="h-2.5 w-2.5" />
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
