'use client';

import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useDocumentStore } from '@/context/DocumentStoreContext';
import { IngestionJobStatus } from '@/lib/types';
import { ADMIN_ROUTES, ADMIN_DYNAMIC_ROUTES } from '@/constants/routes';
import { formatDate } from '@/lib/utils';
import { PageHeader } from '@/components/shared/PageHeader';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/shared/EmptyState';
import {
  ArrowLeft,
  RotateCcw,
  XCircle,
  FileText,
  Cpu,
  CheckCircle2,
  AlertCircle,
  Clock,
  Layers,
  GitFork,
  ExternalLink,
  ChevronRight,
} from 'lucide-react';

export default function IngestionJobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params?.id as string;

  const { getJobById, retryIngestion, cancelIngestion, getDocumentById } = useDocumentStore();
  const job = getJobById(jobId);
  const doc = job ? getDocumentById(job.documentId) : undefined;

  if (!job) {
    return (
      <div className="space-y-6 max-w-3xl">
        <PageHeader
          title="Ingestion Job Not Found"
          subtitle="The requested ingestion job record could not be found."
          actions={
            <Button variant="ghost" size="sm" onClick={() => router.push(ADMIN_ROUTES.INGESTION)}>
              <ArrowLeft className="h-4 w-4 mr-1.5" />
              Back to Ingestion
            </Button>
          }
        />
        <EmptyState title="Job Record Not Found" description="The job ID does not exist in local session store." />
      </div>
    );
  }

  const handleRetry = () => {
    retryIngestion(job.id);
  };

  const handleCancel = () => {
    cancelIngestion(job.id);
  };

  const getLifecycleStepState = (step: 'QUEUED' | 'PROCESSING' | 'FINAL') => {
    const isFailed = job.status === 'FAILED';
    const isCancelled = job.status === 'CANCELLED';
    const isCompleted = job.status === 'COMPLETED';

    if (step === 'QUEUED') return 'completed';
    if (step === 'PROCESSING') {
      if (job.status === 'QUEUED') return 'pending';
      return 'completed';
    }
    if (step === 'FINAL') {
      if (isCompleted) return 'completed';
      if (isFailed) return 'failed';
      if (isCancelled) return 'cancelled';
      return 'pending';
    }
    return 'pending';
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <PageHeader
        title={`Ingestion Job ${job.id}`}
        subtitle={`Linked Document: ${job.documentTitle}`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => router.push(ADMIN_ROUTES.INGESTION)}>
              <ArrowLeft className="h-4 w-4 mr-1.5" />
              Back to Ingestion
            </Button>
            {doc && (
              <Link href={ADMIN_DYNAMIC_ROUTES.DOCUMENT_DETAIL(doc.id)}>
                <Button variant="secondary" size="sm">
                  <FileText className="h-3.5 w-3.5 mr-1.5" />
                  Source Document
                </Button>
              </Link>
            )}
            {(job.status === 'FAILED' || job.status === 'CANCELLED') && (
              <Button variant="primary" size="sm" onClick={handleRetry}>
                <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
                Retry Ingestion Job
              </Button>
            )}
            {(job.status === 'QUEUED' ||
              job.status === 'PARSING' ||
              job.status === 'EXTRACTING_ENTITIES' ||
              job.status === 'BUILDING_INDEX') && (
              <Button variant="destructive" size="sm" onClick={handleCancel}>
                <XCircle className="h-3.5 w-3.5 mr-1.5" />
                Cancel Processing
              </Button>
            )}
          </div>
        }
      />

      {/* Main Job Overview Card */}
      <div className="p-6 rounded-2xl bg-white border border-[#C9D4E1] shadow-xs space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-[#D9E1EA] gap-4">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-[#2563A8] text-white shrink-0">
              <Cpu className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold font-serif text-[#17253A]">Job {job.id}</h2>
              <Link
                href={ADMIN_DYNAMIC_ROUTES.DOCUMENT_DETAIL(job.documentId)}
                className="text-xs font-mono text-[#2563A8] hover:underline flex items-center gap-1 mt-0.5"
              >
                <span>{job.documentTitle}</span>
                <ExternalLink className="h-3 w-3" />
              </Link>
            </div>
          </div>

          <Badge
            variant={
              job.status === 'COMPLETED'
                ? 'success'
                : job.status === 'FAILED'
                ? 'error'
                : job.status === 'CANCELLED'
                ? 'outline'
                : 'primary'
            }
            size="md"
          >
            {job.status}
          </Badge>
        </div>

        {/* Visual Lifecycle Pipeline Stepper */}
        <div className="p-6 rounded-xl bg-[#F5F7FA] border border-[#C9D4E1] space-y-4">
          <h4 className="text-xs font-mono font-bold text-[#17253A] uppercase tracking-wider">
            Ingestion Pipeline Lifecycle
          </h4>

          <div className="flex items-center justify-between max-w-lg mx-auto py-2">
            {/* Step 1: Queued */}
            <div className="flex flex-col items-center gap-1 text-center">
              <div className="h-8 w-8 rounded-full bg-[#1E6B45] text-white flex items-center justify-center text-xs font-bold font-mono">
                <CheckCircle2 className="h-4 w-4" />
              </div>
              <span className="text-xs font-mono text-[#17253A]">Queued</span>
            </div>

            <div className="flex-1 h-0.5 bg-[#2563A8] mx-2" />

            {/* Step 2: Processing */}
            <div className="flex flex-col items-center gap-1 text-center">
              <div
                className={`h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold font-mono ${
                  getLifecycleStepState('PROCESSING') === 'completed'
                    ? 'bg-[#1E6B45] text-white'
                    : 'bg-[#C9D4E1] text-[#526176]'
                }`}
              >
                <Cpu className="h-4 w-4" />
              </div>
              <span className="text-xs font-mono text-[#17253A]">Processing</span>
            </div>

            <div className="flex-1 h-0.5 bg-[#C9D4E1] mx-2" />

            {/* Step 3: Final State */}
            <div className="flex flex-col items-center gap-1 text-center">
              <div
                className={`h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold font-mono ${
                  job.status === 'COMPLETED'
                    ? 'bg-[#1E6B45] text-white'
                    : job.status === 'FAILED'
                    ? 'bg-[#8B2E2E] text-white'
                    : job.status === 'CANCELLED'
                    ? 'bg-[#718096] text-white'
                    : 'bg-[#C9D4E1] text-[#526176]'
                }`}
              >
                {job.status === 'COMPLETED' ? (
                  <CheckCircle2 className="h-4 w-4" />
                ) : job.status === 'FAILED' ? (
                  <AlertCircle className="h-4 w-4" />
                ) : (
                  <Clock className="h-4 w-4" />
                )}
              </div>
              <span className="text-xs font-mono text-[#17253A]">
                {job.status === 'COMPLETED'
                  ? 'Completed'
                  : job.status === 'FAILED'
                  ? 'Failed'
                  : job.status === 'CANCELLED'
                  ? 'Cancelled'
                  : 'Pending'}
              </span>
            </div>
          </div>

          <div className="w-full bg-[#C9D4E1] h-2 rounded-full overflow-hidden mt-2">
            <div
              className={`h-full transition-all duration-300 ${
                job.status === 'FAILED' ? 'bg-[#8B2E2E]' : 'bg-[#2563A8]'
              }`}
              style={{ width: `${job.progressPercentage}%` }}
            />
          </div>
          <div className="text-right text-xs font-mono text-[#526176]">
            Progress: {job.progressPercentage}%
          </div>
        </div>

        {/* Error Exception Box */}
        {job.errorMessage && (
          <div className="p-4 rounded-xl bg-[#F5D9D9] border border-[#E8B8B8] text-[#8B2E2E] space-y-1">
            <div className="flex items-center gap-2 font-mono font-bold text-xs">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>Pipeline Failure Trace</span>
            </div>
            <p className="text-xs font-mono leading-relaxed pl-6">{job.errorMessage}</p>
          </div>
        )}

        {/* Telemetry Metrics Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs font-mono">
          <div className="p-4 rounded-xl bg-[#EFF3F7] border border-[#D9E1EA] space-y-1">
            <span className="text-[#718096] flex items-center gap-1.5">
              <Cpu className="h-3.5 w-3.5 text-[#2563A8]" /> Worker Node
            </span>
            <p className="font-semibold text-[#17253A]">{job.workerNode || 'worker-01'}</p>
          </div>

          <div className="p-4 rounded-xl bg-[#EFF3F7] border border-[#D9E1EA] space-y-1">
            <span className="text-[#718096] flex items-center gap-1.5">
              <Layers className="h-3.5 w-3.5 text-[#2563A8]" /> Chunks Created
            </span>
            <p className="font-semibold text-[#17253A]">{job.chunksCount || '—'}</p>
          </div>

          <div className="p-4 rounded-xl bg-[#EFF3F7] border border-[#D9E1EA] space-y-1">
            <span className="text-[#718096] flex items-center gap-1.5">
              <GitFork className="h-3.5 w-3.5 text-[#2563A8]" /> Entities Extracted
            </span>
            <p className="font-semibold text-[#17253A]">{job.entitiesExtractedCount || '—'}</p>
          </div>

          <div className="p-4 rounded-xl bg-[#EFF3F7] border border-[#D9E1EA] space-y-1">
            <span className="text-[#718096] flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5 text-[#2563A8]" /> Timestamps
            </span>
            <p className="font-semibold text-[#17253A]">
              Started: {job.startedAt ? formatDate(job.startedAt) : '—'}
            </p>
            {job.completedAt && (
              <p className="text-[11px] text-[#526176]">Completed: {formatDate(job.completedAt)}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
