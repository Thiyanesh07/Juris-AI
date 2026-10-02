import React from 'react';
import { cn } from '@/lib/utils';

export interface BadgeProps {
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'error' | 'vector' | 'graph' | 'hybrid';
  children: React.ReactNode;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ variant = 'default', children, className }) => {
  const variantClass = {
    default: 'badge-default',
    primary: 'badge-primary',
    success: 'badge-success',
    warning: 'badge-warning',
    error: 'badge-error',
    vector: 'badge-vector',
    graph: 'badge-graph',
    hybrid: 'badge-hybrid',
  }[variant];

  return <span className={cn('badge', variantClass, className)}>{children}</span>;
};
