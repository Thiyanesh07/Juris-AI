import React from 'react';
import { cn } from '@/lib/utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'primary' | 'outline';
  size?: 'sm' | 'md';
}

export const Badge: React.FC<BadgeProps> = ({
  className,
  variant = 'default',
  size = 'sm',
  children,
  ...props
}) => {
  const variantClass = {
    default: 'bg-[#EFF3F7] text-[#526176] border-[#C9D4E1]',
    success: 'bg-[#D0EDDB] text-[#1E6B45] border-[#B2E2C3]',
    warning: 'bg-[#FBF3D4] text-[#7A5A0F] border-[#F5E5A8]',
    error: 'bg-[#F5D9D9] text-[#8B2E2E] border-[#E8B8B8]',
    primary: 'bg-[#D9E7F5] text-[#2563A8] border-[#B5D3EE]',
    outline: 'bg-transparent text-[#526176] border-[#C9D4E1]',
  }[variant];

  const sizeClass = {
    sm: 'px-2 py-0.5 text-xs rounded-md',
    md: 'px-2.5 py-1 text-sm rounded-md',
  }[size];

  return (
    <span
      className={cn(
        'inline-flex items-center font-mono font-medium border transition-colors',
        variantClass,
        sizeClass,
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
};
