import React from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface LoadingStateProps {
  label?: string;
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  label = 'Loading operational data...',
  className,
}) => {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center p-12 text-center rounded-xl bg-[#EFF3F7]/50 border border-[#C9D4E1]',
        className
      )}
    >
      <Loader2 className="h-7 w-7 text-[#2563A8] animate-spin mb-3" />
      <p className="text-xs font-mono font-medium text-[#526176]">{label}</p>
    </div>
  );
};
