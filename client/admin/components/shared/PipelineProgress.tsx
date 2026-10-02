import React from 'react';
import { cn } from '@/lib/utils';
import { IngestionJobStatus } from '@/lib/types';
import { Badge } from '@/components/ui/Badge';

export interface PipelineProgressProps {
  jobId: string;
  documentTitle: string;
  status: IngestionJobStatus;
  progressPercentage: number;
  workerNode?: string; // e.g. 'worker-04'
  className?: string;
}

export const PipelineProgress: React.FC<PipelineProgressProps> = ({
  jobId,
  documentTitle,
  status,
  progressPercentage,
  workerNode = 'worker-01',
  className,
}) => {
  const statusBadgeVariant = {
    QUEUED: 'default',
    PARSING: 'primary',
    EXTRACTING_ENTITIES: 'primary',
    BUILDING_INDEX: 'primary',
    COMPLETED: 'success',
    FAILED: 'error',
    CANCELLED: 'outline',
  }[status] as 'default' | 'primary' | 'success' | 'error' | 'outline';

  return (
    <div className={cn('p-4 rounded-lg bg-[#EFF3F7] border border-[#C9D4E1]', className)}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 truncate">
          <span className="text-xs font-mono text-[#718096]">{jobId}</span>
          <span className="text-sm font-semibold text-[#17253A] truncate">{documentTitle}</span>
        </div>
        <Badge variant={statusBadgeVariant}>{status}</Badge>
      </div>

      <div className="w-full bg-[#C9D4E1] h-2 rounded-full overflow-hidden my-2">
        <div
          className="bg-[#2563A8] h-full transition-all duration-300 ease-out"
          style={{ width: `${Math.min(100, Math.max(0, progressPercentage))}%` }}
        />
      </div>

      <div className="flex items-center justify-between text-xs text-[#526176] font-mono mt-2">
        <span>Progress: {progressPercentage}%</span>
        <span>Worker: {workerNode}</span>
      </div>
    </div>
  );
};
