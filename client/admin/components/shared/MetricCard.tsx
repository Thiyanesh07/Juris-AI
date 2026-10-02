import React from 'react';
import { cn } from '@/lib/utils';

export interface MetricCardProps {
  label: string;
  value: string | number;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  icon?: React.ReactNode;
  footerText?: string;
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  change,
  changeType = 'neutral',
  icon,
  footerText,
  className,
}) => {
  const changeColor = {
    positive: 'text-[#1E6B45]',
    negative: 'text-[#8B2E2E]',
    neutral: 'text-[#526176]',
  }[changeType];

  return (
    <div
      className={cn(
        'p-5 rounded-xl bg-[#F5F7FA] border border-[#C9D4E1] shadow-[0_2px_4px_rgba(23,37,58,0.04)] flex flex-col justify-between',
        className
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-[#526176] uppercase tracking-wider font-mono">
          {label}
        </span>
        {icon && <div className="p-2 rounded-lg bg-[#EFF3F7] text-[#2563A8]">{icon}</div>}
      </div>

      <div className="mt-3">
        <div className="text-2xl font-bold text-[#17253A] font-mono tracking-tight">{value}</div>
        {change && (
          <div className={cn('text-xs font-mono mt-1 font-medium', changeColor)}>
            {change}
          </div>
        )}
      </div>

      {footerText && (
        <div className="mt-3 pt-2 border-t border-[#D9E1EA] text-xs text-[#718096]">
          {footerText}
        </div>
      )}
    </div>
  );
};
