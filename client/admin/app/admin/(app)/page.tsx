'use client';

/**
 * JURIS AI — ADMIN DASHBOARD (Production MVP)
 *
 * Displays live, real-time connectivity and metric statistics from FastAPI backend,
 * Neo4j Aura, FAISS Vector Index, and PostgreSQL.
 * Never displays hardcoded fallback values.
 */

import React, { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { PageHeader } from '@/components/shared/PageHeader';
import { MetricCard } from '@/components/shared/MetricCard';
import { Button } from '@/components/ui/Button';
import { ADMIN_ROUTES } from '@/constants/routes';
import {
  Upload,
  CheckCircle2,
  History,
  FileText,
  GitFork,
  Server,
  RefreshCw,
  Cpu,
  Layers,
  Activity,
  AlertCircle,
} from 'lucide-react';
import { checkHealth, fetchPublicStats, type HealthCheckResult } from '@/lib/health';
import { apiClient } from '@/lib/apiClient';
import { PublicStatsResponse } from '@/lib/apiTypes';

interface ServiceStatus {
  name: string;
  status: 'CONNECTED' | 'DEGRADED' | 'NOT_CONNECTED' | 'ERROR' | 'CHECKING' | 'CONFIGURED';
  type: string;
  detail?: string;
}

function StatusPill({ status }: { status: ServiceStatus['status'] }) {
  if (status === 'CHECKING') {
    return (
      <span className="text-[#526176] bg-[#E7EDF4] px-2 py-0.5 rounded text-[11px] font-medium border border-[#C9D4E1] flex items-center gap-1">
        <RefreshCw className="h-2.5 w-2.5 animate-spin" />
        Checking…
      </span>
    );
  }
  if (status === 'CONNECTED') {
    return (
      <span className="text-[#1A6B3A] bg-[#D6F0E0] px-2 py-0.5 rounded text-[11px] font-medium border border-[#A8D5B8]">
        Connected
      </span>
    );
  }
  if (status === 'CONFIGURED') {
    return (
      <span className="text-[#1D4ED8] bg-[#DBEAFE] px-2 py-0.5 rounded text-[11px] font-medium border border-[#93C5FD]">
        Configured
      </span>
    );
  }
  if (status === 'DEGRADED') {
    return (
      <span className="text-[#8B5E0A] bg-[#FEF3C7] px-2 py-0.5 rounded text-[11px] font-medium border border-[#F9D979]">
        Degraded
      </span>
    );
  }
  if (status === 'ERROR') {
    return (
      <span className="text-[#8B2E2E] bg-[#F5D9D9] px-2 py-0.5 rounded text-[11px] font-medium border border-[#E8B8B8]">
        Error
      </span>
    );
  }
  return (
    <span className="text-[#8B2E2E] bg-[#F5D9D9] px-2 py-0.5 rounded text-[11px] font-medium border border-[#E8B8B8]">
      Not Connected
    </span>
  );
}

export default function AdminDashboardPage() {
  const [services, setServices] = useState<ServiceStatus[]>([
    { name: 'API Gateway', status: 'CHECKING', type: 'FastAPI REST' },
    { name: 'PostgreSQL DB', status: 'CHECKING', type: 'Relational Store' },
    { name: 'Neo4j Database', status: 'CHECKING', type: 'Knowledge Graph' },
    { name: 'Vector Index', status: 'CHECKING', type: 'FAISS Search' },
    { name: 'LLM Provider', status: 'CHECKING', type: 'Inference Engine' },
  ]);
  const [stats, setStats] = useState<PublicStatsResponse | null>(null);
  const [statsLoading, setStatsLoading] = useState<boolean>(true);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [auditEvents, setAuditEvents] = useState<any[]>([]);
  const [auditError, setAuditError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastChecked, setLastChecked] = useState<string | null>(null);

  const refreshHealthAndStats = useCallback(async () => {
    setIsRefreshing(true);
    setStatsLoading(true);
    setStatsError(null);
    setAuditError(null);
    setServices((prev) => prev.map((s) => ({ ...s, status: 'CHECKING' })));

    try {
      const [healthResult, statsData, auditRes] = await Promise.all([
        checkHealth(),
        fetchPublicStats(),
        apiClient
          .get<{ items: any[] }>('/audit?page_size=5')
          .catch((err) => {
            setAuditError(err instanceof Error ? err.message : 'Audit unavailable');
            return { items: [] };
          }),
      ]);

      if (statsData) {
        setStats(statsData);
      } else {
        setStats(null);
        setStatsError('Public telemetry endpoint unavailable');
      }

      setAuditEvents(auditRes.items || []);

      const comps = healthResult.raw?.components;

      setServices([
        {
          name: 'API Gateway',
          status: healthResult.status === 'NOT_CONNECTED' ? 'NOT_CONNECTED' : 'CONNECTED',
          type: 'FastAPI REST',
          detail: healthResult.raw ? `v${healthResult.raw.version} Production API` : healthResult.detail,
        },
        {
          name: 'PostgreSQL DB',
          status: comps?.database?.status === 'ok' ? 'CONNECTED' : 'ERROR',
          type: 'Relational Store',
          detail:
            comps?.database?.detail ||
            (statsData
              ? `${statsData.total_documents} documents, ${statsData.total_chunks} chunks`
              : comps?.database?.error || 'PostgreSQL unreachable'),
        },
        {
          name: 'Neo4j Database',
          status:
            comps?.neo4j?.status === 'ok'
              ? 'CONNECTED'
              : comps?.neo4j?.status === 'degraded'
              ? 'DEGRADED'
              : 'ERROR',
          type: 'Neo4j Aura Cloud',
          detail:
            comps?.neo4j?.detail ||
            (statsData
              ? `${statsData.graph_nodes.toLocaleString()} nodes, ${statsData.graph_relationships.toLocaleString()} rels`
              : comps?.neo4j?.error || 'Neo4j connection unreachable'),
        },
        {
          name: 'Vector Index',
          status: comps?.vector_index?.status === 'ok' ? 'CONNECTED' : 'ERROR',
          type: 'FAISS IndexFlatIP',
          detail:
            comps?.vector_index?.detail ||
            (statsData
              ? `${statsData.vector_count.toLocaleString()} vectors (${statsData.vector_dimension}d)`
              : comps?.vector_index?.error || 'Vector index unavailable'),
        },
        {
          name: 'LLM Provider',
          status:
            comps?.llm?.status === 'ok'
              ? (comps?.llm?.metrics?.verified_live ? 'CONNECTED' : 'CONFIGURED')
              : 'DEGRADED',
          type: 'Legal AI Reasoning Engine',
          detail: comps?.llm?.detail || comps?.llm?.error || 'Provider unconfigured',
        },
      ]);
      setLastChecked(new Date().toLocaleTimeString());
    } catch (err) {
      setStats(null);
      setStatsError(err instanceof Error ? err.message : 'Failed to query system health');
      setServices((prev) =>
        prev.map((s) => ({
          ...s,
          status: 'ERROR',
          detail: 'System check failed',
        }))
      );
    } finally {
      setIsRefreshing(false);
      setStatsLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [healthResult, statsData, auditRes] = await Promise.all([
          checkHealth(),
          fetchPublicStats(),
          apiClient
            .get<{ items: any[] }>('/audit?page_size=5')
            .catch((err) => {
              if (active) setAuditError(err instanceof Error ? err.message : 'Audit unavailable');
              return { items: [] };
            }),
        ]);

        if (!active) return;
        if (statsData) {
          setStats(statsData);
        } else {
          setStats(null);
          setStatsError('Public telemetry endpoint unavailable');
        }

        setAuditEvents(auditRes.items || []);

        const comps = healthResult.raw?.components;

        setServices([
          {
            name: 'API Gateway',
            status: healthResult.status === 'NOT_CONNECTED' ? 'NOT_CONNECTED' : 'CONNECTED',
            type: 'FastAPI REST',
            detail: healthResult.raw ? `v${healthResult.raw.version} Production API` : healthResult.detail,
          },
          {
            name: 'PostgreSQL DB',
            status: comps?.database?.status === 'ok' ? 'CONNECTED' : 'ERROR',
            type: 'Relational Store',
            detail:
              comps?.database?.detail ||
              (statsData
                ? `${statsData.total_documents} documents, ${statsData.total_chunks} chunks`
                : comps?.database?.error || 'PostgreSQL unreachable'),
          },
          {
            name: 'Neo4j Database',
            status:
              comps?.neo4j?.status === 'ok'
                ? 'CONNECTED'
                : comps?.neo4j?.status === 'degraded'
                ? 'DEGRADED'
                : 'ERROR',
            type: 'Neo4j Aura Cloud',
            detail:
              comps?.neo4j?.detail ||
              (statsData
                ? `${statsData.graph_nodes.toLocaleString()} nodes, ${statsData.graph_relationships.toLocaleString()} rels`
                : comps?.neo4j?.error || 'Neo4j connection unreachable'),
          },
          {
            name: 'Vector Index',
            status: comps?.vector_index?.status === 'ok' ? 'CONNECTED' : 'ERROR',
            type: 'FAISS IndexFlatIP',
            detail:
              comps?.vector_index?.detail ||
              (statsData
                ? `${statsData.vector_count.toLocaleString()} vectors (${statsData.vector_dimension}d)`
                : comps?.vector_index?.error || 'Vector index unavailable'),
          },
          {
            name: 'LLM Provider',
            status:
              comps?.llm?.status === 'ok'
                ? (comps?.llm?.metrics?.verified_live ? 'CONNECTED' : 'CONFIGURED')
                : 'DEGRADED',
            type: 'Legal AI Reasoning Engine',
            detail: comps?.llm?.detail || comps?.llm?.error || 'Provider unconfigured',
          },
        ]);
        setLastChecked(new Date().toLocaleTimeString());
      } catch (err) {
        if (!active) return;
        setStats(null);
        setStatsError(err instanceof Error ? err.message : 'Failed to query system health');
        setServices((prev) =>
          prev.map((s) => ({
            ...s,
            status: 'ERROR',
            detail: 'System check failed',
          }))
        );
      } finally {
        if (active) {
          setIsRefreshing(false);
          setStatsLoading(false);
        }
      }
    })();

    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="space-y-8">
      {/* Header */}
      <PageHeader
        title="Admin Dashboard"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={refreshHealthAndStats}
              disabled={isRefreshing}
            >
              <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${isRefreshing ? 'animate-spin' : ''}`} />
              Refresh Status
            </Button>
            <Link href={ADMIN_ROUTES.DOCUMENTS}>
              <Button variant="primary" size="sm">
                <Upload className="h-3.5 w-3.5 mr-1.5" />
                Upload Document
              </Button>
            </Link>
            <Link href={ADMIN_ROUTES.VALIDATION}>
              <Button variant="secondary" size="sm">
                <CheckCircle2 className="h-3.5 w-3.5 mr-1.5 text-[#2563A8]" />
                View Validation Queue
              </Button>
            </Link>
          </div>
        }
      />

      {/* Telemetry Error Banner */}
      {statsError && (
        <div className="p-4 rounded-xl bg-[#F5D9D9] border border-[#E8B8B8] text-[#8B2E2E] flex items-center justify-between text-xs font-mono">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>Corpus telemetry unavailable: {statsError}</span>
          </div>
          <Button variant="secondary" size="sm" onClick={refreshHealthAndStats}>
            Retry Request
          </Button>
        </div>
      )}

      {/* Verified System Overview Metrics */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-mono font-bold text-[#17253A] uppercase tracking-wider">
            Verified Corpus & Graph Metrics
          </h3>
          <span className="text-[11px] font-mono text-[#718096]">
            {statsLoading ? 'Querying backend stats…' : stats ? 'Live Database Persisted' : 'Offline / Unavailable'}
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label="Total Documents"
            value={stats ? `${stats.total_documents}` : statsLoading ? 'Loading…' : '—'}
            icon={<FileText className="h-4 w-4 text-[#1D4E8A]" />}
            footerText={
              stats
                ? `${stats.ready_documents} Ready for retrieval`
                : statsLoading
                ? 'Fetching document count…'
                : 'Corpus stats unavailable'
            }
          />
          <MetricCard
            label="Knowledge Graph Nodes"
            value={stats ? `${stats.graph_nodes.toLocaleString()}` : statsLoading ? 'Loading…' : '—'}
            icon={<GitFork className="h-4 w-4 text-[#1D4E8A]" />}
            footerText={
              stats
                ? `${stats.graph_relationships.toLocaleString()} Relationships`
                : statsLoading
                ? 'Fetching graph metrics…'
                : 'Graph stats unavailable'
            }
          />
          <MetricCard
            label="FAISS Vectors"
            value={stats ? `${stats.vector_count.toLocaleString()}` : statsLoading ? 'Loading…' : '—'}
            icon={<Cpu className="h-4 w-4 text-[#1D4E8A]" />}
            footerText={
              stats
                ? `${stats.vector_dimension}d (${stats.embedding_model})`
                : statsLoading
                ? 'Loading index status…'
                : 'Vector stats unavailable'
            }
          />
          <MetricCard
            label="Indexed Chunks"
            value={stats ? `${stats.total_chunks.toLocaleString()}` : statsLoading ? 'Loading…' : '—'}
            icon={<Layers className="h-4 w-4 text-[#1D4E8A]" />}
            footerText={
              stats
                ? 'PostgreSQL ↔ FAISS ↔ Graph synced'
                : statsLoading
                ? 'Checking chunk sync…'
                : 'Chunk stats unavailable'
            }
          />
        </div>
      </section>

      {/* Grid: System Health & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* System Health Section */}
        <div className="lg:col-span-7 p-6 rounded-xl bg-[#F5F7FA] border border-[#C9D4E1] shadow-[0_2px_4px_rgba(23,37,58,0.04)] space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#D9E1EA]">
            <div className="flex items-center gap-2">
              <Server className="h-4 w-4 text-[#2563A8]" />
              <h3 className="text-sm font-mono font-bold text-[#17253A] uppercase tracking-wider">
                System Infrastructure Health
              </h3>
            </div>
            <div className="flex items-center gap-2">
              {lastChecked && (
                <span className="text-[10px] font-mono text-[#718096]">
                  Last checked: {lastChecked}
                </span>
              )}
              <button
                onClick={refreshHealthAndStats}
                disabled={isRefreshing}
                className="p-1.5 rounded-md bg-[#EFF3F7] border border-[#D9E1EA] text-[#526176] hover:bg-[#D9E7F5] transition-colors disabled:opacity-50 cursor-pointer"
                title="Refresh health status"
              >
                <RefreshCw className={`h-3 w-3 ${isRefreshing ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>

          <div className="space-y-2.5">
            {services.map((svc) => (
              <div
                key={svc.name}
                className="flex items-center justify-between p-3 rounded-lg bg-[#EFF3F7] border border-[#D9E1EA] text-xs font-mono"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className="font-semibold text-[#17253A] shrink-0">{svc.name}</span>
                  <span className="text-[10px] text-[#718096] shrink-0">({svc.type})</span>
                  {svc.detail && (
                    <span className="text-[10px] text-[#1D4E8A] truncate max-w-[200px]" title={svc.detail}>
                      — {svc.detail}
                    </span>
                  )}
                </div>
                <StatusPill status={svc.status} />
              </div>
            ))}
          </div>
        </div>

        {/* Recent Audit Activity Section */}
        <div className="lg:col-span-5 p-6 rounded-xl bg-[#F5F7FA] border border-[#C9D4E1] shadow-[0_2px_4px_rgba(23,37,58,0.04)] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-[#D9E1EA]">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-[#2563A8]" />
                <h3 className="text-sm font-mono font-bold text-[#17253A] uppercase tracking-wider">
                  Recent Audit Logs
                </h3>
              </div>
              <Link href={ADMIN_ROUTES.AUDIT} className="text-[11px] font-mono text-[#2563A8] hover:underline">
                View all →
              </Link>
            </div>

            {auditError ? (
              <div className="my-6 text-center p-6 rounded-lg bg-[#EFF3F7] border border-[#D9E1EA]">
                <AlertCircle className="h-5 w-5 text-[#8B2E2E] mx-auto mb-2" />
                <p className="text-xs font-semibold text-[#8B2E2E]">Unable to load recent audit activity.</p>
                <p className="text-xs text-[#526176] mt-1">{auditError}</p>
              </div>
            ) : auditEvents.length === 0 ? (
              <div className="my-6 text-center p-6 rounded-lg bg-[#EFF3F7] border border-[#D9E1EA]">
                <History className="h-5 w-5 text-[#2563A8] mx-auto mb-2" />
                <p className="text-xs font-semibold text-[#17253A]">No audit events logged yet.</p>
                <p className="text-xs text-[#526176] mt-1">
                  Administrative actions will appear here.
                </p>
              </div>
            ) : (
              <div className="space-y-2 mt-3">
                {auditEvents.slice(0, 4).map((event) => (
                  <div key={event.id} className="p-2.5 rounded-lg bg-[#EFF3F7] border border-[#D9E1EA] text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-[#17253A] text-[11px]">{event.event_type}</span>
                      <span className="text-[10px] font-mono text-[#718096]">
                        {event.created_at ? new Date(event.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}
                      </span>
                    </div>
                    <p className="text-[11px] text-[#526176] line-clamp-1">
                      {event.actor_email || 'System'} — {event.event_metadata?.description || event.target_resource || 'Action executed'}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
