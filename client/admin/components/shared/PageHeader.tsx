import React from 'react';
import { cn } from '@/lib/utils';

export interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  className?: string;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  actions,
  className,
}) => {
  return (
    <div
      className={cn(
        'flex flex-col md:flex-row md:items-center md:justify-between pb-6 border-b border-[#C9D4E1] gap-4',
        className
      )}
    >
      <div>
        <h1 className="text-2xl font-bold text-[#17253A] font-serif tracking-tight">{title}</h1>
        {subtitle && <p className="text-sm text-[#526176] mt-1">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-3 shrink-0">{actions}</div>}
    </div>
  );
};
