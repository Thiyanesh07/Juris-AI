'use client';

import React, { useState, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuditStore } from '@/context/AuditStoreContext';
import { AuditEvent, AuditCategory, AuditActionResult, AuditSeverity } from '@/lib/types';
import { formatDate } from '@/lib/utils';
import { PageHeader } from '@/components/shared/PageHeader';
import { FilterBar } from '@/components/shared/FilterBar';
import { MetricCard } from '@/components/shared/MetricCard';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { EmptyState } from '@/components/shared/EmptyState';
import {
  ShieldAlert,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Eye,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  UserCheck,
  FileText,
  Cpu,
  GitFork,
  CheckSquare,
  Lock,
  ArrowUpDown,
  Filter,
  Activity,
  Layers,
} from 'lucide-react';

export default function AuditLogsPage() {
  const router = useRouter();
  const {
    filteredEvents,
    searchQuery,
    setSearchQuery,
    categoryFilter,
    setCategoryFilter,
    resultFilter,
    setResultFilter,
    actorFilter,
    setActorFilter,
    dateRangeFilter,
    setDateRangeFilter,
    sortOrder,
    setSortOrder,
    resetFilters,
    uniqueActors,
    metrics,
  } = useAuditStore();

  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  const totalPages = Math.ceil(filteredEvents.length / pageSize) || 1;
  const paginatedEvents = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredEvents.slice(start, start + pageSize);
  }, [filteredEvents, currentPage, pageSize]);

  const getResultBadge = (result: AuditActionResult) => {
    switch (result) {
      case 'SUCCESS':
        return <Badge variant="success">Success</Badge>;
      case 'FAILURE':
        return <Badge variant="error">Failure</Badge>;
      case 'WARNING':
        return <Badge variant="warning">Warning</Badge>;
      default:
        return <Badge variant="default">{result}</Badge>;
    }
  };

  const getSeverityBadge = (severity: AuditSeverity) => {
    switch (severity) {
      case 'ERROR':
        return <Badge variant="error">ERROR</Badge>;
      case 'WARNING':
        return <Badge variant="warning">WARN</Badge>;
      case 'INFO':
      default:
        return <Badge variant="outline">INFO</Badge>;
    }
  };

  const getCategoryIcon = (category: AuditCategory) => {
    switch (category) {
      case 'AUTHENTICATION':
        return <Lock className="h-3.5 w-3.5 text-[#2563A8]" />;
      case 'USER_MANAGEMENT':
        return <UserCheck className="h-3.5 w-3.5 text-[#2563A8]" />;
      case 'ADMIN_MANAGEMENT':
        return <ShieldCheck className="h-3.5 w-3.5 text-[#2563A8]" />;
      case 'DOCUMENT':
        return <FileText className="h-3.5 w-3.5 text-[#2563A8]" />;
      case 'INGESTION':
        return <Cpu className="h-3.5 w-3.5 text-[#2563A8]" />;
      case 'KNOWLEDGE_GRAPH':
        return <GitFork className="h-3.5 w-3.5 text-[#2563A8]" />;
      case 'VALIDATION':
        return <CheckSquare className="h-3.5 w-3.5 text-[#2563A8]" />;
      case 'SECURITY':
        return <ShieldAlert className="h-3.5 w-3.5 text-[#8B2E2E]" />;
      case 'SYSTEM':
      default:
        return <Activity className="h-3.5 w-3.5 text-[#526176]" />;
    }
  };

  const getResourceLink = (event: AuditEvent) => {
    if (!event.resourceType || !event.resourceId) return null;

    switch (event.resourceType) {
      case 'Document':
        return `/admin/documents/${event.resourceId}`;
      case 'User':
        return `/admin/users/${event.resourceId}`;
      case 'Admin':
        return `/admin/admins/${event.resourceId}`;
      case 'IngestionJob':
        return `/admin/ingestion/${event.resourceId}`;
      case 'ValidationItem':
        return `/admin/validation/${event.resourceId}`;
      case 'GraphEntity':
        return `/admin/graph`;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Audit Logs"
        subtitle="Review administrative activity and system events across the Juris AI platform."
      />

      {/* Audit Immutability & Compliance Callout Banner */}
      <div className="p-4 rounded-xl bg-white border border-[#C9D4E1] shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-[#1E6B45]" />
          <span className="font-bold text-[#17253A]">Audit Traceability Notice:</span>
          <span className="text-[#526176]">
            Audit logs are read-only and immutably recorded for compliance and security auditability.
          </span>
        </div>
        <div className="flex items-center gap-2 text-[#718096]">
          <span className="px-2 py-0.5 rounded bg-[#EFF3F7] text-[#17253A] font-bold">
            Development Environment Data
          </span>
        </div>
      </div>

      {/* Summary Telemetry Cards */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono font-bold text-[#17253A] uppercase tracking-wider">
            Audit Activity Telemetry (Mock Environment)
          </span>
          <span className="text-[11px] font-mono text-[#718096]">Development Data Only</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label="Total Recorded Events"
            value={metrics.total}
            icon={<Activity className="h-4 w-4" />}
            footerText="Audit event log size"
          />
          <MetricCard
            label="Successful Operations"
            value={metrics.success}
            icon={<CheckCircle2 className="h-4 w-4 text-[#1E6B45]" />}
            footerText="Normal administrative execution"
          />
          <MetricCard
            label="Failed / Flagged Events"
            value={metrics.failure}
            icon={<XCircle className="h-4 w-4 text-[#8B2E2E]" />}
            footerText="Failed logins & job errors"
          />
          <MetricCard
            label="Recorded Today"
            value={metrics.today}
            icon={<Clock className="h-4 w-4" />}
            footerText="Activity in 24-hour window"
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
        placeholder="Search by actor, action, resource, IP, or description..."
        onReset={() => {
          resetFilters();
          setCurrentPage(1);
        }}
        filters={
          <>
            {/* Category Filter */}
            <Select
              density="dense"
              value={categoryFilter}
              onChange={(e) => {
                setCategoryFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-38 bg-white text-xs"
            >
              <option value="ALL">All Categories</option>
              <option value="AUTHENTICATION">Authentication</option>
              <option value="USER_MANAGEMENT">User Mgt</option>
              <option value="ADMIN_MANAGEMENT">Admin Mgt</option>
              <option value="DOCUMENT">Document</option>
              <option value="INGESTION">Ingestion</option>
              <option value="KNOWLEDGE_GRAPH">Graph</option>
              <option value="VALIDATION">Validation</option>
              <option value="SYSTEM">System</option>
              <option value="SECURITY">Security</option>
            </Select>

            {/* Result Filter */}
            <Select
              density="dense"
              value={resultFilter}
              onChange={(e) => {
                setResultFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-32 bg-white text-xs"
            >
              <option value="ALL">All Results</option>
              <option value="SUCCESS">Success</option>
              <option value="FAILURE">Failure</option>
              <option value="WARNING">Warning</option>
            </Select>

            {/* Actor Filter */}
            <Select
              density="dense"
              value={actorFilter}
              onChange={(e) => {
                setActorFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-40 bg-white text-xs"
            >
              <option value="ALL">All Actors</option>
              {uniqueActors.map((actor) => (
                <option key={actor.id} value={actor.id}>
                  {actor.name}
                </option>
              ))}
            </Select>

            {/* Date Range Filter */}
            <Select
              density="dense"
              value={dateRangeFilter}
              onChange={(e) => {
                setDateRangeFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-32 bg-white text-xs"
            >
              <option value="ALL">All Time</option>
              <option value="TODAY">Today</option>
              <option value="7DAYS">Last 7 Days</option>
              <option value="30DAYS">Last 30 Days</option>
            </Select>

            {/* Sort Toggle */}
            <Select
              density="dense"
              value={sortOrder}
              onChange={(e) => {
                setSortOrder(e.target.value as 'NEWEST' | 'OLDEST');
                setCurrentPage(1);
              }}
              className="w-36 bg-white text-xs font-mono"
            >
              <option value="NEWEST">Newest First</option>
              <option value="OLDEST">Oldest First</option>
            </Select>
          </>
        }
      />

      {/* Main Audit List Content */}
      {filteredEvents.length === 0 ? (
        <EmptyState
          title="No audit events found"
          description="No administrative activity matches your current search or active filters."
          action={
            <Button variant="secondary" size="sm" onClick={resetFilters}>
              Reset Filters
            </Button>
          }
        />
      ) : (
        <div className="space-y-4">
          {/* DESKTOP AUDIT TABLE */}
          <div className="hidden lg:block w-full overflow-hidden rounded-xl border border-[#C9D4E1] bg-white shadow-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm border-collapse">
                <thead>
                  <tr className="bg-[#EFF3F7] border-b border-[#C9D4E1] font-mono text-xs font-bold text-[#526176] uppercase tracking-wider">
                    <th className="px-4 py-3">Timestamp</th>
                    <th className="px-4 py-3">Actor</th>
                    <th className="px-4 py-3">Action</th>
                    <th className="px-4 py-3">Category</th>
                    <th className="px-4 py-3">Resource / Target</th>
                    <th className="px-4 py-3">Result</th>
                    <th className="px-4 py-3">Severity</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#D9E1EA]">
                  {paginatedEvents.map((evt) => {
                    const resourceLink = getResourceLink(evt);
                    return (
                      <tr
                        key={evt.id}
                        onClick={() => router.push(`/admin/audit/${evt.id}`)}
                        className="hover:bg-[#EFF3F7]/50 transition-colors cursor-pointer"
                      >
                        <td className="px-4 py-3.5 font-mono text-xs text-[#17253A] whitespace-nowrap">
                          {formatDate(evt.timestamp)}
                        </td>
                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-2">
                            <div className="h-7 w-7 rounded-full bg-[#D9E7F5] border border-[#B5D3EE] text-[#2563A8] font-mono text-xs font-bold flex items-center justify-center shrink-0">
                              {evt.actorName
                                .split(' ')
                                .map((n) => n[0])
                                .join('')
                                .substring(0, 2)}
                            </div>
                            <div className="flex flex-col max-w-[140px]">
                              <span className="font-semibold text-[#17253A] text-xs truncate">
                                {evt.actorName}
                              </span>
                              <span className="text-[10px] font-mono text-[#718096] truncate">
                                {evt.actorRole}
                              </span>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3.5">
                          <span className="font-mono text-xs font-bold text-[#17253A]">
                            {evt.action}
                          </span>
                        </td>
                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-1 text-xs font-mono text-[#526176]">
                            {getCategoryIcon(evt.category)}
                            <span className="text-[11px]">{evt.category}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3.5 text-xs max-w-[160px] truncate" onClick={(e) => e.stopPropagation()}>
                          {evt.resourceName ? (
                            resourceLink ? (
                              <Link
                                href={resourceLink}
                                className="hover:text-[#2563A8] hover:underline font-mono text-[11px] text-[#2563A8] truncate block"
                              >
                                {evt.resourceName}
                              </Link>
                            ) : (
                              <span className="font-mono text-[11px] text-[#526176] truncate block">
                                {evt.resourceName}
                              </span>
                            )
                          ) : (
                            <span className="text-[#718096] font-mono text-[11px]">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3.5 font-mono text-xs">
                          {getResultBadge(evt.result)}
                        </td>
                        <td className="px-4 py-3.5 font-mono text-xs">
                          {getSeverityBadge(evt.severity)}
                        </td>
                        <td className="px-4 py-3.5 text-right" onClick={(e) => e.stopPropagation()}>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => router.push(`/admin/audit/${evt.id}`)}
                            className="text-[#2563A8] hover:bg-[#D9E7F5]"
                          >
                            <Eye className="h-3.5 w-3.5 mr-1" /> Inspect
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* MOBILE / TABLET AUDIT CARDS */}
          <div className="lg:hidden space-y-3">
            {paginatedEvents.map((evt) => (
              <div
                key={evt.id}
                onClick={() => router.push(`/admin/audit/${evt.id}`)}
                className="p-4 rounded-xl bg-white border border-[#C9D4E1] shadow-xs space-y-3 cursor-pointer hover:border-[#3B82D0] transition-colors"
              >
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="text-[#718096]">{formatDate(evt.timestamp)}</span>
                  {getResultBadge(evt.result)}
                </div>

                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-xs text-[#17253A]">{evt.action}</span>
                  {getSeverityBadge(evt.severity)}
                </div>

                <div className="p-2.5 rounded-lg bg-[#EFF3F7] text-xs font-mono text-[#526176]">
                  {evt.description}
                </div>

                <div className="flex items-center justify-between text-xs font-mono border-t border-[#D9E1EA] pt-2">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-[#17253A]">{evt.actorName}</span>
                    <Badge variant="outline">{evt.actorRole}</Badge>
                  </div>
                  <span className="text-[#2563A8] flex items-center gap-1 font-bold">
                    View <Eye className="h-3 w-3" />
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-4 py-3 rounded-xl bg-[#EFF3F7] border border-[#C9D4E1] text-xs font-mono">
            <span className="text-[#526176]">
              Showing {Math.min((currentPage - 1) * pageSize + 1, filteredEvents.length)} to{' '}
              {Math.min(currentPage * pageSize, filteredEvents.length)} of {filteredEvents.length} audit events
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
    </div>
  );
}
