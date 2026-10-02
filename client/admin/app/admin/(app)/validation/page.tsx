'use client';

import React, { useState, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useValidationStore } from '@/context/ValidationStoreContext';
import { ValidationItem, ValidationCategory, ValidationStatus } from '@/lib/types';
import { ADMIN_ROUTES, ADMIN_DYNAMIC_ROUTES } from '@/constants/routes';
import { formatDate } from '@/lib/utils';
import { PageHeader } from '@/components/shared/PageHeader';
import { FilterBar } from '@/components/shared/FilterBar';
import { MetricCard } from '@/components/shared/MetricCard';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Dropdown } from '@/components/ui/Dropdown';
import { Dialog } from '@/components/ui/Dialog';
import { Textarea } from '@/components/ui/Textarea';
import { EmptyState } from '@/components/shared/EmptyState';
import {
  CheckCircle2,
  XCircle,
  Eye,
  Clock,
  AlertCircle,
  FileText,
  ChevronLeft,
  ChevronRight,
  MoreVertical,
  CheckSquare,
  Sparkles,
  GitFork,
  ArrowRight,
} from 'lucide-react';

export default function ValidationListPage() {
  const router = useRouter();
  const {
    filteredItems,
    searchQuery,
    setSearchQuery,
    typeFilter,
    setTypeFilter,
    statusFilter,
    setStatusFilter,
    confidenceFilter,
    setConfidenceFilter,
    resetFilters,
    approveItem,
    rejectItem,
    bulkApproveItems,
    metrics,
  } = useValidationStore();

  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 8;

  // Selected items for bulk actions
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [rejectTarget, setRejectTarget] = useState<ValidationItem | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [rejectError, setRejectError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const totalPages = Math.ceil(filteredItems.length / pageSize) || 1;
  const paginatedItems = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredItems.slice(start, start + pageSize);
  }, [filteredItems, currentPage, pageSize]);

  const handleToggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleSelectAllOnPage = () => {
    const pageIds = paginatedItems.map((i) => i.id);
    const allSelected = pageIds.every((id) => selectedIds.includes(id));
    if (allSelected) {
      setSelectedIds((prev) => prev.filter((id) => !pageIds.includes(id)));
    } else {
      setSelectedIds((prev) => Array.from(new Set([...prev, ...pageIds])));
    }
  };

  const handleBulkApprove = () => {
    if (selectedIds.length === 0) return;
    bulkApproveItems(selectedIds);
    setSelectedIds([]);
  };

  const handleConfirmReject = () => {
    if (!rejectReason.trim()) {
      setRejectError('A rejection note/reason is required for quality audit logging.');
      return;
    }
    if (!rejectTarget) return;

    setIsProcessing(true);
    setTimeout(() => {
      rejectItem(rejectTarget.id, rejectReason);
      setIsProcessing(false);
      setRejectTarget(null);
      setRejectReason('');
      setRejectError(null);
    }, 300);
  };

  const getConfidenceBadge = (score: number) => {
    if (score >= 90) {
      return <Badge variant="success">{score}% (High)</Badge>;
    } else if (score >= 70) {
      return <Badge variant="warning">{score}% (Medium)</Badge>;
    }
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
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Validation Queue"
        subtitle="Review extracted legal entities, relationships, citations, and metadata before they enter the trusted knowledge layer."
      />

      {/* Workflow Banner */}
      <div className="p-4 rounded-xl bg-white border border-[#C9D4E1] shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-[#2563A8]" />
          <span className="font-bold text-[#17253A]">Quality Control Lifecycle:</span>
        </div>
        <div className="flex flex-wrap items-center gap-1.5 text-[#526176]">
          <span className="px-2 py-0.5 rounded bg-[#EFF3F7]">Extracted</span>
          <ArrowRight className="h-3 w-3 text-[#718096]" />
          <span className="px-2 py-0.5 rounded bg-[#FBF3D4] text-[#7A5A0F] font-bold">Validation Queue</span>
          <ArrowRight className="h-3 w-3 text-[#718096]" />
          <span className="px-2 py-0.5 rounded bg-[#EFF3F7]">Reviewer</span>
          <ArrowRight className="h-3 w-3 text-[#718096]" />
          <span className="px-2 py-0.5 rounded bg-[#D0EDDB] text-[#1E6B45] font-bold">Trusted Knowledge Layer</span>
        </div>
      </div>

      {/* Telemetry Summary Cards */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono font-bold text-[#17253A] uppercase tracking-wider">
            Queue Summary (Mock Environment)
          </span>
          <span className="text-[11px] font-mono text-[#718096]">Development Data Only</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label="Pending Review"
            value={metrics.pending}
            icon={<Clock className="h-4 w-4" />}
            footerText="Awaiting reviewer approval"
          />
          <MetricCard
            label="High Confidence Pending"
            value={metrics.highConfidencePending}
            icon={<CheckCircle2 className="h-4 w-4" />}
            footerText="Extraction model confidence ≥ 90%"
          />
          <MetricCard
            label="Approved Items"
            value={metrics.approved}
            icon={<CheckSquare className="h-4 w-4" />}
            footerText="Verified into Knowledge Graph"
          />
          <MetricCard
            label="Rejected Items"
            value={metrics.rejected}
            icon={<XCircle className="h-4 w-4" />}
            footerText="Flagged by human reviewer"
          />
        </div>
      </div>

      {/* Filter Bar */}
      <FilterBar
        searchValue={searchQuery}
        onSearchChange={(val) => {
          setSearchQuery(val);
          setCurrentPage(1);
        }}
        placeholder="Search by title, label, or source document..."
        onReset={() => {
          resetFilters();
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
              <option value="ALL">All Categories</option>
              <option value="ENTITY">Entity</option>
              <option value="RELATIONSHIP">Relationship</option>
              <option value="CITATION">Citation</option>
              <option value="DOCUMENT_METADATA">Metadata</option>
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
              <option value="PENDING">Pending</option>
              <option value="APPROVED">Approved</option>
              <option value="REJECTED">Rejected</option>
            </Select>

            <Select
              density="dense"
              value={confidenceFilter}
              onChange={(e) => {
                setConfidenceFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-36 bg-white text-xs"
            >
              <option value="ALL">All Confidence</option>
              <option value="HIGH">High (≥ 90%)</option>
              <option value="MEDIUM">Medium (70-89%)</option>
              <option value="LOW">Low (&lt; 70%)</option>
            </Select>
          </>
        }
      />

      {/* Bulk Actions Bar */}
      {selectedIds.length > 0 && (
        <div className="p-3 rounded-xl bg-[#D9E7F5] border border-[#B5D3EE] flex items-center justify-between text-xs font-mono animate-in fade-in">
          <span className="font-bold text-[#17253A]">
            {selectedIds.length} validation items selected
          </span>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => setSelectedIds([])}>
              Deselect All
            </Button>
            <Button variant="primary" size="sm" onClick={handleBulkApprove}>
              <CheckCircle2 className="h-3.5 w-3.5 mr-1" /> Approve Selected ({selectedIds.length})
            </Button>
          </div>
        </div>
      )}

      {/* Main Validation Table / Card View */}
      {filteredItems.length === 0 ? (
        <EmptyState
          title="No validation items found"
          description="No records match your search or active filter parameters."
          action={
            <Button variant="secondary" size="sm" onClick={resetFilters}>
              Reset Filters
            </Button>
          }
        />
      ) : (
        <div className="space-y-4">
          {/* DESKTOP TABLE */}
          <div className="hidden md:block w-full overflow-hidden rounded-xl border border-[#C9D4E1] bg-white shadow-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm border-collapse">
                <thead>
                  <tr className="bg-[#EFF3F7] border-b border-[#C9D4E1] font-mono text-xs font-bold text-[#526176] uppercase tracking-wider">
                    <th className="px-4 py-3 w-10">
                      <input
                        type="checkbox"
                        checked={
                          paginatedItems.length > 0 &&
                          paginatedItems.every((i) => selectedIds.includes(i.id))
                        }
                        onChange={handleSelectAllOnPage}
                        className="rounded border-[#C9D4E1] text-[#2563A8] focus:ring-[#3B82D0] cursor-pointer"
                      />
                    </th>
                    <th className="px-4 py-3">Extracted Item</th>
                    <th className="px-4 py-3">Category</th>
                    <th className="px-4 py-3">Source Document</th>
                    <th className="px-4 py-3">Confidence</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Created</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#D9E1EA]">
                  {paginatedItems.map((item) => (
                    <tr
                      key={item.id}
                      onClick={() => router.push(ADMIN_DYNAMIC_ROUTES.USER_DETAIL(item.id).replace('/users/', '/validation/'))}
                      className="hover:bg-[#EFF3F7]/50 transition-colors cursor-pointer"
                    >
                      <td className="px-4 py-3.5" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(item.id)}
                          onChange={() => handleToggleSelect(item.id)}
                          className="rounded border-[#C9D4E1] text-[#2563A8] focus:ring-[#3B82D0] cursor-pointer"
                        />
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="flex flex-col max-w-xs">
                          <span className="font-semibold text-[#17253A] text-xs leading-tight truncate">
                            {item.title}
                          </span>
                          <span className="text-[11px] font-mono text-[#718096] truncate mt-0.5">
                            Label: {item.proposedLabel}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3.5">
                        <Badge variant="outline">{item.itemType}</Badge>
                      </td>
                      <td className="px-4 py-3.5 text-xs text-[#526176] max-w-[180px] truncate">
                        <Link
                          href={ADMIN_DYNAMIC_ROUTES.DOCUMENT_DETAIL(item.sourceDocumentId)}
                          onClick={(e) => e.stopPropagation()}
                          className="hover:text-[#2563A8] hover:underline flex items-center gap-1"
                        >
                          <FileText className="h-3 w-3 text-[#718096] shrink-0" />
                          <span className="truncate">{item.sourceDocumentTitle}</span>
                        </Link>
                      </td>
                      <td className="px-4 py-3.5 font-mono text-xs">
                        {getConfidenceBadge(item.confidenceScore)}
                      </td>
                      <td className="px-4 py-3.5">{getStatusBadge(item.status)}</td>
                      <td className="px-4 py-3.5 font-mono text-xs text-[#718096]">
                        {formatDate(item.createdAt)}
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
                              id: 'review',
                              label: 'Review Details',
                              icon: <Eye className="h-3.5 w-3.5" />,
                              onClick: () =>
                                router.push(`/admin/validation/${item.id}`),
                            },
                            ...(item.status === 'PENDING'
                              ? [
                                  {
                                    id: 'approve',
                                    label: 'Quick Approve',
                                    icon: <CheckCircle2 className="h-3.5 w-3.5 text-[#1E6B45]" />,
                                    onClick: () => approveItem(item.id),
                                  },
                                  {
                                    id: 'reject',
                                    label: 'Reject Item',
                                    icon: <XCircle className="h-3.5 w-3.5 text-[#8B2E2E]" />,
                                    danger: true,
                                    onClick: () => {
                                      setRejectTarget(item);
                                      setRejectReason('');
                                      setRejectError(null);
                                    },
                                  },
                                ]
                              : []),
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
            {paginatedItems.map((item) => (
              <div
                key={item.id}
                onClick={() => router.push(`/admin/validation/${item.id}`)}
                className="p-4 rounded-xl bg-white border border-[#C9D4E1] shadow-xs space-y-3 cursor-pointer hover:border-[#3B82D0] transition-colors"
              >
                <div className="flex items-center justify-between">
                  <Badge variant="outline">{item.itemType}</Badge>
                  {getStatusBadge(item.status)}
                </div>

                <div>
                  <h4 className="text-xs font-semibold text-[#17253A]">{item.title}</h4>
                  <p className="text-[11px] font-mono text-[#718096] mt-0.5">{item.proposedLabel}</p>
                </div>

                <div className="flex items-center justify-between text-xs font-mono border-t border-[#D9E1EA] pt-2">
                  <span className="text-[#526176]">{item.sourceDocumentTitle}</span>
                  {getConfidenceBadge(item.confidenceScore)}
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-4 py-3 rounded-xl bg-[#EFF3F7] border border-[#C9D4E1] text-xs font-mono">
            <span className="text-[#526176]">
              Showing {Math.min((currentPage - 1) * pageSize + 1, filteredItems.length)} to{' '}
              {Math.min(currentPage * pageSize, filteredItems.length)} of {filteredItems.length} items
            </span>

            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
              >
                <ChevronLeft className="h-4 w-4 mr-1" /> Previous
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
                Next <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Reject Modal Dialog */}
      {rejectTarget && (
        <Dialog
          isOpen={true}
          onClose={() => setRejectTarget(null)}
          title="Reject Validation Item"
          description={`Provide a reviewer note explaining why "${rejectTarget.title}" is being rejected.`}
          footer={
            <>
              <Button variant="ghost" onClick={() => setRejectTarget(null)} disabled={isProcessing}>
                Cancel
              </Button>
              <Button variant="destructive" onClick={handleConfirmReject} isLoading={isProcessing}>
                <XCircle className="h-4 w-4 mr-1.5" /> Reject Item
              </Button>
            </>
          }
        >
          <div className="space-y-4">
            <div className="p-3 rounded-lg bg-[#EFF3F7] border border-[#D9E1EA] text-xs font-mono space-y-1">
              <span className="text-[#718096]">Proposed Item:</span>
              <p className="font-bold text-[#17253A]">{rejectTarget.title}</p>
              <p className="text-[11px] text-[#526176]">Source: {rejectTarget.sourceDocumentTitle}</p>
            </div>

            <div>
              <label className="block text-xs font-mono font-medium text-[#17253A] mb-1">
                Rejection Note / Reason <span className="text-[#8B2E2E]">*</span>
              </label>
              <Textarea
                value={rejectReason}
                onChange={(e) => {
                  setRejectReason(e.target.value);
                  if (rejectError) setRejectError(null);
                }}
                placeholder="e.g. Incorrect relationship direction. Evidence snippet indicates conflicts_with rather than modifies."
                error={!!rejectError}
              />
              {rejectError && (
                <p className="text-xs text-[#8B2E2E] font-mono mt-1 flex items-center gap-1">
                  <AlertCircle className="h-3.5 w-3.5" /> {rejectError}
                </p>
              )}
            </div>
          </div>
        </Dialog>
      )}
    </div>
  );
}
