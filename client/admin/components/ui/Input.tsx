import React from 'react';
import { cn } from '@/lib/utils';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  density?: 'dense' | 'comfortable';
  error?: boolean;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, density = 'comfortable', error = false, ...props }, ref) => {
    return (
      <input
        type={type}
        ref={ref}
        className={cn(
          'input-field w-full',
          density === 'dense' ? 'input-dense' : 'input-comfortable',
          error && 'border-[#8B2E2E] focus:border-[#8B2E2E] focus:ring-1 focus:ring-[#8B2E2E]',
          className
        )}
        {...props}
      />
    );
  }
);

Input.displayName = 'Input';
