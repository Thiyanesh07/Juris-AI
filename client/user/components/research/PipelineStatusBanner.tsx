'use client';

import React from 'react';
import { PipelineStage, ResearchStatus } from '@/lib/types';
import { cn } from '@/lib/utils';
import { CheckCircle2, Loader2, Circle, Cpu, Sparkles } from 'lucide-react';

interface PipelineStatusProps {
  stages: PipelineStage[];
  status: ResearchStatus;
  query: string;
}

export const PipelineStatusBanner: React.FC<PipelineStatusProps> = ({ stages, status, query }) => {
  if (status === 'IDLE') return null;

  const completedCount = stages.filter(s => s.status === 'COMPLETE').length;
  const progressPercent = Math.round((completedCount / stages.length) * 100);
  const currentRunningStage = stages.find(s => s.status === 'RUNNING');

  return (
    <div className="card p-5 border-[#1D4E8A]/30 bg-gradient-to-r from-white via-[#F8FAFC] to-[#E8F0FD] shadow-md animate-fade-in-up">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 border-b border-[#E2E8F0] pb-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-[#1D4E8A] text-white">
            <Cpu className="h-5 w-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold text-[#1D4E8A] uppercase tracking-wider">
                GraphRAG Research Execution
              </span>
              <span className="badge badge-primary text-[10px]">
                {status === 'COMPLETE' ? 'Complete' : 'Processing Pipeline'}
              </span>
            </div>
            <p className="text-xs text-[#526176] font-mono mt-0.5 truncate max-w-md">
              "{query}"
            </p>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-xs font-mono font-bold text-[#17253A]">{progressPercent}%</p>
            <p className="text-[10px] font-mono text-[#718096]">{completedCount}/{stages.length} Stages</p>
          </div>
          <div className="w-28 h-2.5 bg-[#E2E8F0] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#1D4E8A] transition-all duration-300 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* Stages grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
        {stages.map((stage, i) => (
          <div
            key={stage.id}
            className={cn(
              'p-2 rounded-lg border text-xs transition-all',
              stage.status === 'COMPLETE' && 'bg-[#F0FDF4] border-[#BBF7D0] text-[#166534]',
              stage.status === 'RUNNING' && 'bg-[#EFF6FF] border-[#BFDBFE] text-[#1E40AF] font-medium shadow-sm scale-105',
              stage.status === 'PENDING' && 'bg-white border-[#E2E8F0] text-[#718096] opacity-60'
            )}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-mono text-[10px] font-bold">0{i + 1}</span>
              {stage.status === 'COMPLETE' && <CheckCircle2 className="h-3 w-3 text-[#166534]" />}
              {stage.status === 'RUNNING' && <Loader2 className="h-3 w-3 animate-spin text-[#1D4E8A]" />}
              {stage.status === 'PENDING' && <Circle className="h-3 w-3 text-[#CBD5E0]" />}
            </div>
            <p className="font-sans text-[11px] leading-tight line-clamp-1 truncate">{stage.label}</p>
          </div>
        ))}
      </div>

      {currentRunningStage && (
        <div className="mt-3 flex items-center gap-2 text-xs font-mono text-[#1D4E8A]">
          <Sparkles className="h-3.5 w-3.5 animate-spin" />
          <span>Active: {currentRunningStage.description}</span>
        </div>
      )}
    </div>
  );
};
