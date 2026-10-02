'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useValidationStore } from '@/context/ValidationStoreContext';
import { ValidationCategory, ValidationStatus } from '@/lib/types';
import { ADMIN_ROUTES, ADMIN_DYNAMIC_ROUTES } from '@/constants/routes';
import { formatDate } from '@/lib/utils';
import { PageHeader } from '@/components/shared/PageHeader';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Textarea';
import { Dialog } from '@/components/ui/Dialog';
import { EmptyState } from '@/components/shared/EmptyState';
import {
  ChevronLeft,
  CheckCircle2,
  XCircle,
  FileText,
  GitFork,
  ExternalLink,
  Clock,
  User,
  Sparkles,
  AlertCircle,
  ShieldCheck,
  ArrowRight,
  BookOpen,
  Layers,
  Scale,
  MessageSquare,
  HelpCircle,
  History,
} from 'lucide-react';

export default function ValidationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;

  const { getItemById, approveItem, rejectItem } = useValidationStore();
  const item = getItemById(id);

  const [reviewerNote, setReviewerNote] = useState('');
  const [rejectError, setRejectError] = useState<string | null>(null);
  const [confirmModal, setConfirmModal] = useState<'APPROVE' | 'REJECT' | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);

  if (!item) {
    return (
      <div className="space-y-6">
        <Link
          href={ADMIN_ROUTES.VALIDATION}
          className="inline-flex items-center text-xs font-mono text-[#526176] hover:text-[#2563A8] transition-colors"
        >
          <ChevronLeft className="h-4 w-4 mr-1" /> Back to Validation Queue
        </Link>
        <EmptyState
          title="Validation Item Not Found"
          description={`No validation record exists with ID "${id}".`}
          action={
            <Button variant="primary" size="sm" onClick={() => router.push(ADMIN_ROUTES.VALIDATION)}>
              Return to Validation Queue
            </Button>
          }
        />
      </div>
    );
  }

  const handleApprove = () => {
    setIsSubmitting(true);
    setTimeout(() => {
      approveItem(item.id, reviewerNote);
      setIsSubmitting(false);
      setConfirmModal(null);
      setActionFeedback('Validation item successfully approved into the Trusted Knowledge Layer.');
    }, 300);
  };

  const handleReject = () => {
    if (!reviewerNote.trim()) {
      setRejectError('A reviewer note/reason is required for rejection quality logging.');
      return;
    }
    setIsSubmitting(true);
    setTimeout(() => {
      rejectItem(item.id, reviewerNote);
      setIsSubmitting(false);
      setConfirmModal(null);
      setRejectError(null);
      setActionFeedback('Validation item successfully rejected and flagged in quality logs.');
    }, 300);
  };

  const openRejectDialog = () => {
    if (!reviewerNote.trim()) {
      setRejectError('A reviewer note/reason is required for rejection quality logging.');
      return;
    }
    setRejectError(null);
    setConfirmModal('REJECT');
  };

  const getConfidenceBadge = (score: number) => {
    if (score >= 90) return <Badge variant="success">{score}% (High)</Badge>;
    if (score >= 70) return <Badge variant="warning">{score}% (Medium)</Badge>;
    return <Badge variant="error">{score}% (Low)</Badge>;
  };

  const getStatusBadge = (status: ValidationStatus) => {
    switch (status) {
      case 'APPROVED':
        return <Badge variant="success">Approved</Badge>;
      case 'REJECTED':
        return <Badge variant="error">Rejected</Badge>;
      case 'PENDING':
      default:
        return <Badge variant="warning">Pending Review</Badge>;
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Top Navigation */}
      <div className="flex items-center justify-between">
        <Link
          href={ADMIN_ROUTES.VALIDATION}
          className="inline-flex items-center text-xs font-mono text-[#526176] hover:text-[#2563A8] transition-colors"
        >
          <ChevronLeft className="h-4 w-4 mr-1" /> Back to Validation Queue
        </Link>
        <span className="text-xs font-mono text-[#718096]">ID: {item.id}</span>
      </div>

      {/* Action Feedback Banner */}
      {actionFeedback && (
        <div className="p-4 rounded-xl bg-[#D0EDDB] border border-[#A1DBB7] text-[#1E6B45] text-xs font-mono flex items-center justify-between animate-in fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <span>{actionFeedback}</span>
          </div>
          <button
            onClick={() => setActionFeedback(null)}
            className="text-[#1E6B45] hover:text-[#14472E] font-bold cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Page Header */}
      <PageHeader
        title={item.title}
        subtitle={`Category: ${item.itemType} • Extracted on ${formatDate(item.createdAt)}`}
        actions={
          <div className="flex items-center gap-2">
            <Badge variant="outline">{item.itemType}</Badge>
            {getStatusBadge(item.status)}
          </div>
        }
      />

      {/* Two Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT COLUMN: EVIDENCE & SOURCE CONTEXT */}
        <div className="lg:col-span-7 space-y-6">
          {/* Source Document Context Card */}
          <div className="p-5 rounded-xl bg-white border border-[#C9D4E1] shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-[#D9E1EA] pb-3">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-[#2563A8]" />
                <h3 className="text-sm font-bold text-[#17253A]">Source Document & Context</h3>
              </div>
              <Link
                href={ADMIN_DYNAMIC_ROUTES.DOCUMENT_DETAIL(item.sourceDocumentId)}
                className="inline-flex items-center text-xs font-mono text-[#2563A8] hover:underline"
              >
                View Source Document <ExternalLink className="h-3 w-3 ml-1" />
              </Link>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
              <div>
                <span className="text-[#718096] uppercase text-[10px] tracking-wider block">
                  Document Title
                </span>
                <span className="font-semibold text-[#17253A] mt-0.5 block">
                  {item.sourceDocumentTitle}
                </span>
              </div>
              <div>
                <span className="text-[#718096] uppercase text-[10px] tracking-wider block">
                  Specific Location
                </span>
                <span className="font-semibold text-[#17253A] mt-0.5 block">
                  {item.sourceLocation || 'General Document Section'}
                </span>
              </div>
            </div>

            {/* Evidence Excerpt Snippet */}
            <div className="space-y-1.5 pt-2">
              <span className="text-[11px] font-mono font-bold text-[#526176] uppercase tracking-wider flex items-center gap-1.5">
                <BookOpen className="h-3.5 w-3.5 text-[#2563A8]" />
                Extracted Source Evidence
              </span>
              <div className="p-3.5 rounded-lg bg-[#EFF3F7] border border-[#D9E1EA] text-xs font-mono text-[#17253A] leading-relaxed italic relative">
                "{item.sourceTextSnippet}"
              </div>
              <p className="text-[11px] font-mono text-[#718096]">
                Note: Mock evidence excerpt provided for human verification of NLP extraction accuracy.
              </p>
            </div>
          </div>

          {/* Structured Extraction Proposal Card */}
          <div className="p-5 rounded-xl bg-white border border-[#C9D4E1] shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-[#D9E1EA] pb-3">
              <div className="flex items-center gap-2">
                <Layers className="h-4 w-4 text-[#2563A8]" />
                <h3 className="text-sm font-bold text-[#17253A]">Proposed Extraction Structure</h3>
              </div>
              <Badge variant="outline">{item.itemType}</Badge>
            </div>

            {/* RELATIONSHIP STRUCTURE */}
            {item.itemType === 'RELATIONSHIP' && item.relationship && (
              <div className="space-y-3">
                <span className="text-xs font-mono text-[#526176]">
                  Proposed Legal Triple (Source → Relation → Target):
                </span>
                <div className="p-4 rounded-xl bg-[#EFF3F7] border border-[#C9D4E1] flex flex-col sm:flex-row items-center justify-between gap-3 text-xs font-mono text-center">
                  <div className="p-2.5 rounded-lg bg-white border border-[#C9D4E1] shadow-xs w-full sm:w-auto flex-1 font-bold text-[#17253A]">
                    {item.relationship.source}
                  </div>
                  <div className="flex items-center gap-1 text-[#2563A8] font-bold shrink-0 px-2 py-1 bg-[#D9E7F5] rounded">
                    <GitFork className="h-3.5 w-3.5" />
                    <span>{item.relationship.relation}</span>
                    <ArrowRight className="h-3.5 w-3.5 ml-1" />
                  </div>
                  <div className="p-2.5 rounded-lg bg-white border border-[#C9D4E1] shadow-xs w-full sm:w-auto flex-1 font-bold text-[#17253A]">
                    {item.relationship.target}
                  </div>
                </div>
              </div>
            )}

            {/* ENTITY STRUCTURE */}
            {item.itemType === 'ENTITY' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
                <div className="p-3 rounded-lg bg-[#EFF3F7] border border-[#D9E1EA]">
                  <span className="text-[#718096] text-[10px] uppercase block">Proposed Label</span>
                  <span className="font-bold text-[#17253A] mt-0.5 block">{item.proposedLabel}</span>
                </div>
                <div className="p-3 rounded-lg bg-[#EFF3F7] border border-[#D9E1EA]">
                  <span className="text-[#718096] text-[10px] uppercase block">Entity Node ID</span>
                  <span className="font-bold text-[#2563A8] mt-0.5 block">{item.entityId || item.id}</span>
                </div>
              </div>
            )}

            {/* CITATION STRUCTURE */}
            {item.itemType === 'CITATION' && (
              <div className="space-y-2 text-xs font-mono">
                <div className="p-3 rounded-lg bg-[#EFF3F7] border border-[#D9E1EA]">
                  <span className="text-[#718096] text-[10px] uppercase block">Legal Citation Reference</span>
                  <span className="font-bold text-[#17253A] mt-0.5 block">{item.proposedLabel}</span>
                </div>
                <div className="p-3 rounded-lg bg-[#EFF3F7] border border-[#D9E1EA]">
                  <span className="text-[#718096] text-[10px] uppercase block">Citing Authority</span>
                  <span className="font-medium text-[#17253A] mt-0.5 block">{item.sourceDocumentTitle}</span>
                </div>
              </div>
            )}

            {/* DOCUMENT_METADATA STRUCTURE */}
            {item.itemType === 'DOCUMENT_METADATA' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
                <div className="p-3 rounded-lg bg-[#EFF3F7] border border-[#D9E1EA]">
                  <span className="text-[#718096] text-[10px] uppercase block">Metadata Key</span>
                  <span className="font-bold text-[#17253A] mt-0.5 block">
                    {item.metadataKey || item.proposedLabel}
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-[#EFF3F7] border border-[#D9E1EA]">
                  <span className="text-[#718096] text-[10px] uppercase block">Extracted Value</span>
                  <span className="font-bold text-[#1E6B45] mt-0.5 block">
                    {item.metadataValue || item.proposedLabel}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Graph Context Card */}
          <div className="p-5 rounded-xl bg-white border border-[#C9D4E1] shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-[#D9E1EA] pb-3">
              <div className="flex items-center gap-2">
                <GitFork className="h-4 w-4 text-[#2563A8]" />
                <h3 className="text-sm font-bold text-[#17253A]">Knowledge Graph Context</h3>
              </div>
              <Link
                href={`${ADMIN_ROUTES.GRAPH}?search=${encodeURIComponent(item.proposedLabel)}`}
                className="inline-flex items-center text-xs font-mono text-[#2563A8] hover:underline"
              >
                View in Knowledge Graph <ExternalLink className="h-3 w-3 ml-1" />
              </Link>
            </div>

            <div className="p-4 rounded-xl bg-[#17253A] text-white space-y-3 font-mono text-xs">
              <div className="flex items-center justify-between text-[#A0AEC0] text-[11px]">
                <span>MOCK GRAPH NODE PREVIEW</span>
                <span>Neo4j Visualization Ready</span>
              </div>
              <div className="flex items-center justify-center py-4 border border-dashed border-[#526176] rounded-lg bg-[#0F172A]">
                <div className="flex items-center gap-3">
                  <div className="px-3 py-1.5 rounded-full bg-[#2563A8] text-white font-bold text-xs shadow-sm">
                    {item.proposedLabel.split(' ')[0] || item.title}
                  </div>
                  <ArrowRight className="h-4 w-4 text-[#A0AEC0]" />
                  <div className="px-3 py-1.5 rounded-full bg-[#3B82D0] text-white font-bold text-xs shadow-sm">
                    {item.itemType}
                  </div>
                </div>
              </div>
              <p className="text-[11px] text-[#A0AEC0]">
                Upon approval, this record is linked to existing entities in the graph database for multi-hop reasoning.
              </p>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: REVIEW PANEL & AUDIT HISTORY */}
        <div className="lg:col-span-5 space-y-6">
          {/* Quality Control Telemetry & Status Card */}
          <div className="p-5 rounded-xl bg-white border border-[#C9D4E1] shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-[#D9E1EA] pb-3">
              <h3 className="text-sm font-bold text-[#17253A]">Extraction Quality Telemetry</h3>
              <Sparkles className="h-4 w-4 text-[#2563A8]" />
            </div>

            {/* Model Confidence Rating */}
            <div className="space-y-2 text-xs font-mono">
              <div className="flex items-center justify-between">
                <span className="text-[#526176]">Extraction Model Confidence:</span>
                {getConfidenceBadge(item.confidenceScore)}
              </div>
              <div className="w-full h-2 rounded-full bg-[#EFF3F7] overflow-hidden border border-[#D9E1EA]">
                <div
                  className={`h-full transition-all duration-500 ${
                    item.confidenceScore >= 90
                      ? 'bg-[#1E6B45]'
                      : item.confidenceScore >= 70
                      ? 'bg-[#B7791F]'
                      : 'bg-[#8B2E2E]'
                  }`}
                  style={{ width: `${item.confidenceScore}%` }}
                />
              </div>
              <p className="text-[11px] text-[#718096] flex items-center gap-1">
                <HelpCircle className="h-3 w-3 shrink-0" />
                Confidence calculated by downstream legal parser model.
              </p>
            </div>

            {/* Workflow Lifecycle Visualizer */}
            <div className="p-3.5 rounded-lg bg-[#EFF3F7] border border-[#D9E1EA] space-y-2 text-xs font-mono">
              <span className="font-bold text-[#17253A] block text-[11px] uppercase tracking-wider">
                Lifecycle Stage:
              </span>
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="px-2 py-0.5 rounded bg-white border border-[#C9D4E1] text-[#718096]">
                  Extracted
                </span>
                <ArrowRight className="h-3 w-3 text-[#718096]" />
                <span className="px-2 py-0.5 rounded bg-[#FBF3D4] text-[#7A5A0F] font-bold">
                  Queue Review
                </span>
                <ArrowRight className="h-3 w-3 text-[#718096]" />
                <span
                  className={`px-2 py-0.5 rounded font-bold ${
                    item.status === 'APPROVED'
                      ? 'bg-[#D0EDDB] text-[#1E6B45]'
                      : item.status === 'REJECTED'
                      ? 'bg-[#FBE8E8] text-[#8B2E2E]'
                      : 'bg-white text-[#718096]'
                  }`}
                >
                  {item.status}
                </span>
              </div>
            </div>
          </div>

          {/* Review Action Card */}
          <div className="p-5 rounded-xl bg-white border border-[#C9D4E1] shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-[#D9E1EA] pb-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-[#2563A8]" />
                <h3 className="text-sm font-bold text-[#17253A]">Reviewer Decision Panel</h3>
              </div>
              {getStatusBadge(item.status)}
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
                  Reviewer Notes / Rationale{' '}
                  {item.status === 'PENDING' && <span className="text-[#718096]">(Required for Rejection)</span>}
                </label>
                <Textarea
                  value={reviewerNote}
                  onChange={(e) => {
                    setReviewerNote(e.target.value);
                    if (rejectError) setRejectError(null);
                  }}
                  placeholder="Enter audit notes, legal verification remarks, or correction directives..."
                  rows={3}
                  error={!!rejectError}
                />
                {rejectError && (
                  <p className="text-xs text-[#8B2E2E] font-mono mt-1 flex items-center gap-1">
                    <AlertCircle className="h-3.5 w-3.5" /> {rejectError}
                  </p>
                )}
              </div>

              <div className="flex items-center gap-3 pt-2">
                <Button
                  variant="primary"
                  className="flex-1 bg-[#1E6B45] hover:bg-[#154B30] text-white"
                  onClick={() => setConfirmModal('APPROVE')}
                >
                  <CheckCircle2 className="h-4 w-4 mr-1.5" /> Approve Item
                </Button>
                <Button variant="destructive" className="flex-1" onClick={openRejectDialog}>
                  <XCircle className="h-4 w-4 mr-1.5" /> Reject Item
                </Button>
              </div>

              {item.status !== 'PENDING' && (
                <div className="p-3 rounded-lg bg-[#EFF3F7] border border-[#D9E1EA] text-xs font-mono text-[#526176] text-center">
                  Item is currently <strong className="text-[#17253A]">{item.status}</strong>. Submitting actions above will update the quality state.
                </div>
              )}
            </div>
          </div>

          {/* Audit & Review History Timeline */}
          <div className="p-5 rounded-xl bg-white border border-[#C9D4E1] shadow-xs space-y-4">
            <div className="flex items-center gap-2 border-b border-[#D9E1EA] pb-3">
              <History className="h-4 w-4 text-[#2563A8]" />
              <h3 className="text-sm font-bold text-[#17253A]">Audit & Review History</h3>
            </div>

            <div className="space-y-4 text-xs font-mono">
              {/* Event 1: Extraction */}
              <div className="flex gap-3 relative before:absolute before:left-[11px] before:top-6 before:bottom-0 before:w-0.5 before:bg-[#D9E1EA]">
                <div className="h-6 w-6 rounded-full bg-[#EFF3F7] border border-[#C9D4E1] flex items-center justify-center text-[#526176] shrink-0 z-10">
                  <Sparkles className="h-3 w-3" />
                </div>
                <div className="space-y-0.5">
                  <span className="font-bold text-[#17253A] block">Extracted by Ingestion Engine</span>
                  <span className="text-[11px] text-[#718096] block">{formatDate(item.createdAt)}</span>
                  <p className="text-[11px] text-[#526176] mt-1">
                    Initial NLP candidate generated from {item.sourceDocumentTitle}.
                  </p>
                </div>
              </div>

              {/* Event 2: Human Review (if reviewed) */}
              {item.reviewedAt ? (
                <div className="flex gap-3">
                  <div
                    className={`h-6 w-6 rounded-full border flex items-center justify-center shrink-0 z-10 ${
                      item.status === 'APPROVED'
                        ? 'bg-[#D0EDDB] border-[#A1DBB7] text-[#1E6B45]'
                        : 'bg-[#FBE8E8] border-[#F4B8B8] text-[#8B2E2E]'
                    }`}
                  >
                    {item.status === 'APPROVED' ? (
                      <CheckCircle2 className="h-3 w-3" />
                    ) : (
                      <XCircle className="h-3 w-3" />
                    )}
                  </div>
                  <div className="space-y-0.5">
                    <span className="font-bold text-[#17253A] block">
                      {item.status} by {item.reviewedBy || 'Administrator'}
                    </span>
                    <span className="text-[11px] text-[#718096] block">{formatDate(item.reviewedAt)}</span>
                    {item.reviewNote && (
                      <div className="p-2.5 rounded bg-[#EFF3F7] border border-[#D9E1EA] text-[11px] text-[#17253A] mt-1">
                        "{item.reviewNote}"
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="flex gap-3">
                  <div className="h-6 w-6 rounded-full bg-[#FBF3D4] border border-[#F3E3A1] text-[#7A5A0F] flex items-center justify-center shrink-0 z-10">
                    <Clock className="h-3 w-3" />
                  </div>
                  <div className="space-y-0.5">
                    <span className="font-bold text-[#7A5A0F] block">Pending Human Verification</span>
                    <span className="text-[11px] text-[#718096] block">Awaiting administrator decision</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Confirmation Dialog */}
      {confirmModal && (
        <Dialog
          isOpen={true}
          onClose={() => setConfirmModal(null)}
          title={confirmModal === 'APPROVE' ? 'Approve Validation Item?' : 'Reject Validation Item?'}
          description={
            confirmModal === 'APPROVE'
              ? `Confirm approval for "${item.title}". Approved items enter the trusted knowledge layer.`
              : `Confirm rejection for "${item.title}". Rejected items will be excluded from Knowledge Graph indexing.`
          }
          footer={
            <>
              <Button variant="ghost" onClick={() => setConfirmModal(null)} disabled={isSubmitting}>
                Cancel
              </Button>
              {confirmModal === 'APPROVE' ? (
                <Button variant="primary" onClick={handleApprove} isLoading={isSubmitting} className="bg-[#1E6B45] hover:bg-[#154B30]">
                  Confirm Approval
                </Button>
              ) : (
                <Button variant="destructive" onClick={handleReject} isLoading={isSubmitting}>
                  Confirm Rejection
                </Button>
              )}
            </>
          }
        >
          <div className="space-y-3 font-mono text-xs">
            <div className="p-3 rounded-lg bg-[#EFF3F7] border border-[#D9E1EA]">
              <span className="text-[#718096] block text-[10px]">Item Title:</span>
              <span className="font-bold text-[#17253A] block">{item.title}</span>
              <span className="text-[#526176] text-[11px] block mt-1">
                Source Document: {item.sourceDocumentTitle}
              </span>
            </div>
            {reviewerNote && (
              <div className="p-3 rounded-lg bg-white border border-[#C9D4E1]">
                <span className="text-[#718096] block text-[10px]">Attached Reviewer Note:</span>
                <p className="text-[#17253A] italic font-sans">{reviewerNote}</p>
              </div>
            )}
          </div>
        </Dialog>
      )}
    </div>
  );
}
