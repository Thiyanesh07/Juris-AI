import React from 'react';
import { cn } from '@/lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'destructive';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', isLoading, children, disabled, ...props }, ref) => {
    const variantClass = {
      primary: 'btn-primary',
      secondary: 'btn-secondary',
      ghost: 'btn-ghost',
      destructive: 'btn-destructive',
    }[variant];

    const sizeClass = {
      sm: 'h-8 px-3 text-xs rounded-md',
      md: 'h-9 px-4 text-sm rounded-md',
      lg: 'h-10 px-5 text-sm rounded-lg',
    }[size];

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(
          'inline-flex items-center justify-center font-medium transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3B82D0]',
          'disabled:opacity-50 disabled:pointer-events-none cursor-pointer',
          variantClass,
          sizeClass,
          className
        )}
        {...props}
      >
        {isLoading && (
          <span className="mr-2 h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
        )}
        {children}
      </button>
    );
  }
);
Button.displayName = 'Button';
