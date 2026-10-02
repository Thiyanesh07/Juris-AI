'use client';

/**
 * JURIS AI — ADMIN DASHBOARD (Phase 11 — Real Health Integration)
 *
 * Changes from Phase 10:
 *  - System Health section now calls GET /health in real-time
 *  - "API Gateway" status is derived from the actual /health response
 *  - "PostgreSQL DB" status comes from health.components.database
 *  - Neo4j, Vector Index, LLM remain NOT_CONNECTED (no backend health endpoints for them)
 *  - System Overview metrics remain "—" (no user/graph/validation count endpoints yet)
 *  - No fake production metrics are displayed
 */

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { PageHeader } from '@/components/shared/PageHeader';
import { MetricCard } from '@/components/shared/MetricCard';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { ADMIN_ROUTES } from '@/constants/routes';
import {
  Upload,
  CheckCircle2,
  Users,
  History,
  FileText,
  GitFork,
  CheckSquare,
  Server,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import { checkHealth, type HealthCheckResult } from '@/lib/health';

interface ServiceStatus {
  name: string;
  status: 'CONNECTED' | 'DEGRADED' | 'NOT_CONNECTED' | 'ERROR' | 'CHECKING';
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
  // NOT_CONNECTED
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
    { name: 'Neo4j Database', status: 'NOT_CONNECTED', type: 'Knowledge Graph' },
    { name: 'Vector Index', status: 'NOT_CONNECTED', type: 'FAISS Search' },
    { name: 'LLM Provider', status: 'NOT_CONNECTED', type: 'Inference Engine' },
  ]);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastChecked, setLastChecked] = useState<string | null>(null);

  async function refreshHealth() {
    setIsRefreshing(true);
    setServices((prev) =>
      prev.map((s) =>
        s.name === 'API Gateway' || s.name === 'PostgreSQL DB'
          ? { ...s, status: 'CHECKING' }
          : s,
      ),
    );

    try {
      const result: HealthCheckResult = await checkHealth();

      setServices((prev) =>
        prev.map((s) => {
          if (s.name === 'API Gateway') {
            return {
              ...s,
              status: result.status === 'NOT_CONNECTED' ? 'NOT_CONNECTED'
                : result.status === 'ERROR' ? 'ERROR'
                : 'CONNECTED',
              detail: result.detail,
            };
          }
          if (s.name === 'PostgreSQL DB') {
            if (result.raw) {
              const dbStatus = result.raw.components?.database?.status;
              return {
                ...s,
                status: dbStatus === 'ok' ? 'CONNECTED'
                  : dbStatus === 'unreachable' ? 'NOT_CONNECTED'
                  : result.status === 'NOT_CONNECTED' ? 'NOT_CONNECTED'
                  : 'ERROR',
                detail: result.raw.components?.database?.error ?? undefined,
              };
            }
            // Backend unreachable — DB also unreachable
            return { ...s, status: result.status === 'NOT_CONNECTED' ? 'NOT_CONNECTED' : 'ERROR' };
          }
          return s;
        }),
      );
      setLastChecked(new Date().toLocaleTimeString());
    } catch {
      setServices((prev) =>
        prev.map((s) =>
          s.name === 'API Gateway' || s.name === 'PostgreSQL DB'
            ? { ...s, status: 'ERROR' }
            : s,
        ),
      );
    } finally {
      setIsRefreshing(false);
    }
  }

  useEffect(() => {
    refreshHealth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-8">
      {/* Header */}
      <PageHeader
        title="Admin Dashboard"
        subtitle="Manage and monitor the Juris AI legal intelligence platform."
        actions={
          <div className="flex flex-wrap items-center gap-2">
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

      {/* Quick Action Navigation Bar */}
      <div className="p-4 rounded-xl bg-[#F5F7FA] border border-[#C9D4E1] shadow-[0_2px_4px_rgba(23,37,58,0.04)] flex flex-wrap items-center justify-between gap-3">
        <span className="text-xs font-mono font-bold uppercase tracking-wider text-[#526176]">
          Quick Actions:
        </span>
        <div className="flex flex-wrap items-center gap-2.5">
          <Link href={ADMIN_ROUTES.DOCUMENTS}>
            <Button variant="secondary" size="sm" className="text-xs">
              <FileText className="h-3.5 w-3.5 mr-1.5 text-[#526176]" />
              Upload Document
            </Button>
          </Link>
          <Link href={ADMIN_ROUTES.VALIDATION}>
            <Button variant="secondary" size="sm" className="text-xs">
              <CheckSquare className="h-3.5 w-3.5 mr-1.5 text-[#526176]" />
              View Validation Queue
            </Button>
          </Link>
          <Link href={ADMIN_ROUTES.USERS}>
            <Button variant="secondary" size="sm" className="text-xs">
              <Users className="h-3.5 w-3.5 mr-1.5 text-[#526176]" />
              Manage Users
            </Button>
          </Link>
          <Link href={ADMIN_ROUTES.AUDIT}>
            <Button variant="secondary" size="sm" className="text-xs">
              <History className="h-3.5 w-3.5 mr-1.5 text-[#526176]" />
              View Audit Logs
            </Button>
          </Link>
        </div>
      </div>

      {/* System Overview Cards (honest development states) */}
      <section className="space-y-3">
        <h3 className="text-sm font-mono font-bold text-[#17253A] uppercase tracking-wider">
          System Overview
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label="Documents"
            value="—"
            icon={<FileText className="h-4 w-4" />}
            footerText="Backend endpoint pending user count"
          />
          <MetricCard
            label="Knowledge Graph"
            value="—"
            icon={<GitFork className="h-4 w-4" />}
            footerText="No graph count endpoint yet"
          />
          <MetricCard
            label="Validation Queue"
            value="—"
            icon={<CheckCircle2 className="h-4 w-4" />}
            footerText="No validation count endpoint yet"
          />
          <MetricCard
            label="Users"
            value="—"
            icon={<Users className="h-4 w-4" />}
            footerText="No users list endpoint yet"
          />
        </div>
      </section>

      {/* Grid: System Health & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* System Health Section — Real backend connectivity */}
        <div className="lg:col-span-7 p-6 rounded-xl bg-[#F5F7FA] border border-[#C9D4E1] shadow-[0_2px_4px_rgba(23,37,58,0.04)] space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#D9E1EA]">
            <div className="flex items-center gap-2">
              <Server className="h-4 w-4 text-[#2563A8]" />
              <h3 className="text-sm font-mono font-bold text-[#17253A] uppercase tracking-wider">
                System Health
              </h3>
            </div>
            <div className="flex items-center gap-2">
              {lastChecked && (
                <span className="text-[10px] font-mono text-[#718096]">
                  Last checked: {lastChecked}
                </span>
              )}
              <button
                onClick={refreshHealth}
                disabled={isRefreshing}
                className="p-1.5 rounded-md bg-[#EFF3F7] border border-[#D9E1EA] text-[#526176] hover:bg-[#D9E7F5] transition-colors disabled:opacity-50"
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
                <div className="flex items-center gap-2.5">
                  <span className="font-semibold text-[#17253A]">{svc.name}</span>
                  <span className="text-[10px] text-[#718096]">({svc.type})</span>
                  {svc.detail && svc.status !== 'CONNECTED' && (
                    <span className="text-[10px] text-[#718096] italic truncate max-w-[120px]" title={svc.detail}>
                      — {svc.detail}
                    </span>
                  )}
                </div>
                <StatusPill status={svc.status} />
              </div>
            ))}
          </div>

          <p className="text-[10px] font-mono text-[#718096] pt-1">
            API Gateway and PostgreSQL reflect real backend connectivity.
            Neo4j, FAISS, and LLM status require dedicated health endpoints (pending Phase 12+).
          </p>
        </div>

        {/* Recent Activity Section (Empty / Development State) */}
        <div className="lg:col-span-5 p-6 rounded-xl bg-[#F5F7FA] border border-[#C9D4E1] shadow-[0_2px_4px_rgba(23,37,58,0.04)] flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 pb-3 border-b border-[#D9E1EA]">
              <History className="h-4 w-4 text-[#2563A8]" />
              <h3 className="text-sm font-mono font-bold text-[#17253A] uppercase tracking-wider">
                Recent Activity
              </h3>
              <Badge variant="outline" size="sm">
                <span className="flex items-center gap-1.5 text-[#718096]">
                  <AlertCircle className="h-3 w-3" />
                  Pending Integration
                </span>
              </Badge>
            </div>

            <div className="my-8 text-center p-6 rounded-lg bg-[#EFF3F7] border border-[#D9E1EA]">
              <div className="p-3 rounded-full bg-[#D9E7F5] text-[#2563A8] w-fit mx-auto mb-3">
                <History className="h-5 w-5" />
              </div>
              <p className="text-xs font-semibold text-[#17253A]">No activity yet.</p>
              <p className="text-xs text-[#526176] mt-1 leading-relaxed">
                Administrative events will appear here once the audit endpoint is implemented.
              </p>
            </div>
          </div>

          <div className="pt-3 border-t border-[#D9E1EA] text-[11px] font-mono text-[#718096] text-center">
            Audit logging service pending backend implementation
          </div>
        </div>
      </div>
    </div>
  );
}
