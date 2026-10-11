'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useDocumentStore } from '@/context/DocumentStoreContext';
import { Document, DocumentTypeCategory, DocumentStatus } from '@/lib/types';
import { ProcessingJob } from '@/lib/apiTypes';
import { ADMIN_ROUTES, ADMIN_DYNAMIC_ROUTES } from '@/constants/routes';
import { formatDate } from '@/lib/utils';
import { PageHeader } from '@/components/shared/PageHeader';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { EmptyState } from '@/components/shared/EmptyState';
import {
  ArrowLeft,
  Cpu,
  Archive,
  FileText,
  Building,
  Calendar,
  Layers,
  Activity,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  RotateCcw,
  RefreshCw,
} from 'lucide-react';

export default function DocumentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const docId = params?.id as string;

  const {
    getDocumentById,
    fetchDocumentDetail,
    archiveDocument,
    restoreDocument,
    reprocessDocument,
    fetchDocumentStages,
  } = useDocumentStore();

  const [doc, setDoc] = useState<Document | null>(null);
  const [stages, setStages] = useState<ProcessingJob[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [isArchiveDialogOpen, setIsArchiveDialogOpen] = useState(false);
  const [isRestoreDialogOpen, setIsRestoreDialogOpen] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [actionFeedback, setActionFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const loadDocumentData = useCallback(async () => {
    if (!docId) return;
    setIsLoading(true);
    setLoadError(null);
    try {
      const fetched = await fetchDocumentDetail(docId);
      if (fetched) {
        setDoc(fetched);
        const st = await fetchDocumentStages(docId);
        setStages(st);
      } else {
        setDoc(null);
      }
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to fetch document');
    } finally {
      setIsLoading(false);
    }
  }, [docId, fetchDocumentDetail, fetchDocumentStages]);

  useEffect(() => {
    loadDocumentData();
  }, [loadDocumentData]);

  const handleReprocess = async () => {
    if (!doc || isProcessing) return;
    setIsProcessing(true);
    setActionFeedback(null);
    try {
      const res = await reprocessDocument(doc.id);
      setActionFeedback({
        type: 'success',
        message: res.message || 'Pipeline reprocess initiated.',
      });
      await loadDocumentData();
    } catch (err) {
      setActionFeedback({
        type: 'error',
        message: err instanceof Error ? err.message : 'Reprocess request failed.',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleConfirmArchive = async () => {
    if (!doc) return;
    setIsProcessing(true);
    setActionFeedback(null);
    try {
      await archiveDocument(doc.id);
      setActionFeedback({
        type: 'success',
        message: 'Document archived successfully.',
      });
      setIsArchiveDialogOpen(false);
      await loadDocumentData();
    } catch (err) {
      setActionFeedback({
        type: 'error',
        message: err instanceof Error ? err.message : 'Archive failed.',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleConfirmRestore = async () => {
    if (!doc) return;
    setIsProcessing(true);
    setActionFeedback(null);
    try {
      const res = await restoreDocument(doc.id);
      setActionFeedback({
        type: 'success',
        message: res.message || `Document restored to ${res.status?.toUpperCase()}.`,
      });
      setIsRestoreDialogOpen(false);
      await loadDocumentData();
    } catch (err) {
      setActionFeedback({
        type: 'error',
        message: err instanceof Error ? err.message : 'Restore failed.',
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const getStatusBadge = (status: DocumentStatus) => {
    switch (status) {
      case 'READY':
        return <Badge variant="success">Ready for Reasoning</Badge>;
      case 'PROCESSING':
        return (
          <Badge variant="primary">
            <Activity className="h-3 w-3 mr-1 animate-spin" /> Ingestion Processing
          </Badge>
        );
      case 'FAILED':
        return <Badge variant="error">Ingestion Failed</Badge>;
      case 'ARCHIVED':
        return <Badge variant="outline">Archived / Disabled</Badge>;
      case 'UPLOADED':
      default:
        return <Badge variant="default">Uploaded</Badge>;
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6 max-w-4xl">
        <PageHeader
          title="Loading Document..."
          subtitle={`Fetching document ${docId} from backend`}
          actions={
            <Button variant="ghost" size="sm" onClick={() => router.push(ADMIN_ROUTES.DOCUMENTS)}>
              <ArrowLeft className="h-4 w-4 mr-1.5" />
              Back to Documents
            </Button>
          }
        />
        <div className="p-12 text-center rounded-xl border border-[#C9D4E1] bg-white">
          <Activity className="h-6 w-6 text-[#2563A8] animate-spin mx-auto mb-2" />
          <p className="font-mono text-xs text-[#526176]">Loading document metadata...</p>
        </div>
      </div>
    );
  }

  if (!doc) {
    return (
      <div className="space-y-6 max-w-3xl">
        <PageHeader
          title="Document Not Found"
          subtitle={`The document with ID "${docId}" could not be found in the database.`}
          actions={
            <Button variant="ghost" size="sm" onClick={() => router.push(ADMIN_ROUTES.DOCUMENTS)}>
              <ArrowLeft className="h-4 w-4 mr-1.5" />
              Back to Documents
            </Button>
          }
        />
        <EmptyState
          title="Document Record Not Found"
          description={loadError || 'The document ID does not exist in the PostgreSQL repository.'}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <PageHeader
        title={doc.title}
        subtitle={`Document ID: ${doc.id}`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => router.push(ADMIN_ROUTES.DOCUMENTS)}>
              <ArrowLeft className="h-4 w-4 mr-1.5" />
              Back to Documents
            </Button>
            <Button variant="secondary" size="sm" onClick={loadDocumentData} disabled={isLoading}>
              <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Link href={ADMIN_DYNAMIC_ROUTES.INGESTION_JOB_DETAIL(doc.id)}>
              <Button variant="secondary" size="sm">
                <Cpu className="h-3.5 w-3.5 mr-1.5" />
                Pipeline Stages
              </Button>
            </Link>
            {doc.status !== 'ARCHIVED' && (
              <Button
                variant="primary"
                size="sm"
                onClick={handleReprocess}
                disabled={isProcessing || doc.status === 'PROCESSING'}
              >
                <RotateCcw className={`h-3.5 w-3.5 mr-1.5 ${isProcessing ? 'animate-spin' : ''}`} />
                {doc.status === 'PROCESSING' ? 'Processing...' : 'Reprocess Ingestion'}
              </Button>
            )}
            {doc.status === 'ARCHIVED' ? (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setIsRestoreDialogOpen(true)}
                disabled={isProcessing}
              >
                <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
                Restore Document
              </Button>
            ) : (
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setIsArchiveDialogOpen(true)}
                disabled={isProcessing}
              >
                <Archive className="h-3.5 w-3.5 mr-1.5" />
                Archive Document
              </Button>
            )}
          </div>
        }
      />

      {/* Action Feedback */}
      {actionFeedback && (
        <div
          className={`p-4 rounded-xl text-xs font-mono flex items-center justify-between border ${
            actionFeedback.type === 'success'
              ? 'bg-[#D0EDDB] border-[#B2E2C3] text-[#1E6B45]'
              : 'bg-[#F5D9D9] border-[#E8B8B8] text-[#8B2E2E]'
          }`}
        >
          <div className="flex items-center gap-2">
            {actionFeedback.type === 'success' ? (
              <CheckCircle2 className="h-4 w-4 shrink-0" />
            ) : (
              <AlertCircle className="h-4 w-4 shrink-0" />
            )}
            <span>{actionFeedback.message}</span>
          </div>
          <button
            onClick={() => setActionFeedback(null)}
            className="underline font-semibold ml-4 cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Identity & Metadata Card */}
      <div className="p-6 rounded-2xl bg-white border border-[#C9D4E1] shadow-xs space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-[#D9E1EA] gap-4">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-[#2563A8] text-white shrink-0">
              <FileText className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h2 className="text-xl font-bold font-serif text-[#17253A]">{doc.title}</h2>
                <Badge variant="outline">{doc.documentType}</Badge>
              </div>
              <p className="text-xs font-mono text-[#526176] mt-1">{doc.fileName}</p>
            </div>
          </div>
          <div>{getStatusBadge(doc.status)}</div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 text-xs font-mono">
          <div className="p-4 rounded-xl bg-[#EFF3F7] border border-[#D9E1EA] space-y-1">
            <span className="text-[#718096] flex items-center gap-1.5">
              <Building className="h-3.5 w-3.5 text-[#2563A8]" /> Source & Authority
            </span>
            <p className="font-semibold text-[#17253A]">{doc.source || '—'}</p>
            {doc.authority && <p className="text-[11px] text-[#526176]">{doc.authority}</p>}
          </div>

          <div className="p-4 rounded-xl bg-[#EFF3F7] border border-[#D9E1EA] space-y-1">
            <span className="text-[#718096] flex items-center gap-1.5">
              <Layers className="h-3.5 w-3.5 text-[#2563A8]" /> Jurisdiction & Type
            </span>
            <p className="font-semibold text-[#17253A]">{doc.jurisdiction || 'Union of India'}</p>
            <p className="text-[11px] text-[#526176]">Category: {doc.documentType}</p>
          </div>

          <div className="p-4 rounded-xl bg-[#EFF3F7] border border-[#D9E1EA] space-y-1">
            <span className="text-[#718096] flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5 text-[#2563A8]" /> Dates & Tracking
            </span>
            <p className="font-semibold text-[#17253A]">Registered: {formatDate(doc.createdAt)}</p>
            <p className="text-[11px] text-[#526176]">Modified: {formatDate(doc.updatedAt)}</p>
          </div>
        </div>
      </div>

      {/* Ingestion Relationship & Stages Summary */}
      <div className="p-6 rounded-2xl bg-[#F5F7FA] border border-[#C9D4E1] shadow-xs space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-[#D9E1EA]">
          <div className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-[#2563A8]" />
            <h3 className="text-sm font-mono font-bold text-[#17253A] uppercase tracking-wider">
              Ingestion Pipeline Status
            </h3>
          </div>
          <Link href={ADMIN_DYNAMIC_ROUTES.INGESTION_JOB_DETAIL(doc.id)}>
            <Button variant="secondary" size="sm">
              View Detailed Stages
              <ExternalLink className="h-3.5 w-3.5 ml-1.5" />
            </Button>
          </Link>
        </div>

        {stages.length > 0 ? (
          <div className="p-4 rounded-xl bg-white border border-[#D9E1EA] space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between">
              <span className="font-bold text-[#17253A]">
                Stages Executed: {stages.filter((s) => s.status?.toLowerCase() === 'completed').length} / {stages.length}
              </span>
              <Badge variant={doc.status === 'READY' ? 'success' : doc.status === 'FAILED' ? 'error' : 'primary'}>
                Pipeline: {doc.status}
              </Badge>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-[#EFF3F7]">
              {stages.slice(0, 4).map((s) => (
                <div key={s.id} className="p-2 rounded bg-[#EFF3F7] border border-[#D9E1EA]">
                  <p className="font-semibold text-[11px] text-[#17253A] capitalize">{s.stage.replace(/_/g, ' ')}</p>
                  <p className="text-[10px] text-[#526176] uppercase">{s.status}</p>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="p-6 text-center text-xs font-mono text-[#718096] bg-white rounded-xl border border-[#D9E1EA]">
            No processing stages recorded yet for this document. Click "Reprocess Ingestion" above to execute the pipeline.
          </div>
        )}
      </div>

      {/* Confirm Archive Dialog */}
      {isArchiveDialogOpen && (
        <ConfirmDialog
          isOpen={true}
          onClose={() => setIsArchiveDialogOpen(false)}
          onConfirm={handleConfirmArchive}
          title="Archive Legal Document?"
          message={`Are you sure you want to archive "${doc.title}"? The document will be disabled and will not be retrieved during search.`}
          confirmText="Archive Document"
          variant="danger"
          isLoading={isProcessing}
        />
      )}

      {/* Confirm Restore Dialog */}
      {isRestoreDialogOpen && (
        <ConfirmDialog
          isOpen={true}
          onClose={() => setIsRestoreDialogOpen(false)}
          onConfirm={handleConfirmRestore}
          title="Restore Document?"
          message={`Are you sure you want to restore "${doc.title}"? The backend will verify if all required stages succeeded before marking it READY.`}
          confirmText="Restore Document"
          variant="primary"
          isLoading={isProcessing}
        />
      )}
    </div>
  );
}
