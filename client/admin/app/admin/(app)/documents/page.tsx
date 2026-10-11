'use client';

import React, { useState, useMemo, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useDocumentStore } from '@/context/DocumentStoreContext';
import { Document, DocumentTypeCategory, DocumentStatus } from '@/lib/types';
import { ADMIN_ROUTES, ADMIN_DYNAMIC_ROUTES } from '@/constants/routes';
import { formatDate, formatBytes } from '@/lib/utils';
import { PageHeader } from '@/components/shared/PageHeader';
import { FilterBar } from '@/components/shared/FilterBar';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Dropdown } from '@/components/ui/Dropdown';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { EmptyState } from '@/components/shared/EmptyState';
import {
  Upload,
  Eye,
  Cpu,
  Archive,
  RotateCcw,
  MoreVertical,
  FileText,
  ChevronLeft,
  ChevronRight,
  Activity,
  AlertCircle,
  RefreshCw,
  CheckCircle2,
} from 'lucide-react';

export default function DocumentsListPage() {
  const router = useRouter();
  const {
    documents,
    documentsTotal,
    isLoading,
    documentsError,
    fetchDocuments,
    archiveDocument,
    restoreDocument,
    reprocessDocument,
  } = useDocumentStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  const [archiveTarget, setArchiveTarget] = useState<Document | null>(null);
  const [restoreTarget, setRestoreTarget] = useState<Document | null>(null);
  const [isProcessingAction, setIsProcessingAction] = useState(false);
  const [actionFeedback, setActionFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const loadDocs = useCallback(() => {
    fetchDocuments({
      page: 1,
      page_size: 100,
      status: statusFilter === 'ALL' ? undefined : statusFilter,
      type: typeFilter === 'ALL' ? undefined : typeFilter,
      search: searchQuery.trim() || undefined,
    });
  }, [fetchDocuments, statusFilter, typeFilter, searchQuery]);

  useEffect(() => {
    loadDocs();
  }, [loadDocs]);

  const filteredDocs = useMemo(() => {
    return documents.filter((d) => {
      const matchesSearch =
        !searchQuery.trim() ||
        d.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        d.fileName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        d.source.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesType = typeFilter === 'ALL' || d.documentType.toLowerCase() === typeFilter.toLowerCase();
      const matchesStatus = statusFilter === 'ALL' || d.status.toLowerCase() === statusFilter.toLowerCase();

      return matchesSearch && matchesType && matchesStatus;
    });
  }, [documents, searchQuery, typeFilter, statusFilter]);

  const totalPages = Math.ceil(filteredDocs.length / pageSize) || 1;
  const paginatedDocs = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredDocs.slice(start, start + pageSize);
  }, [filteredDocs, currentPage, pageSize]);

  const handleConfirmArchive = async () => {
    if (!archiveTarget) return;
    setIsProcessingAction(true);
    setActionFeedback(null);
    try {
      await archiveDocument(archiveTarget.id);
      setActionFeedback({
        type: 'success',
        message: `Document "${archiveTarget.title}" was archived successfully.`,
      });
      setArchiveTarget(null);
      loadDocs();
    } catch (err) {
      setActionFeedback({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to archive document.',
      });
    } finally {
      setIsProcessingAction(false);
    }
  };

  const handleConfirmRestore = async () => {
    if (!restoreTarget) return;
    setIsProcessingAction(true);
    setActionFeedback(null);
    try {
      const res = await restoreDocument(restoreTarget.id);
      setActionFeedback({
        type: 'success',
        message: res.message || `Document restored with status ${res.status?.toUpperCase()}.`,
      });
      setRestoreTarget(null);
      loadDocs();
    } catch (err) {
      setActionFeedback({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to restore document.',
      });
    } finally {
      setIsProcessingAction(false);
    }
  };

  const handleReprocess = async (doc: Document) => {
    setIsProcessingAction(true);
    setActionFeedback(null);
    try {
      const res = await reprocessDocument(doc.id);
      setActionFeedback({
        type: 'success',
        message: res.message || `Document reprocess initiated for "${doc.title}".`,
      });
      loadDocs();
    } catch (err) {
      setActionFeedback({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to initiate reprocess.',
      });
    } finally {
      setIsProcessingAction(false);
    }
  };

  const getStatusBadge = (status: DocumentStatus) => {
    switch (status) {
      case 'READY':
        return <Badge variant="success">Ready</Badge>;
      case 'PROCESSING':
        return (
          <Badge variant="primary">
            <Activity className="h-3 w-3 mr-1 animate-spin" /> Processing
          </Badge>
        );
      case 'FAILED':
        return <Badge variant="error">Failed</Badge>;
      case 'ARCHIVED':
        return <Badge variant="outline">Archived</Badge>;
      case 'UPLOADED':
      default:
        return <Badge variant="default">Uploaded</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="Documents"
        subtitle="Manage legal corpora, review ingestion statuses, and trigger processing workflows."
        actions={
          <div className="flex items-center gap-2">
            <Button variant="secondary" size="md" onClick={loadDocs} disabled={isLoading}>
              <RefreshCw className={`h-4 w-4 mr-1.5 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Link href={ADMIN_ROUTES.DOCUMENTS + '/new'}>
              <Button variant="primary" size="md">
                <Upload className="h-4 w-4 mr-2" />
                Upload Document
              </Button>
            </Link>
          </div>
        }
      />

      {/* Action Notification */}
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

      {/* API Error Alert */}
      {documentsError && (
        <div className="p-4 rounded-xl bg-[#F5D9D9] border border-[#E8B8B8] text-[#8B2E2E] flex items-center justify-between">
          <div className="flex items-center gap-2 font-mono text-xs">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>Failed to load documents: {documentsError}</span>
          </div>
          <Button variant="secondary" size="sm" onClick={loadDocs}>
            Retry Request
          </Button>
        </div>
      )}

      {/* Filter Bar */}
      <FilterBar
        searchValue={searchQuery}
        onSearchChange={(val) => {
          setSearchQuery(val);
          setCurrentPage(1);
        }}
        placeholder="Search documents by title, filename, or source..."
        onReset={() => {
          setSearchQuery('');
          setTypeFilter('ALL');
          setStatusFilter('ALL');
          setCurrentPage(1);
        }}
        filters={
          <>
            <Select
              density="dense"
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-36 bg-white text-xs"
            >
              <option value="ALL">All Types</option>
              <option value="constitution">Constitution</option>
              <option value="act">Act</option>
              <option value="rule">Rule</option>
              <option value="regulation">Regulation</option>
              <option value="judgment">Judgment</option>
              <option value="notification">Notification</option>
              <option value="other">Other</option>
            </Select>

            <Select
              density="dense"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-32 bg-white text-xs"
            >
              <option value="ALL">All Statuses</option>
              <option value="uploaded">Uploaded</option>
              <option value="processing">Processing</option>
              <option value="ready">Ready</option>
              <option value="failed">Failed</option>
              <option value="disabled">Archived</option>
            </Select>
          </>
        }
      />

      {/* Main Table / Empty State */}
      {isLoading && documents.length === 0 ? (
        <div className="p-12 text-center rounded-xl border border-[#C9D4E1] bg-white">
          <Activity className="h-6 w-6 text-[#2563A8] animate-spin mx-auto mb-2" />
          <p className="font-mono text-xs text-[#526176]">Loading documents from repository...</p>
        </div>
      ) : filteredDocs.length === 0 ? (
        <EmptyState
          title="No documents found"
          description={
            documentsError
              ? 'Could not connect to the document repository. Please check backend status and retry.'
              : 'No documents match your query or filter criteria in the legal corpus.'
          }
          action={
            <Link href={ADMIN_ROUTES.DOCUMENTS + '/new'}>
              <Button variant="primary" size="sm">
                <Upload className="h-4 w-4 mr-1.5" />
                Upload New Document
              </Button>
            </Link>
          }
        />
      ) : (
        <div className="space-y-4">
          {/* Desktop Table */}
          <div className="hidden md:block w-full overflow-hidden rounded-xl border border-[#C9D4E1] bg-white shadow-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm border-collapse">
                <thead>
                  <tr className="bg-[#EFF3F7] border-b border-[#C9D4E1] font-mono text-xs font-bold text-[#526176] uppercase tracking-wider">
                    <th className="px-4 py-3">Document</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Legal Source</th>
                    <th className="px-4 py-3">Ingestion Status</th>
                    <th className="px-4 py-3">Created</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#D9E1EA]">
                  {paginatedDocs.map((doc) => (
                    <tr
                      key={doc.id}
                      onClick={() => router.push(ADMIN_DYNAMIC_ROUTES.DOCUMENT_DETAIL(doc.id))}
                      className="hover:bg-[#EFF3F7]/50 transition-colors cursor-pointer"
                    >
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-3">
                          <div className="p-2 rounded-lg bg-[#D9E7F5] text-[#2563A8] shrink-0">
                            <FileText className="h-4 w-4" />
                          </div>
                          <div className="flex flex-col max-w-xs truncate">
                            <span className="font-semibold text-[#17253A] text-xs leading-tight truncate">
                              {doc.title}
                            </span>
                            <span className="text-[11px] font-mono text-[#718096] truncate">
                              {doc.id}
                            </span>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3.5">
                        <Badge variant="outline">{doc.documentType}</Badge>
                      </td>
                      <td className="px-4 py-3.5 text-xs text-[#526176] truncate max-w-[180px]">
                        {doc.source}
                      </td>
                      <td className="px-4 py-3.5">{getStatusBadge(doc.status)}</td>
                      <td className="px-4 py-3.5 font-mono text-xs text-[#718096]">
                        {formatDate(doc.createdAt)}
                      </td>
                      <td className="px-4 py-3.5 text-right" onClick={(e) => e.stopPropagation()}>
                        <Dropdown
                          trigger={
                            <button className="p-1.5 rounded-lg hover:bg-[#D9E7F5] text-[#526176] transition-colors cursor-pointer">
                              <MoreVertical className="h-4 w-4" />
                            </button>
                          }
                          items={[
                            {
                              id: 'view',
                              label: 'View Details',
                              icon: <Eye className="h-3.5 w-3.5" />,
                              onClick: () => router.push(ADMIN_DYNAMIC_ROUTES.DOCUMENT_DETAIL(doc.id)),
                            },
                            {
                              id: 'ingestion-page',
                              label: 'View Pipeline Stages',
                              icon: <Cpu className="h-3.5 w-3.5" />,
                              onClick: () => router.push(ADMIN_DYNAMIC_ROUTES.INGESTION_JOB_DETAIL(doc.id)),
                            },
                            ...(doc.status !== 'ARCHIVED'
                              ? [
                                  {
                                    id: 'reprocess',
                                    label: doc.status === 'PROCESSING' ? 'Processing...' : 'Reprocess Ingestion',
                                    icon: <RotateCcw className="h-3.5 w-3.5" />,
                                    disabled: doc.status === 'PROCESSING' || isProcessingAction,
                                    onClick: () => handleReprocess(doc),
                                  },
                                  {
                                    id: 'archive',
                                    label: 'Archive Document',
                                    icon: <Archive className="h-3.5 w-3.5" />,
                                    danger: true,
                                    onClick: () => setArchiveTarget(doc),
                                  },
                                ]
                              : [
                                  {
                                    id: 'restore',
                                    label: 'Restore Document',
                                    icon: <RotateCcw className="h-3.5 w-3.5" />,
                                    onClick: () => setRestoreTarget(doc),
                                  },
                                ]),
                          ]}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Mobile Cards List */}
          <div className="md:hidden space-y-3">
            {paginatedDocs.map((doc) => (
              <div
                key={doc.id}
                onClick={() => router.push(ADMIN_DYNAMIC_ROUTES.DOCUMENT_DETAIL(doc.id))}
                className="p-4 rounded-xl bg-white border border-[#C9D4E1] shadow-xs space-y-3 cursor-pointer hover:border-[#3B82D0] transition-colors"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-[#17253A] text-sm truncate max-w-[200px]">
                    {doc.title}
                  </span>
                  {getStatusBadge(doc.status)}
                </div>

                <div className="flex items-center justify-between text-xs font-mono text-[#718096]">
                  <Badge variant="outline">{doc.documentType}</Badge>
                  <span>{formatDate(doc.createdAt)}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-4 py-3 rounded-xl bg-[#EFF3F7] border border-[#C9D4E1] text-xs font-mono">
            <span className="text-[#526176]">
              Showing {Math.min((currentPage - 1) * pageSize + 1, filteredDocs.length)} to{' '}
              {Math.min(currentPage * pageSize, filteredDocs.length)} of {filteredDocs.length} documents
            </span>

            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Previous
              </Button>

              <span className="px-3 py-1 bg-white rounded border border-[#C9D4E1] font-semibold text-[#17253A]">
                {currentPage} / {totalPages}
              </span>

              <Button
                variant="ghost"
                size="sm"
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
              >
                Next
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Archive Confirm Dialog */}
      {archiveTarget && (
        <ConfirmDialog
          isOpen={true}
          onClose={() => setArchiveTarget(null)}
          onConfirm={handleConfirmArchive}
          title="Archive Legal Document?"
          message={`Are you sure you want to archive "${archiveTarget.title}"? The document will be marked as disabled/archived, and will not participate in retrieval until restored.`}
          confirmText="Archive Document"
          variant="danger"
          isLoading={isProcessingAction}
        />
      )}

      {/* Restore Confirm Dialog */}
      {restoreTarget && (
        <ConfirmDialog
          isOpen={true}
          onClose={() => setRestoreTarget(null)}
          onConfirm={handleConfirmRestore}
          title="Restore Legal Document?"
          message={`Restore "${restoreTarget.title}"? Note: The document will only be marked READY if all required ingestion stages succeeded; otherwise it will be restored to FAILED status.`}
          confirmText="Restore Document"
          variant="primary"
          isLoading={isProcessingAction}
        />
      )}
    </div>
  );
}
