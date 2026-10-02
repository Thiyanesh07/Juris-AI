import React from 'react';
import { MetricCard } from '@/components/shared/MetricCard';
import { Badge } from '@/components/ui/Badge';
import { GitFork, Network, Layers, Shield, Server, AlertCircle } from 'lucide-react';

export const GraphTelemetry: React.FC = () => {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono font-bold text-[#17253A] uppercase tracking-wider">
          Knowledge Graph Telemetry (Mock Environment)
        </span>
        <Badge variant="outline" size="sm">
          <span className="flex items-center gap-1.5 text-[#718096] font-mono">
            <AlertCircle className="h-3 w-3" /> Neo4j Not Connected
          </span>
        </Badge>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Total Graph Nodes"
          value="20"
          icon={<GitFork className="h-4 w-4" />}
          footerText="Development dataset nodes"
        />
        <MetricCard
          label="Typed Relationships"
          value="24"
          icon={<Network className="h-4 w-4" />}
          footerText="Multi-hop connected edges"
        />
        <MetricCard
          label="Entity Types"
          value="7"
          icon={<Layers className="h-4 w-4" />}
          footerText="Constitutional & legal categories"
        />
        <MetricCard
          label="Relation Types"
          value="9"
          icon={<Shield className="h-4 w-4" />}
          footerText="Semantic legal predicates"
        />
      </div>

      {/* Honest Connection Status */}
      <div className="p-4 rounded-xl bg-[#F5F7FA] border border-[#C9D4E1] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center gap-2.5">
          <Server className="h-4 w-4 text-[#2563A8] shrink-0" />
          <div>
            <span className="font-bold text-[#17253A]">Graph Database Engine: </span>
            <span className="text-[#8B2E2E]">Development / Not Connected</span>
          </div>
        </div>
        <div className="flex items-center gap-3 text-[#718096]">
          <span>Neo4j: Disconnected</span>
          <span>&bull;</span>
          <span>Last Sync: N/A</span>
        </div>
      </div>
    </div>
  );
};
