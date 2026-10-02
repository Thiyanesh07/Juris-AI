'use client';

import React, { useState, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useDocumentStore } from '@/context/DocumentStoreContext';
import { IngestionJob, IngestionJobStatus } from '@/lib/types';
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
import { Cpu, Eye, RotateCcw, XCircle, Activity, FileText, CheckCircle2, AlertCircle, Clock, MoreVertical } from 'lucide-react';

export default function IngestionDashboardPage() {
  const router = useRouter();
  const { ingestionJobs, retryIngestion, cancelIngestion } = useDocumentStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const filteredJobs = useMemo(() => {
    return ingestionJobs.filter((job) => {
      const matchesSearch =
        job.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        job.documentTitle.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (job.workerNode && job.workerNode.toLowerCase().includes(searchQuery.toLowerCase()));

      const matchesStatus = statusFilter === 'ALL' || job.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [ingestionJobs, searchQuery, statusFilter]);

  // Metrics calculation
  const metrics = useMemo(() => {
    const queued = ingestionJobs.filter((j) => j.status === 'QUEUED').length;
    const processing = ingestionJobs.filter(
      (j) => j.status === 'PARSING' || j.status === 'EXTRACTING_ENTITIES' || j.status === 'BUILDING_INDEX'
    ).length;
    const completed = ingestionJobs.filter((j) => j.status === 'COMPLETED').length;
    const failed = ingestionJobs.filter((j) => j.status === 'FAILED').length;
    return { queued, processing, completed, failed };
  }, [ingestionJobs]);

  const getStatusBadge = (status: IngestionJobStatus) => {
    switch (status) {
      case 'COMPLETED':
        return <Badge variant="success">Completed</Badge>;
      case 'QUEUED':
        return <Badge variant="default">Queued</Badge>;
      case 'FAILED':
        return <Badge variant="error">Failed</Badge>;
      case 'CANCELLED':
        return <Badge variant="outline">Cancelled</Badge>;
      case 'PARSING':
      case 'EXTRACTING_ENTITIES':
      case 'BUILDING_INDEX':
      default:
        return (
          <Badge variant="primary">
            <Activity className="h-3 w-3 mr-1 animate-spin" /> {status.replace(/_/g, ' ')}
          </Badge>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="Ingestion"
        subtitle="Monitor document processing jobs, entity extraction, and worker telemetry."
      />

      {/* Summary Metrics (Mock Environment / Development Data) */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono font-bold text-[#17253A] uppercase tracking-wider">
            Pipeline Telemetry (Mock Environment)
          </span>
          <span className="text-[11px] font-mono text-[#718096]">Development Data Only</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label="Queued Jobs"
            value={metrics.queued}
            icon={<Clock className="h-4 w-4" />}
            footerText="Awaiting worker assignment"
          />
          <MetricCard
            label="Active Workers"
            value={metrics.processing}
            icon={<Cpu className="h-4 w-4" />}
            footerText="Parsing & extracting entities"
          />
          <MetricCard
            label="Completed Jobs"
            value={metrics.completed}
            icon={<CheckCircle2 className="h-4 w-4" />}
            footerText="Indexed into Knowledge Graph"
          />
          <MetricCard
            label="Failed Jobs"
            value={metrics.failed}
            icon={<AlertCircle className="h-4 w-4" />}
            footerText="Exceptions awaiting retry"
          />
        </div>
      </div>

      {/* Filter Bar */}
      <FilterBar
        searchValue={searchQuery}
        onSearchChange={setSearchQuery}
        placeholder="Search jobs by ID, document title, or worker..."
        onReset={() => {
          setSearchQuery('');
          setStatusFilter('ALL');
        }}
        filters={
          <Select
            density="dense"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-40 bg-white text-xs"
          >
            <option value="ALL">All Statuses</option>
            <option value="QUEUED">Queued</option>
            <option value="PARSING">Parsing</option>
            <option value="EXTRACTING_ENTITIES">Extracting Entities</option>
            <option value="COMPLETED">Completed</option>
            <option value="FAILED">Failed</option>
            <option value="CANCELLED">Cancelled</option>
          </Select>
        }
      />

      {/* Jobs Table */}
      {filteredJobs.length === 0 ? (
        <EmptyState
          title="No ingestion jobs found"
          description="No job records match your search or filter parameters."
        />
      ) : (
        <div className="space-y-4">
          {/* DESKTOP TABLE */}
          <div className="hidden md:block w-full overflow-hidden rounded-xl border border-[#C9D4E1] bg-white shadow-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm border-collapse">
                <thead>
                  <tr className="bg-[#EFF3F7] border-b border-[#C9D4E1] font-mono text-xs font-bold text-[#526176] uppercase tracking-wider">
                    <th className="px-4 py-3">Job ID</th>
                    <th className="px-4 py-3">Document Title</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Progress</th>
                    <th className="px-4 py-3">Worker Node</th>
                    <th className="px-4 py-3">Started</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#D9E1EA]">
                  {filteredJobs.map((job) => (
                    <tr
                      key={job.id}
                      onClick={() => router.push(ADMIN_DYNAMIC_ROUTES.INGESTION_JOB_DETAIL(job.id))}
                      className="hover:bg-[#EFF3F7]/50 transition-colors cursor-pointer"
                    >
                      <td className="px-4 py-3.5 font-mono text-xs font-semibold text-[#2563A8]">
                        {job.id}
                      </td>
                      <td className="px-4 py-3.5">
                        <Link
                          href={ADMIN_DYNAMIC_ROUTES.DOCUMENT_DETAIL(job.documentId)}
                          onClick={(e) => e.stopPropagation()}
                          className="font-medium text-[#17253A] hover:text-[#2563A8] hover:underline flex items-center gap-1.5"
                        >
                          <FileText className="h-3.5 w-3.5 text-[#526176] shrink-0" />
                          <span className="truncate max-w-xs">{job.documentTitle}</span>
                        </Link>
                      </td>
                      <td className="px-4 py-3.5">{getStatusBadge(job.status)}</td>
                      <td className="px-4 py-3.5 w-40">
                        <div className="flex items-center gap-2 font-mono text-xs text-[#526176]">
                          <div className="w-full bg-[#C9D4E1] h-1.5 rounded-full overflow-hidden">
                            <div
                              className="bg-[#2563A8] h-full transition-all duration-300"
                              style={{ width: `${job.progressPercentage}%` }}
                            />
                          </div>
                          <span>{job.progressPercentage}%</span>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 font-mono text-xs text-[#718096]">
                        {job.workerNode || 'worker-01'}
                      </td>
                      <td className="px-4 py-3.5 font-mono text-xs text-[#718096]">
                        {job.startedAt ? formatDate(job.startedAt) : '—'}
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
                            ...(job.status === 'FAILED' || job.status === 'CANCELLED'
                              ? [
                                  {
                                    id: 'retry',
                                    label: 'Retry Job',
                                    icon: <RotateCcw className="h-3.5 w-3.5" />,
                                    onClick: () => retryIngestion(job.id),
                                  },
                                ]
                              : []),
                            ...(job.status === 'QUEUED' ||
                            job.status === 'PARSING' ||
                            job.status === 'EXTRACTING_ENTITIES' ||
                            job.status === 'BUILDING_INDEX'
                              ? [
                                  {
                                    id: 'cancel',
                                    label: 'Cancel Ingestion',
                                    icon: <XCircle className="h-3.5 w-3.5" />,
                                    danger: true,
                                    onClick: () => cancelIngestion(job.id),
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
            {filteredJobs.map((job) => (
              <div
                key={job.id}
                onClick={() => router.push(ADMIN_DYNAMIC_ROUTES.INGESTION_JOB_DETAIL(job.id))}
                className="p-4 rounded-xl bg-white border border-[#C9D4E1] shadow-xs space-y-3 cursor-pointer hover:border-[#3B82D0] transition-colors"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-xs text-[#2563A8]">{job.id}</span>
                  {getStatusBadge(job.status)}
                </div>

                <p className="text-xs font-semibold text-[#17253A] truncate">{job.documentTitle}</p>

                <div className="flex items-center justify-between text-xs font-mono text-[#718096]">
                  <span>Worker: {job.workerNode || 'worker-01'}</span>
                  <span>{job.progressPercentage}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
