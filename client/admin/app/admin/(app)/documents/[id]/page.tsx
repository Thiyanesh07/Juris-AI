'use client';

import React, { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useDocumentStore } from '@/context/DocumentStoreContext';
import { DocumentTypeCategory, DocumentStatus } from '@/lib/types';
import { ADMIN_ROUTES, ADMIN_DYNAMIC_ROUTES } from '@/constants/routes';
import { formatDate, formatBytes } from '@/lib/utils';
import { PageHeader } from '@/components/shared/PageHeader';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { EmptyState } from '@/components/shared/EmptyState';
import {
  ArrowLeft,
  Edit3,
  Cpu,
  Archive,
  Save,
  X,
  FileText,
  Building,
  Calendar,
  Layers,
  Activity,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
} from 'lucide-react';

export default function DocumentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const docId = params?.id as string;

  const { getDocumentById, updateDocument, archiveDocument, startIngestion, getJobById } = useDocumentStore();
  const doc = getDocumentById(docId);
  const latestJob = doc?.latestJobId ? getJobById(doc.latestJobId) : undefined;

  const [isEditing, setIsEditing] = useState(false);
  const [title, setTitle] = useState(doc?.title || '');
  const [source, setSource] = useState(doc?.source || '');
  const [authority, setAuthority] = useState(doc?.authority || '');
  const [jurisdiction, setJurisdiction] = useState(doc?.jurisdiction || '');
  const [version, setVersion] = useState(doc?.version || '');
  const [documentType, setDocumentType] = useState<DocumentTypeCategory>(doc?.documentType || 'Act');

  const [isArchiveDialogOpen, setIsArchiveDialogOpen] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  if (!doc) {
    return (
      <div className="space-y-6 max-w-3xl">
        <PageHeader
          title="Document Not Found"
          subtitle="The requested document record could not be found."
          actions={
            <Button variant="ghost" size="sm" onClick={() => router.push(ADMIN_ROUTES.DOCUMENTS)}>
              <ArrowLeft className="h-4 w-4 mr-1.5" />
              Back to Documents
            </Button>
          }
        />
        <EmptyState title="Document Record Not Found" description="The document ID does not exist in local session store." />
      </div>
    );
  }

  const handleSaveEdit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsProcessing(true);
    setTimeout(() => {
      updateDocument(doc.id, {
        title,
        source,
        authority,
        jurisdiction,
        version,
        documentType,
      });
      setIsProcessing(false);
      setIsEditing(false);
    }, 300);
  };

  const handleStartIngestion = () => {
    startIngestion(doc.id);
  };

  const handleConfirmArchive = () => {
    setIsProcessing(true);
    setTimeout(() => {
      archiveDocument(doc.id);
      setIsProcessing(false);
      setIsArchiveDialogOpen(false);
    }, 300);
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
        return <Badge variant="error">Parsing Failed</Badge>;
      case 'ARCHIVED':
        return <Badge variant="outline">Archived</Badge>;
      case 'UPLOADED':
      default:
        return <Badge variant="default">Uploaded</Badge>;
    }
  };

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
            <Button variant="secondary" size="sm" onClick={() => setIsEditing(!isEditing)}>
              <Edit3 className="h-3.5 w-3.5 mr-1.5" />
              {isEditing ? 'Cancel Edit' : 'Edit Metadata'}
            </Button>
            {doc.status !== 'PROCESSING' && doc.status !== 'ARCHIVED' && (
              <Button variant="primary" size="sm" onClick={handleStartIngestion}>
                <Cpu className="h-3.5 w-3.5 mr-1.5" />
                Start Ingestion
              </Button>
            )}
            {doc.status !== 'ARCHIVED' && (
              <Button variant="destructive" size="sm" onClick={() => setIsArchiveDialogOpen(true)}>
                <Archive className="h-3.5 w-3.5 mr-1.5" />
                Archive
              </Button>
            )}
          </div>
        }
      />

      {/* Identity & Ingestion Status Section */}
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

        {/* View / Edit Mode */}
        {isEditing ? (
          <form onSubmit={handleSaveEdit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
                  Document Title
                </label>
                <Input value={title} onChange={(e) => setTitle(e.target.value)} required />
              </div>
              <div>
                <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
                  Document Type
                </label>
                <Select
                  value={documentType}
                  onChange={(e) => setDocumentType(e.target.value as DocumentTypeCategory)}
                >
                  <option value="Constitution">Constitution</option>
                  <option value="Act">Act</option>
                  <option value="Amendment Act">Amendment Act</option>
                  <option value="Rule">Rule</option>
                  <option value="Regulation">Regulation</option>
                  <option value="Judgment">Judgment</option>
                  <option value="Notification">Notification</option>
                  <option value="Other">Other</option>
                </Select>
              </div>
              <div>
                <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
                  Source
                </label>
                <Input value={source} onChange={(e) => setSource(e.target.value)} />
              </div>
              <div>
                <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
                  Authority
                </label>
                <Input value={authority} onChange={(e) => setAuthority(e.target.value)} />
              </div>
              <div>
                <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
                  Jurisdiction
                </label>
                <Input value={jurisdiction} onChange={(e) => setJurisdiction(e.target.value)} />
              </div>
              <div>
                <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
                  Version
                </label>
                <Input value={version} onChange={(e) => setVersion(e.target.value)} />
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#D9E1EA]">
              <Button type="button" variant="ghost" onClick={() => setIsEditing(false)}>
                <X className="h-4 w-4 mr-1.5" /> Cancel
              </Button>
              <Button type="submit" variant="primary" isLoading={isProcessing}>
                <Save className="h-4 w-4 mr-1.5" /> Save Changes
              </Button>
            </div>
          </form>
        ) : (
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
                <Layers className="h-3.5 w-3.5 text-[#2563A8]" /> Jurisdiction & Version
              </span>
              <p className="font-semibold text-[#17253A]">{doc.jurisdiction || 'Union of India'}</p>
              {doc.version && <p className="text-[11px] text-[#526176]">{doc.version}</p>}
            </div>

            <div className="p-4 rounded-xl bg-[#EFF3F7] border border-[#D9E1EA] space-y-1">
              <span className="text-[#718096] flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5 text-[#2563A8]" /> Dates & File Metadata
              </span>
              <p className="font-semibold text-[#17253A]">Uploaded: {formatDate(doc.createdAt)}</p>
              <p className="text-[11px] text-[#526176]">
                Size: {formatBytes(doc.fileSizeBytes)} &bull; {doc.pageCount ? `${doc.pageCount} pages` : 'PDF'}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Ingestion Relationship Card */}
      <div className="p-6 rounded-2xl bg-[#F5F7FA] border border-[#C9D4E1] shadow-xs space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-[#D9E1EA]">
          <div className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-[#2563A8]" />
            <h3 className="text-sm font-mono font-bold text-[#17253A] uppercase tracking-wider">
              Ingestion Job Link
            </h3>
          </div>
          {latestJob && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => router.push(ADMIN_DYNAMIC_ROUTES.INGESTION_JOB_DETAIL(latestJob.id))}
            >
              View Ingestion Job Details
              <ExternalLink className="h-3.5 w-3.5 ml-1.5" />
            </Button>
          )}
        </div>

        {latestJob ? (
          <div className="p-4 rounded-xl bg-white border border-[#D9E1EA] space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between">
              <span className="font-bold text-[#17253A]">Job ID: {latestJob.id}</span>
              <Badge variant={latestJob.status === 'COMPLETED' ? 'success' : latestJob.status === 'FAILED' ? 'error' : 'primary'}>
                {latestJob.status}
              </Badge>
            </div>

            <div className="w-full bg-[#C9D4E1] h-2 rounded-full overflow-hidden">
              <div
                className="bg-[#2563A8] h-full transition-all duration-300"
                style={{ width: `${latestJob.progressPercentage}%` }}
              />
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-2 border-t border-[#EFF3F7] text-[11px] text-[#526176]">
              <div>Worker: {latestJob.workerNode || 'worker-01'}</div>
              <div>Progress: {latestJob.progressPercentage}%</div>
              <div>Chunks: {latestJob.chunksCount || '—'}</div>
              <div>Entities: {latestJob.entitiesExtractedCount || '—'}</div>
            </div>

            {latestJob.errorMessage && (
              <div className="p-2.5 rounded bg-[#F5D9D9] text-[#8B2E2E] text-xs flex items-center gap-2 border border-[#E8B8B8]">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{latestJob.errorMessage}</span>
              </div>
            )}
          </div>
        ) : (
          <div className="p-6 text-center text-xs font-mono text-[#718096] bg-white rounded-xl border border-[#D9E1EA]">
            No ingestion job initiated yet for this document. Click "Start Ingestion" above to queue processing.
          </div>
        )}
      </div>

      {/* Confirm Archive Dialog */}
      {isArchiveDialogOpen && (
        <ConfirmDialog
          isOpen={true}
          onClose={() => setIsArchiveDialogOpen(false)}
          onConfirm={handleConfirmArchive}
          title="Archive Document?"
          message={`Are you sure you want to archive "${doc.title}"?`}
          confirmText="Archive Document"
          variant="danger"
          isLoading={isProcessing}
        />
      )}
    </div>
  );
}
