import React from 'react';
import { getInitials } from '@/lib/utils';
import { cn } from '@/lib/utils';

export interface AvatarInitialsProps {
  name: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const AvatarInitials: React.FC<AvatarInitialsProps> = ({
  name,
  size = 'md',
  className,
}) => {
  const sizeClass = {
    sm: 'h-7 w-7 text-xs',
    md: 'h-9 w-9 text-sm',
    lg: 'h-11 w-11 text-base',
  }[size];

  return (
    <div
      className={cn(
        'inline-flex items-center justify-center font-mono font-semibold rounded-full bg-[#D9E7F5] text-[#2563A8] border border-[#B5D3EE] shrink-0 select-none',
        sizeClass,
        className
      )}
    >
      {getInitials(name)}
    </div>
  );
};
