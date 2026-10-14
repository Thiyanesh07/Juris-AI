'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useDocumentStore } from '@/context/DocumentStoreContext';
import { Document } from '@/lib/types';
import { ProcessingJobSummary, ProcessingJob } from '@/lib/apiTypes';
import { ADMIN_ROUTES, ADMIN_DYNAMIC_ROUTES } from '@/constants/routes';
import { formatDate } from '@/lib/utils';
import { PageHeader } from '@/components/shared/PageHeader';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/shared/EmptyState';
import {
  ArrowLeft,
  RotateCcw,
  FileText,
  Cpu,
  CheckCircle2,
  AlertCircle,
  Clock,
  Layers,
  Activity,
  ExternalLink,
  RefreshCw,
} from 'lucide-react';

const PIPELINE_ORDER: { stage: string; label: string; desc: string }[] = [
  { stage: 'ingestion', label: 'Ingestion & Registration', desc: 'File validation and database registration' },
  { stage: 'extraction', label: 'Text Extraction', desc: 'PDF text and legal metadata parsing' },
  { stage: 'chunking', label: 'Structural Chunking', desc: 'Hierarchy-aware section segmentation' },
  { stage: 'embedding', label: 'InLegalBERT Embedding', desc: '768-dim legal dense vector generation' },
  { stage: 'vector_index', label: 'FAISS Vector Index', desc: 'Atomic incremental index synchronization' },
  { stage: 'entity_extraction', label: 'Legal Entity Extraction', desc: 'Courts, acts, statutes, and party identification' },
  { stage: 'relation_extraction', label: 'Relation Extraction', desc: 'Citations, amendments, and overrides extraction' },
  { stage: 'graph_population', label: 'Graph Population', desc: 'Neo4j knowledge graph topology commit' },
];

export default function IngestionJobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const targetId = params?.id as string;

  const { fetchJobDetail, reprocessDocument } = useDocumentStore();

  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [job, setJob] = useState<ProcessingJobSummary | null>(null);
  const [document, setDocument] = useState<Document | null>(null);
  const [stages, setStages] = useState<ProcessingJob[]>([]);
  const [isReprocessing, setIsReprocessing] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!targetId) return;
    setIsLoading(true);
    setLoadError(null);
    try {
      const res = await fetchJobDetail(targetId);
      if (!res.job && !res.document && res.stages?.length === 0) {
        setJob(null);
        setDocument(null);
        setStages([]);
      } else {
        setJob(res.job || null);
        setDocument(res.document || null);
        setStages(res.stages || []);
      }
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load job details');
    } finally {
      setIsLoading(false);
    }
  }, [targetId, fetchJobDetail]);

  useEffect(() => {
    if (!targetId) return;
    let active = true;
    fetchJobDetail(targetId)
      .then((res) => {
        if (!active) return;
        if (!res.job && !res.document && res.stages?.length === 0) {
          setJob(null);
          setDocument(null);
          setStages([]);
        } else {
          setJob(res.job || null);
          setDocument(res.document || null);
          setStages(res.stages || []);
        }
      })
      .catch((err) => {
        if (active) setLoadError(err instanceof Error ? err.message : 'Failed to load job details');
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [targetId, fetchJobDetail]);

  // Periodic refresh if any stage is running
  useEffect(() => {
    const hasRunningStage = stages.some((s) => s.status?.toLowerCase() === 'running');
    if (!hasRunningStage) return;

    const interval = setInterval(() => {
      if (typeof window !== 'undefined' && window.document.hidden) return;
      loadData();
    }, 4000);

    return () => clearInterval(interval);
  }, [stages, loadData]);

  const handleReprocess = async () => {
    const docId = document?.id || job?.document_id;
    if (!docId || isReprocessing) return;

    setIsReprocessing(true);
    setActionMessage(null);
    try {
      const res = await reprocessDocument(docId);
      setActionMessage(res.message || 'Pipeline reprocess initiated');
      await loadData();
    } catch (err) {
      setActionMessage(err instanceof Error ? err.message : 'Reprocess request failed');
    } finally {
      setIsReprocessing(false);
    }
  };

  const getStageStatus = (stageName: string): ProcessingJob | undefined => {
    return stages.find((s) => s.stage.toLowerCase() === stageName.toLowerCase());
  };

  const getStatusBadge = (status?: string) => {
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
        return <Badge variant="outline">Not Started</Badge>;
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6 max-w-4xl">
        <PageHeader
          title="Loading Ingestion Job..."
          subtitle="Fetching pipeline stage records from backend"
          actions={
            <Button variant="ghost" size="sm" onClick={() => router.push(ADMIN_ROUTES.INGESTION)}>
              <ArrowLeft className="h-4 w-4 mr-1.5" />
              Back to Ingestion
            </Button>
          }
        />
        <div className="p-12 text-center rounded-xl border border-[#C9D4E1] bg-white">
          <Activity className="h-6 w-6 text-[#2563A8] animate-spin mx-auto mb-2" />
          <p className="font-mono text-xs text-[#526176]">Retrieving job telemetry...</p>
        </div>
      </div>
    );
  }

  if (!job && !document && stages.length === 0) {
    return (
      <div className="space-y-6 max-w-3xl">
        <PageHeader
          title="Job Record Not Found"
          subtitle={`No ingestion job or document matching identifier "${targetId}" exists on the backend.`}
          actions={
            <Button variant="ghost" size="sm" onClick={() => router.push(ADMIN_ROUTES.INGESTION)}>
              <ArrowLeft className="h-4 w-4 mr-1.5" />
              Back to Ingestion
            </Button>
          }
        />
        <EmptyState
          title="Ingestion Record Not Found"
          description={
            loadError || 'The requested job identifier could not be verified in the PostgreSQL document store.'
          }
        />
      </div>
    );
  }

  const activeDocTitle = document?.title || job?.document_title || 'Legal Document';
  const activeDocId = document?.id || job?.document_id || '';
  const isDocumentProcessing = document?.status === 'PROCESSING';

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <PageHeader
        title={`Ingestion: ${activeDocTitle}`}
        subtitle={`Job / Document ID: ${targetId}`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => router.push(ADMIN_ROUTES.INGESTION)}>
              <ArrowLeft className="h-4 w-4 mr-1.5" />
              Back to Ingestion
            </Button>
            <Button variant="secondary" size="sm" onClick={loadData} disabled={isLoading}>
              <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            {activeDocId && (
              <Link href={ADMIN_DYNAMIC_ROUTES.DOCUMENT_DETAIL(activeDocId)}>
                <Button variant="secondary" size="sm">
                  <FileText className="h-3.5 w-3.5 mr-1.5" />
                  View Document
                </Button>
              </Link>
            )}
            <Button
              variant="primary"
              size="sm"
              disabled={isReprocessing || isDocumentProcessing}
              onClick={handleReprocess}
            >
              <RotateCcw className={`h-3.5 w-3.5 mr-1.5 ${isReprocessing ? 'animate-spin' : ''}`} />
              {isReprocessing ? 'Submitting Reprocess...' : 'Reprocess Ingestion'}
            </Button>
          </div>
        }
      />

      {/* Action Notification */}
      {actionMessage && (
        <div className="p-4 rounded-xl bg-[#D9E7F5] border border-[#B3D1EB] text-[#2563A8] text-xs font-mono flex items-center justify-between">
          <span>{actionMessage}</span>
          <button onClick={() => setActionMessage(null)} className="underline font-semibold ml-4">
            Dismiss
          </button>
        </div>
      )}

      {/* Main Overview Card */}
      <div className="p-6 rounded-2xl bg-white border border-[#C9D4E1] shadow-xs space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-[#D9E1EA] gap-4">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-[#2563A8] text-white shrink-0">
              <Cpu className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold font-serif text-[#17253A]">{activeDocTitle}</h2>
              {activeDocId && (
                <Link
                  href={ADMIN_DYNAMIC_ROUTES.DOCUMENT_DETAIL(activeDocId)}
                  className="text-xs font-mono text-[#2563A8] hover:underline flex items-center gap-1 mt-0.5"
                >
                  <span>Document ID: {activeDocId}</span>
                  <ExternalLink className="h-3 w-3" />
                </Link>
              )}
            </div>
          </div>

          <div>
            {document?.status ? (
              <Badge
                variant={
                  document.status === 'READY'
                    ? 'success'
                    : document.status === 'FAILED'
                    ? 'error'
                    : document.status === 'ARCHIVED'
                    ? 'outline'
                    : 'primary'
                }
                size="md"
              >
                Status: {document.status}
              </Badge>
            ) : job?.status ? (
              getStatusBadge(job.status)
            ) : null}
          </div>
        </div>

        {/* 8-Stage Pipeline Progression Table */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-mono font-bold text-[#17253A] uppercase tracking-wider">
              End-to-End Pipeline Stages (Persisted Audit Records)
            </h4>
            <span className="text-[11px] font-mono text-[#718096]">
              {stages.filter((s) => s.status?.toLowerCase() === 'completed').length} of {PIPELINE_ORDER.length} stages completed
            </span>
          </div>

          <div className="overflow-hidden rounded-xl border border-[#C9D4E1] bg-white">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-[#EFF3F7] border-b border-[#C9D4E1] font-mono text-xs font-bold text-[#526176] uppercase tracking-wider">
                  <th className="px-4 py-2.5">#</th>
                  <th className="px-4 py-2.5">Pipeline Stage</th>
                  <th className="px-4 py-2.5">Description</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5">Stage Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#D9E1EA]">
                {PIPELINE_ORDER.map((item, idx) => {
                  const stageRec = getStageStatus(item.stage);
                  const status = stageRec?.status || 'pending';
                  const isFailed = status.toLowerCase() === 'failed';

                  return (
                    <React.Fragment key={item.stage}>
                      <tr className={`hover:bg-[#EFF3F7]/50 transition-colors ${isFailed ? 'bg-[#F5D9D9]/20' : ''}`}>
                        <td className="px-4 py-3 font-mono font-semibold text-[#526176]">{idx + 1}</td>
                        <td className="px-4 py-3 font-semibold text-[#17253A]">{item.label}</td>
                        <td className="px-4 py-3 text-[#526176]">{item.desc}</td>
                        <td className="px-4 py-3">{getStatusBadge(stageRec ? stageRec.status : undefined)}</td>
                        <td className="px-4 py-3 font-mono text-[#718096]">
                          {stageRec?.updated_at ? formatDate(stageRec.updated_at) : '—'}
                        </td>
                      </tr>
                      {stageRec?.error && (
                        <tr className="bg-[#F5D9D9]/40 border-b border-[#E8B8B8]">
                          <td colSpan={5} className="px-4 py-2 text-[#8B2E2E] font-mono text-xs">
                            <div className="flex items-center gap-2">
                              <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                              <span className="font-semibold">Stage Error:</span>
                              <span>{stageRec.error}</span>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Telemetry Information Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs font-mono pt-2">
          <div className="p-4 rounded-xl bg-[#EFF3F7] border border-[#D9E1EA] space-y-1">
            <span className="text-[#718096] flex items-center gap-1.5">
              <Layers className="h-3.5 w-3.5 text-[#2563A8]" /> Document Details
            </span>
            <p className="font-semibold text-[#17253A] truncate">{document?.fileName || 'document.pdf'}</p>
            <p className="text-[11px] text-[#526176]">Type: {document?.documentType || 'Legal Text'}</p>
          </div>

          <div className="p-4 rounded-xl bg-[#EFF3F7] border border-[#D9E1EA] space-y-1">
            <span className="text-[#718096] flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5 text-[#2563A8]" /> Registration Timestamp
            </span>
            <p className="font-semibold text-[#17253A]">
              {document?.createdAt ? formatDate(document.createdAt) : job?.created_at ? formatDate(job.created_at) : '—'}
            </p>
            <p className="text-[11px] text-[#526176]">
              Last Modified: {document?.updatedAt ? formatDate(document.updatedAt) : '—'}
            </p>
          </div>

          <div className="p-4 rounded-xl bg-[#EFF3F7] border border-[#D9E1EA] space-y-1">
            <span className="text-[#718096] flex items-center gap-1.5">
              <Cpu className="h-3.5 w-3.5 text-[#2563A8]" /> Execution Target
            </span>
            <p className="font-semibold text-[#17253A]">Render Background Task</p>
            <p className="text-[11px] text-[#526176]">InLegalBERT + FAISS + Neo4j</p>
          </div>
        </div>
      </div>
    </div>
  );
}
