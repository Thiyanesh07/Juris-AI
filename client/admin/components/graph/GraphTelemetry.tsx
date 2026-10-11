'use client';

import React, { useEffect, useState } from 'react';
import { MetricCard } from '@/components/shared/MetricCard';
import { Badge } from '@/components/ui/Badge';
import { GitFork, Network, Layers, Shield, Server, RefreshCw, AlertCircle, CheckCircle2 } from 'lucide-react';
import { fetchPublicStats, checkHealth } from '@/lib/health';
import { PublicStatsResponse } from '@/lib/apiTypes';

export const GraphTelemetry: React.FC = () => {
  const [stats, setStats] = useState<PublicStatsResponse | null>(null);
  const [neo4jStatus, setNeo4jStatus] = useState<'CONNECTED' | 'DEGRADED' | 'NOT_CONNECTED' | 'CHECKING'>('CHECKING');
  const [neo4jDetail, setNeo4jDetail] = useState<string>('Querying Aura connection…');
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;

    async function loadTelemetry() {
      try {
        const [statsRes, healthRes] = await Promise.all([
          fetchPublicStats(),
          checkHealth(),
        ]);

        if (!isMounted) return;

        setStats(statsRes);

        const neoComp = healthRes.raw?.components?.neo4j;
        if (neoComp?.status === 'ok') {
          setNeo4jStatus('CONNECTED');
          setNeo4jDetail(neoComp.detail || 'Neo4j Aura Connected');
        } else if (neoComp?.status === 'degraded') {
          setNeo4jStatus('DEGRADED');
          setNeo4jDetail(neoComp.detail || 'Neo4j Aura Degraded');
        } else {
          setNeo4jStatus('NOT_CONNECTED');
          setNeo4jDetail(neoComp?.error || 'Neo4j Aura Unreachable');
        }
      } catch {
        if (!isMounted) return;
        setNeo4jStatus('NOT_CONNECTED');
        setNeo4jDetail('Connection check failed');
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    loadTelemetry();
    return () => {
      isMounted = false;
    };
  }, []);

  const entityTypeCount = stats ? Object.keys(stats.graph_labels || {}).length : 0;
  const relationTypeCount = stats ? Object.keys(stats.graph_relationship_types || {}).length : 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono font-bold text-[#17253A] uppercase tracking-wider">
          Knowledge Graph Telemetry (Neo4j Aura)
        </span>
        <Badge
          variant={neo4jStatus === 'CONNECTED' ? 'success' : neo4jStatus === 'DEGRADED' ? 'outline' : 'error'}
          size="sm"
        >
          <span className="flex items-center gap-1.5 font-mono text-[11px]">
            {neo4jStatus === 'CHECKING' ? (
              <>
                <RefreshCw className="h-3 w-3 animate-spin" /> Checking Aura…
              </>
            ) : neo4jStatus === 'CONNECTED' ? (
              <>
                <CheckCircle2 className="h-3 w-3" /> Aura Connected
              </>
            ) : (
              <>
                <AlertCircle className="h-3 w-3" /> {neo4jStatus === 'DEGRADED' ? 'Degraded' : 'Not Connected'}
              </>
            )}
          </span>
        </Badge>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Total Graph Nodes"
          value={isLoading ? 'Loading…' : stats ? stats.graph_nodes.toLocaleString() : '—'}
          icon={<GitFork className="h-4 w-4" />}
          footerText={stats ? 'Persisted legal entities' : 'Node telemetry unavailable'}
        />
        <MetricCard
          label="Typed Relationships"
          value={isLoading ? 'Loading…' : stats ? stats.graph_relationships.toLocaleString() : '—'}
          icon={<Network className="h-4 w-4" />}
          footerText={stats ? 'Multi-hop legal edges' : 'Edge telemetry unavailable'}
        />
        <MetricCard
          label="Entity Types"
          value={isLoading ? 'Loading…' : stats ? String(entityTypeCount) : '—'}
          icon={<Layers className="h-4 w-4" />}
          footerText={stats ? 'Distinct entity labels' : 'Label stats unavailable'}
        />
        <MetricCard
          label="Relation Types"
          value={isLoading ? 'Loading…' : stats ? String(relationTypeCount) : '—'}
          icon={<Shield className="h-4 w-4" />}
          footerText={stats ? 'Distinct relation types' : 'Predicate stats unavailable'}
        />
      </div>

      {/* Honest Connection Status */}
      <div className="p-4 rounded-xl bg-[#F5F7FA] border border-[#C9D4E1] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center gap-2.5">
          <Server className="h-4 w-4 text-[#2563A8] shrink-0" />
          <div>
            <span className="font-bold text-[#17253A]">Graph Database Engine: </span>
            <span className={neo4jStatus === 'CONNECTED' ? 'text-[#1E6B45]' : 'text-[#8B2E2E]'}>
              {neo4jDetail}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3 text-[#718096]">
          <span>Neo4j: {neo4jStatus}</span>
          <span>&bull;</span>
          <span>Scope: Production Graph</span>
        </div>
      </div>
    </div>
  );
};
