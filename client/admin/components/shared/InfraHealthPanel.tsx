import React from 'react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/Badge';
import { Server, Activity, CheckCircle2 } from 'lucide-react';

export interface ServiceHealth {
  name: string;
  status: 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY';
  latencyMs?: number;
}

export interface InfraHealthPanelProps {
  clusterName?: string;
  services?: ServiceHealth[];
  className?: string;
}

export const InfraHealthPanel: React.FC<InfraHealthPanelProps> = ({
  clusterName = 'Juris-Prod-Cluster-01',
  services = [
    { name: 'Core API Gateway', status: 'HEALTHY', latencyMs: 14 },
    { name: 'Document Parser Node (worker-01)', status: 'HEALTHY', latencyMs: 42 },
    { name: 'Vector Store Service', status: 'HEALTHY', latencyMs: 28 },
    { name: 'Graph Indexer Node (worker-02)', status: 'HEALTHY', latencyMs: 35 },
  ],
  className,
}) => {
  return (
    <div className={cn('p-5 rounded-xl bg-[#F5F7FA] border border-[#C9D4E1]', className)}>
      <div className="flex items-center justify-between pb-3 border-b border-[#D9E1EA]">
        <div className="flex items-center gap-2">
          <Server className="h-4 w-4 text-[#2563A8]" />
          <span className="text-xs font-mono font-bold text-[#17253A] uppercase tracking-wider">
            {clusterName}
          </span>
        </div>
        <Badge variant="success">
          <span className="flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3" /> Operational
          </span>
        </Badge>
      </div>

      <div className="mt-4 space-y-2.5">
        {services.map((svc) => (
          <div
            key={svc.name}
            className="flex items-center justify-between text-xs font-mono p-2 rounded bg-[#EFF3F7]"
          >
            <span className="text-[#17253A] font-medium">{svc.name}</span>
            <div className="flex items-center gap-3">
              {svc.latencyMs !== undefined && (
                <span className="text-[#718096]">{svc.latencyMs} ms</span>
              )}
              <span
                className={cn(
                  'h-2 w-2 rounded-full',
                  svc.status === 'HEALTHY'
                    ? 'bg-[#1E6B45]'
                    : svc.status === 'DEGRADED'
                    ? 'bg-[#7A5A0F]'
                    : 'bg-[#8B2E2E]'
                )}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
