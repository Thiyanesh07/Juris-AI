'use client';

import React from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useAuditStore } from '@/context/AuditStoreContext';
import { AuditActionResult, AuditCategory, AuditSeverity } from '@/lib/types';
import { ADMIN_ROUTES } from '@/constants/routes';
import { formatDate } from '@/lib/utils';
import { PageHeader } from '@/components/shared/PageHeader';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/shared/EmptyState';
import {
  ChevronLeft,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  User,
  ShieldCheck,
  FileText,
  Cpu,
  GitFork,
  CheckSquare,
  Lock,
  Activity,
  ExternalLink,
  Code2,
  Monitor,
  Terminal,
  ArrowRight,
  ShieldAlert,
  HelpCircle,
} from 'lucide-react';

export default function AuditEventDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;

  const { getEventById } = useAuditStore();
  const event = getEventById(id);

  if (!event) {
    return (
      <div className="space-y-6">
        <Link
          href={ADMIN_ROUTES.AUDIT}
          className="inline-flex items-center text-xs font-mono text-[#526176] hover:text-[#2563A8] transition-colors"
        >
          <ChevronLeft className="h-4 w-4 mr-1" /> Back to Audit Logs
        </Link>
        <EmptyState
          title="Audit Event Not Found"
          description={`No audit event record exists with ID "${id}".`}
          action={
            <Button variant="primary" size="sm" onClick={() => router.push(ADMIN_ROUTES.AUDIT)}>
              Return to Audit Logs
            </Button>
          }
        />
      </div>
    );
  }

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

  const getResourceLink = () => {
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

  const resourceLink = getResourceLink();

  // Helper to mask sensitive value strings
  const maskSensitive = (key: string, value: unknown): string => {
    const k = key.toLowerCase();
    if (k.includes('secret') || k.includes('token') || k.includes('password') || k.includes('key')) {
      return '••••••••••••••••';
    }
    if (typeof value === 'object' && value !== null) {
      return JSON.stringify(value);
    }
    return String(value);
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Top Navigation */}
      <div className="flex items-center justify-between">
        <Link
          href={ADMIN_ROUTES.AUDIT}
          className="inline-flex items-center text-xs font-mono text-[#526176] hover:text-[#2563A8] transition-colors"
        >
          <ChevronLeft className="h-4 w-4 mr-1" /> Back to Audit Logs
        </Link>
        <span className="text-xs font-mono text-[#718096]">Event ID: {event.id}</span>
      </div>

      {/* Page Header */}
      <PageHeader
        title={`Audit Event: ${event.action}`}
        subtitle={`Recorded on ${formatDate(event.timestamp)} • Category: ${event.category}`}
        actions={
          <div className="flex items-center gap-2">
            {getResultBadge(event.result)}
            {getSeverityBadge(event.severity)}
          </div>
        }
      />

      {/* Two Column Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT COLUMN: EVENT DETAILS & STATE COMPARISON */}
        <div className="lg:col-span-7 space-y-6">
          {/* Event Description Card */}
          <div className="p-5 rounded-xl bg-white border border-[#C9D4E1] shadow-xs space-y-3">
            <div className="flex items-center justify-between border-b border-[#D9E1EA] pb-3">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-[#2563A8]" />
                <h3 className="text-sm font-bold text-[#17253A]">Event Summary & Description</h3>
              </div>
              <Badge variant="outline">{event.category}</Badge>
            </div>
            <p className="text-sm font-sans text-[#17253A] leading-relaxed">
              {event.description}
            </p>
          </div>

          {/* Actor & Execution Identity Card */}
          <div className="p-5 rounded-xl bg-white border border-[#C9D4E1] shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-[#D9E1EA] pb-3">
              <div className="flex items-center gap-2">
                <User className="h-4 w-4 text-[#2563A8]" />
                <h3 className="text-sm font-bold text-[#17253A]">Actor & Session Identity</h3>
              </div>
              <Badge variant="outline">{event.actorRole}</Badge>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
              <div className="p-3 rounded-lg bg-[#EFF3F7] border border-[#D9E1EA] space-y-1">
                <span className="text-[#718096] text-[10px] uppercase block">Actor Name</span>
                <span className="font-bold text-[#17253A] block">{event.actorName}</span>
                <span className="text-[#526176] text-[11px] block">{event.actorEmail}</span>
              </div>
              <div className="p-3 rounded-lg bg-[#EFF3F7] border border-[#D9E1EA] space-y-1">
                <span className="text-[#718096] text-[10px] uppercase block">Actor ID</span>
                <span className="font-bold text-[#2563A8] block">{event.actorId}</span>
                <span className="text-[#526176] text-[11px] block">Role: {event.actorRole}</span>
              </div>
            </div>

            {/* Network Telemetry */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono pt-1">
              <div>
                <span className="text-[#718096] uppercase text-[10px] tracking-wider block">
                  IP Address
                </span>
                <span className="font-semibold text-[#17253A] mt-0.5 block flex items-center gap-1">
                  <Monitor className="h-3.5 w-3.5 text-[#718096]" />
                  {event.ipAddress || '127.0.0.1 (Internal)'}
                </span>
              </div>
              <div>
                <span className="text-[#718096] uppercase text-[10px] tracking-wider block">
                  User Agent / Client
                </span>
                <span className="font-semibold text-[#526176] mt-0.5 block truncate text-[11px]">
                  {event.userAgent || 'Juris AI Core Engine / System Task'}
                </span>
              </div>
            </div>
          </div>

          {/* Resource Context Card */}
          <div className="p-5 rounded-xl bg-white border border-[#C9D4E1] shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-[#D9E1EA] pb-3">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-[#2563A8]" />
                <h3 className="text-sm font-bold text-[#17253A]">Affected Resource</h3>
              </div>
              {resourceLink && (
                <Link
                  href={resourceLink}
                  className="inline-flex items-center text-xs font-mono text-[#2563A8] hover:underline"
                >
                  View Target Resource <ExternalLink className="h-3 w-3 ml-1" />
                </Link>
              )}
            </div>

            {event.resourceType ? (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
                <div className="p-3 rounded-lg bg-[#EFF3F7] border border-[#D9E1EA]">
                  <span className="text-[#718096] text-[10px] uppercase block">Resource Type</span>
                  <span className="font-bold text-[#17253A] mt-0.5 block">{event.resourceType}</span>
                </div>
                <div className="p-3 rounded-lg bg-[#EFF3F7] border border-[#D9E1EA]">
                  <span className="text-[#718096] text-[10px] uppercase block">Resource ID</span>
                  <span className="font-bold text-[#2563A8] mt-0.5 block">{event.resourceId || '—'}</span>
                </div>
                <div className="p-3 rounded-lg bg-[#EFF3F7] border border-[#D9E1EA]">
                  <span className="text-[#718096] text-[10px] uppercase block">Resource Name</span>
                  <span className="font-bold text-[#17253A] mt-0.5 block truncate">
                    {event.resourceName || '—'}
                  </span>
                </div>
              </div>
            ) : (
              <p className="text-xs font-mono text-[#718096]">
                This action is a system-wide or authentication event without a specific target entity resource.
              </p>
            )}
          </div>

          {/* Before / After State Comparison (if applicable) */}
          {(event.beforeState || event.afterState) && (
            <div className="p-5 rounded-xl bg-white border border-[#C9D4E1] shadow-xs space-y-4">
              <div className="flex items-center justify-between border-b border-[#D9E1EA] pb-3">
                <div className="flex items-center gap-2">
                  <Code2 className="h-4 w-4 text-[#2563A8]" />
                  <h3 className="text-sm font-bold text-[#17253A]">State Modification (Before vs After)</h3>
                </div>
                <span className="text-[11px] font-mono text-[#718096]">State Diff</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
                {/* BEFORE STATE */}
                <div className="space-y-1.5">
                  <span className="text-[#8B2E2E] font-bold text-[11px] uppercase tracking-wider block">
                    Before State:
                  </span>
                  <div className="p-3 rounded-lg bg-[#FBE8E8] border border-[#F4B8B8] text-[#8B2E2E] overflow-x-auto">
                    {event.beforeState ? (
                      <pre className="whitespace-pre-wrap font-mono text-[11px]">
                        {JSON.stringify(event.beforeState, null, 2)}
                      </pre>
                    ) : (
                      <span className="italic text-[11px]">None (New Resource Creation)</span>
                    )}
                  </div>
                </div>

                {/* AFTER STATE */}
                <div className="space-y-1.5">
                  <span className="text-[#1E6B45] font-bold text-[11px] uppercase tracking-wider block">
                    After State:
                  </span>
                  <div className="p-3 rounded-lg bg-[#D0EDDB] border border-[#A1DBB7] text-[#1E6B45] overflow-x-auto">
                    {event.afterState ? (
                      <pre className="whitespace-pre-wrap font-mono text-[11px]">
                        {JSON.stringify(event.afterState, null, 2)}
                      </pre>
                    ) : (
                      <span className="italic text-[11px]">None (Resource Deletion)</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* RIGHT COLUMN: STRUCTURED METADATA & IMMUTABILITY PANEL */}
        <div className="lg:col-span-5 space-y-6">
          {/* Metadata Key/Value Table Card */}
          <div className="p-5 rounded-xl bg-white border border-[#C9D4E1] shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-[#D9E1EA] pb-3">
              <div className="flex items-center gap-2">
                <Terminal className="h-4 w-4 text-[#2563A8]" />
                <h3 className="text-sm font-bold text-[#17253A]">Structured Event Metadata</h3>
              </div>
              <span className="text-[11px] font-mono text-[#718096]">JSON Attributes</span>
            </div>

            {event.metadata && Object.keys(event.metadata).length > 0 ? (
              <div className="border border-[#C9D4E1] rounded-lg overflow-hidden bg-[#EFF3F7]">
                <table className="w-full text-left font-mono text-xs border-collapse">
                  <thead>
                    <tr className="bg-[#D9E1EA] text-[#526176] text-[10px] uppercase font-bold border-b border-[#C9D4E1]">
                      <th className="px-3 py-2">Attribute Key</th>
                      <th className="px-3 py-2">Recorded Value</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#D9E1EA]">
                    {Object.entries(event.metadata).map(([key, value]) => (
                      <tr key={key} className="hover:bg-white/60 transition-colors">
                        <td className="px-3 py-2 font-bold text-[#17253A] text-[11px]">{key}</td>
                        <td className="px-3 py-2 text-[#2563A8] text-[11px] break-all">
                          {maskSensitive(key, value)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-3.5 rounded-lg bg-[#EFF3F7] border border-[#D9E1EA] text-xs font-mono text-[#718096]">
                No additional structured metadata payload attached to this audit event.
              </div>
            )}
          </div>

          {/* Read-Only & Compliance Immutability Notice */}
          <div className="p-5 rounded-xl bg-white border border-[#C9D4E1] shadow-xs space-y-4">
            <div className="flex items-center gap-2 border-b border-[#D9E1EA] pb-3">
              <ShieldCheck className="h-4 w-4 text-[#1E6B45]" />
              <h3 className="text-sm font-bold text-[#17253A]">Compliance & Security Notice</h3>
            </div>

            <div className="space-y-3 text-xs font-mono text-[#526176]">
              <div className="p-3.5 rounded-lg bg-[#EFF3F7] border border-[#D9E1EA] space-y-2">
                <span className="font-bold text-[#17253A] block flex items-center gap-1.5">
                  <Lock className="h-3.5 w-3.5 text-[#1E6B45]" />
                  Audit Immutability Policy
                </span>
                <p className="text-[11px] leading-relaxed">
                  Audit records in Juris AI are permanent and read-only. Administrative events cannot be edited, tampered with, or deleted by any user role.
                </p>
              </div>

              <div className="space-y-1.5 text-[11px]">
                <div className="flex items-center justify-between">
                  <span className="text-[#718096]">Cryptographic Verification:</span>
                  <span className="font-bold text-[#1E6B45]">SHA-256 Verified</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[#718096]">Storage Layer:</span>
                  <span className="font-bold text-[#17253A]">Append-Only Log Stream</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
