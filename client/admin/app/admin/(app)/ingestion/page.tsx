'use client';

import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useDocumentStore } from '@/context/DocumentStoreContext';
import { ProcessingJobSummary } from '@/lib/apiTypes';
import { ADMIN_ROUTES, ADMIN_DYNAMIC_ROUTES } from '@/constants/routes';
import { formatDate } from '@/lib/utils';
import { PageHeader } from '@/components/shared/PageHeader';
import { FilterBar } from '@/components/shared/FilterBar';
import { MetricCard } from '@/components/shared/MetricCard';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Dropdown } from '@/components/ui/Dropdown';
import { EmptyState } from '@/components/shared/EmptyState';
import {
  Cpu,
  Eye,
  RotateCcw,
  Activity,
  FileText,
  CheckCircle2,
  AlertCircle,
  Clock,
  MoreVertical,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
} from 'lucide-react';

const STAGE_LABELS: Record<string, string> = {
  ingestion: 'Ingestion',
  extraction: 'Text Extraction',
  chunking: 'Structural Chunking',
  embedding: 'InLegalBERT Embedding',
  vector_index: 'FAISS Vector Index',
  entity_extraction: 'Legal Entity Extraction',
  relation_extraction: 'Relation Extraction',
  graph_population: 'Knowledge Graph Population',
};

export default function IngestionDashboardPage() {
  const router = useRouter();
  const {
    ingestionJobs,
    jobsTotal,
    jobsLoading,
    jobsError,
    fetchJobs,
    reprocessDocument,
  } = useDocumentStore();

  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [stageFilter, setStageFilter] = useState<string>('ALL');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [reprocessingDocId, setReprocessingDocId] = useState<string | null>(null);
  const pageSize = 15;

  // Load jobs with server-side query parameters
  const loadJobs = useCallback(
    (page: number, status: string, stage: string) => {
      fetchJobs({
        page,
        page_size: pageSize,
        status: status === 'ALL' ? undefined : status,
        stage: stage === 'ALL' ? undefined : stage,
      });
    },
    [fetchJobs, pageSize]
  );

  useEffect(() => {
    loadJobs(currentPage, statusFilter, stageFilter);
  }, [loadJobs, currentPage, statusFilter, stageFilter]);

  // Active-job polling: only poll while jobs are running or pending, and page is active
  const hasActiveJobs = useMemo(() => {
    return ingestionJobs.some(
      (j) => j.status?.toLowerCase() === 'running' || j.status?.toLowerCase() === 'pending'
    );
  }, [ingestionJobs]);

  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!hasActiveJobs) {
      if (pollingRef.current) clearInterval(pollingRef.current);
      return;
    }

    const interval = setInterval(() => {
      if (typeof document !== 'undefined' && document.hidden) return;
      loadJobs(currentPage, statusFilter, stageFilter);
    }, 5000);

    pollingRef.current = interval;
    return () => clearInterval(interval);
  }, [hasActiveJobs, loadJobs, currentPage, statusFilter, stageFilter]);

  // Client-side text filter (for document title or job ID search)
  const displayedJobs = useMemo(() => {
    if (!searchQuery.trim()) return ingestionJobs;
    const q = searchQuery.toLowerCase().trim();
    return ingestionJobs.filter(
      (job) =>
        job.id.toLowerCase().includes(q) ||
        (job.document_title && job.document_title.toLowerCase().includes(q)) ||
        job.stage.toLowerCase().includes(q)
    );
  }, [ingestionJobs, searchQuery]);

  // Derived counts from current queried job records
  const counts = useMemo(() => {
    const queued = ingestionJobs.filter((j) => j.status?.toLowerCase() === 'pending').length;
    const running = ingestionJobs.filter((j) => j.status?.toLowerCase() === 'running').length;
    const completed = ingestionJobs.filter((j) => j.status?.toLowerCase() === 'completed').length;
    const failed = ingestionJobs.filter((j) => j.status?.toLowerCase() === 'failed').length;
    return { queued, running, completed, failed };
  }, [ingestionJobs]);

  const totalPages = Math.ceil(jobsTotal / pageSize) || 1;

  const handleRetryJob = async (job: ProcessingJobSummary) => {
    if (reprocessingDocId) return;
    setReprocessingDocId(job.document_id);
    try {
      await reprocessDocument(job.document_id);
      loadJobs(currentPage, statusFilter, stageFilter);
    } catch {
      // Handled in store
    } finally {
      setReprocessingDocId(null);
    }
  };

  const getStatusBadge = (status: string) => {
    const s = status?.toLowerCase();
    switch (s) {
      case 'completed':
        return <Badge variant="success">Completed</Badge>;
      case 'running':
        return (
          <Badge variant="primary">
            <Activity className="h-3 w-3 mr-1 animate-spin" /> In Progress
          </Badge>
        );
      case 'pending':
        return <Badge variant="default">Queued</Badge>;
      case 'failed':
        return <Badge variant="error">Failed</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const formatStage = (stage: string) => {
    return STAGE_LABELS[stage.toLowerCase()] || stage.replace(/_/g, ' ');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="Ingestion Jobs"
        subtitle="Real-time pipeline execution, stage progression, and persisted task audit trail."
        actions={
          <Button
            variant="secondary"
            size="sm"
            onClick={() => loadJobs(currentPage, statusFilter, stageFilter)}
            disabled={jobsLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-1.5 ${jobsLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        }
      />

      {/* Summary Metrics */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono font-bold text-[#17253A] uppercase tracking-wider">
            Pipeline Stage Telemetry (Database Persisted)
          </span>
          <span className="text-[11px] font-mono text-[#718096]">
            Total Records: {jobsTotal} {hasActiveJobs ? '• Polling Active' : '• Idle'}
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label="Queued Jobs"
            value={counts.queued}
            icon={<Clock className="h-4 w-4" />}
            footerText="Awaiting worker pipeline start"
          />
          <MetricCard
            label="Active Processing"
            value={counts.running}
            icon={<Cpu className="h-4 w-4" />}
            footerText="Currently running stages"
          />
          <MetricCard
            label="Completed Jobs"
            value={counts.completed}
            icon={<CheckCircle2 className="h-4 w-4" />}
            footerText="Successfully persisted"
          />
          <MetricCard
            label="Failed Jobs"
            value={counts.failed}
            icon={<AlertCircle className="h-4 w-4" />}
            footerText="Persisted pipeline errors"
          />
        </div>
      </div>

      {/* API Error Alert */}
      {jobsError && (
        <div className="p-4 rounded-xl bg-[#F5D9D9] border border-[#E8B8B8] text-[#8B2E2E] flex items-center justify-between">
          <div className="flex items-center gap-2 font-mono text-xs">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>Failed to load ingestion jobs: {jobsError}</span>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => loadJobs(currentPage, statusFilter, stageFilter)}
          >
            Retry
          </Button>
        </div>
      )}

      {/* Filter Bar */}
      <FilterBar
        searchValue={searchQuery}
        onSearchChange={setSearchQuery}
        placeholder="Filter by job ID, document title, or stage..."
        onReset={() => {
          setSearchQuery('');
          setStatusFilter('ALL');
          setStageFilter('ALL');
          setCurrentPage(1);
        }}
        filters={
          <div className="flex flex-wrap items-center gap-2">
            <Select
              density="dense"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-36 bg-white text-xs"
            >
              <option value="ALL">All Statuses</option>
              <option value="pending">Queued</option>
              <option value="running">In Progress</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </Select>

            <Select
              density="dense"
              value={stageFilter}
              onChange={(e) => {
                setStageFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-48 bg-white text-xs"
            >
              <option value="ALL">All Pipeline Stages</option>
              <option value="ingestion">Ingestion</option>
              <option value="extraction">Text Extraction</option>
              <option value="chunking">Structural Chunking</option>
              <option value="embedding">Embedding</option>
              <option value="vector_index">Vector Index</option>
              <option value="entity_extraction">Entity Extraction</option>
              <option value="relation_extraction">Relation Extraction</option>
              <option value="graph_population">Graph Population</option>
            </Select>
          </div>
        }
      />

      {/* Loading State */}
      {jobsLoading && ingestionJobs.length === 0 ? (
        <div className="p-12 text-center rounded-xl border border-[#C9D4E1] bg-white">
          <Activity className="h-6 w-6 text-[#2563A8] animate-spin mx-auto mb-2" />
          <p className="font-mono text-xs text-[#526176]">Loading ingestion jobs from backend...</p>
        </div>
      ) : displayedJobs.length === 0 ? (
        <EmptyState
          title="No ingestion jobs found"
          description={
            jobsError
              ? 'Unable to display job records due to a network or server error.'
              : 'No job records match the requested stage, status, or search filters.'
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
                    <th className="px-4 py-3">Job ID</th>
                    <th className="px-4 py-3">Document</th>
                    <th className="px-4 py-3">Pipeline Stage</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Created</th>
                    <th className="px-4 py-3">Updated</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#D9E1EA]">
                  {displayedJobs.map((job) => (
                    <tr
                      key={job.id}
                      onClick={() => router.push(ADMIN_DYNAMIC_ROUTES.INGESTION_JOB_DETAIL(job.id))}
                      className="hover:bg-[#EFF3F7]/50 transition-colors cursor-pointer"
                    >
                      <td className="px-4 py-3.5 font-mono text-xs font-semibold text-[#2563A8]">
                        {job.id.slice(0, 8)}...
                      </td>
                      <td className="px-4 py-3.5">
                        <Link
                          href={ADMIN_DYNAMIC_ROUTES.DOCUMENT_DETAIL(job.document_id)}
                          onClick={(e) => e.stopPropagation()}
                          className="font-medium text-[#17253A] hover:text-[#2563A8] hover:underline flex items-center gap-1.5"
                        >
                          <FileText className="h-3.5 w-3.5 text-[#526176] shrink-0" />
                          <span className="truncate max-w-xs">{job.document_title || job.document_id}</span>
                        </Link>
                      </td>
                      <td className="px-4 py-3.5 font-mono text-xs font-medium text-[#17253A]">
                        {formatStage(job.stage)}
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-1.5">
                          {getStatusBadge(job.status)}
                          {job.error && (
                            <span
                              title={job.error}
                              className="text-xs text-[#8B2E2E] cursor-help max-w-[120px] truncate"
                            >
                              ({job.error})
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3.5 font-mono text-xs text-[#718096]">
                        {job.created_at ? formatDate(job.created_at) : '—'}
                      </td>
                      <td className="px-4 py-3.5 font-mono text-xs text-[#718096]">
                        {job.updated_at ? formatDate(job.updated_at) : '—'}
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
                              label: 'View Job Details',
                              icon: <Eye className="h-3.5 w-3.5" />,
                              onClick: () => router.push(ADMIN_DYNAMIC_ROUTES.INGESTION_JOB_DETAIL(job.id)),
                            },
                            ...(job.status?.toLowerCase() === 'failed'
                              ? [
                                  {
                                    id: 'retry',
                                    label: reprocessingDocId === job.document_id ? 'Reprocessing...' : 'Reprocess Document',
                                    icon: <RotateCcw className="h-3.5 w-3.5" />,
                                    disabled: reprocessingDocId === job.document_id,
                                    onClick: () => handleRetryJob(job),
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

          {/* Mobile Cards List */}
          <div className="md:hidden space-y-3">
            {displayedJobs.map((job) => (
              <div
                key={job.id}
                onClick={() => router.push(ADMIN_DYNAMIC_ROUTES.INGESTION_JOB_DETAIL(job.id))}
                className="p-4 rounded-xl bg-white border border-[#C9D4E1] shadow-xs space-y-3 cursor-pointer hover:border-[#3B82D0] transition-colors"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-xs text-[#2563A8]">{job.id.slice(0, 8)}...</span>
                  {getStatusBadge(job.status)}
                </div>

                <p className="text-xs font-semibold text-[#17253A] truncate">
                  {job.document_title || job.document_id}
                </p>

                <div className="flex items-center justify-between text-xs font-mono text-[#718096]">
                  <span>Stage: {formatStage(job.stage)}</span>
                  <span>{job.created_at ? formatDate(job.created_at) : '—'}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination Controls */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-4 py-3 rounded-xl bg-[#EFF3F7] border border-[#C9D4E1] text-xs font-mono">
            <span className="text-[#526176]">
              Showing {Math.min((currentPage - 1) * pageSize + 1, jobsTotal)} to{' '}
              {Math.min(currentPage * pageSize, jobsTotal)} of {jobsTotal} job records
            </span>

            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                disabled={currentPage <= 1 || jobsLoading}
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
                disabled={currentPage >= totalPages || jobsLoading}
                onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
              >
                Next
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
