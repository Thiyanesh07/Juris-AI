'use client';

import React, { useState, useMemo } from 'react';
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
import { Upload, Eye, Cpu, Archive, MoreVertical, FileText, ChevronLeft, ChevronRight, Activity } from 'lucide-react';

export default function DocumentsListPage() {
  const router = useRouter();
  const { documents, startIngestion, archiveDocument } = useDocumentStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 8;

  const [archiveTarget, setArchiveTarget] = useState<Document | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const filteredDocs = useMemo(() => {
    return documents.filter((d) => {
      const matchesSearch =
        d.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        d.fileName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        d.source.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesType = typeFilter === 'ALL' || d.documentType === typeFilter;
      const matchesStatus = statusFilter === 'ALL' || d.status === statusFilter;

      return matchesSearch && matchesType && matchesStatus;
    });
  }, [documents, searchQuery, typeFilter, statusFilter]);

  const totalPages = Math.ceil(filteredDocs.length / pageSize) || 1;
  const paginatedDocs = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredDocs.slice(start, start + pageSize);
  }, [filteredDocs, currentPage, pageSize]);

  const handleStartIngestion = (doc: Document) => {
    startIngestion(doc.id);
  };

  const handleConfirmArchive = () => {
    if (!archiveTarget) return;
    setIsProcessing(true);
    setTimeout(() => {
      archiveDocument(archiveTarget.id);
      setIsProcessing(false);
      setArchiveTarget(null);
    }, 300);
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
        subtitle="Manage legal corpora, upload legal documents, and track parsing statuses."
        actions={
          <Link href={ADMIN_ROUTES.DOCUMENTS + '/new'}>
            <Button variant="primary" size="md">
              <Upload className="h-4 w-4 mr-2" />
              Upload Document
            </Button>
          </Link>
        }
      />

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
              <option value="Constitution">Constitution</option>
              <option value="Act">Act</option>
              <option value="Amendment Act">Amendment Act</option>
              <option value="Rule">Rule</option>
              <option value="Regulation">Regulation</option>
              <option value="Judgment">Judgment</option>
              <option value="Notification">Notification</option>
              <option value="Other">Other</option>
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
              <option value="UPLOADED">Uploaded</option>
              <option value="PROCESSING">Processing</option>
              <option value="READY">Ready</option>
              <option value="FAILED">Failed</option>
              <option value="ARCHIVED">Archived</option>
            </Select>
          </>
        }
      />

      {/* Main Table / List Container */}
      {filteredDocs.length === 0 ? (
        <EmptyState
          title="No documents found"
          description="No records match your search or filter parameters."
        />
      ) : (
        <div className="space-y-4">
          {/* DESKTOP TABLE */}
          <div className="hidden md:block w-full overflow-hidden rounded-xl border border-[#C9D4E1] bg-white shadow-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm border-collapse">
                <thead>
                  <tr className="bg-[#EFF3F7] border-b border-[#C9D4E1] font-mono text-xs font-bold text-[#526176] uppercase tracking-wider">
                    <th className="px-4 py-3">Document</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Source</th>
                    <th className="px-4 py-3">Ingestion Status</th>
                    <th className="px-4 py-3">Uploaded</th>
                    <th className="px-4 py-3">Size</th>
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
                              {doc.fileName}
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
                      <td className="px-4 py-3.5 font-mono text-xs text-[#718096]">
                        {formatBytes(doc.fileSizeBytes)}
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
                              id: 'ingest',
                              label: doc.status === 'PROCESSING' ? 'Processing...' : 'Start Ingestion',
                              icon: <Cpu className="h-3.5 w-3.5" />,
                              disabled: doc.status === 'PROCESSING',
                              onClick: () => handleStartIngestion(doc),
                            },
                            ...(doc.latestJobId
                              ? [
                                  {
                                    id: 'view-ingest',
                                    label: 'View Ingestion Job',
                                    icon: <Activity className="h-3.5 w-3.5" />,
                                    onClick: () =>
                                      router.push(ADMIN_DYNAMIC_ROUTES.INGESTION_JOB_DETAIL(doc.latestJobId!)),
                                  },
                                ]
                              : []),
                            {
                              id: 'archive',
                              label: 'Archive Document',
                              icon: <Archive className="h-3.5 w-3.5" />,
                              danger: true,
                              disabled: doc.status === 'ARCHIVED',
                              onClick: () => setArchiveTarget(doc),
                            },
                          ]}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* MOBILE CARDS LIST */}
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
                  <span>{formatBytes(doc.fileSizeBytes)}</span>
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

      {/* Archive Modal */}
      {archiveTarget && (
        <ConfirmDialog
          isOpen={true}
          onClose={() => setArchiveTarget(null)}
          onConfirm={handleConfirmArchive}
          title="Archive Document?"
          message={`Are you sure you want to archive "${archiveTarget.title}"? It will be marked as archived in the document repository.`}
          confirmText="Archive Document"
          variant="danger"
          isLoading={isProcessing}
        />
      )}
    </div>
  );
}
