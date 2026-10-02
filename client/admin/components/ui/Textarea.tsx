import React from 'react';
import { cn } from '@/lib/utils';

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, error = false, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={cn(
          'input-field w-full p-3 text-sm min-h-[90px] resize-y',
          error && 'border-[#8B2E2E] focus:border-[#8B2E2E] focus:ring-1 focus:ring-[#8B2E2E]',
          className
        )}
        {...props}
      />
    );
  }
);

Textarea.displayName = 'Textarea';
