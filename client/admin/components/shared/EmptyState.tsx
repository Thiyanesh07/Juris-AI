import React from 'react';
import { FolderOpen } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No records found',
  description = 'There are no items to display at this time.',
  icon,
  action,
  className,
}) => {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center p-12 text-center rounded-xl bg-[#EFF3F7] border border-[#C9D4E1]',
        className
      )}
    >
      <div className="p-3.5 rounded-full bg-[#D9E7F5] text-[#2563A8] mb-4">
        {icon || <FolderOpen className="h-6 w-6" />}
      </div>
      <h3 className="text-base font-semibold text-[#17253A] font-serif">{title}</h3>
      <p className="text-xs text-[#526176] mt-1 max-w-sm">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
};
