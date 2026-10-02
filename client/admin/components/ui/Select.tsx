import React from 'react';
import { cn } from '@/lib/utils';

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  density?: 'dense' | 'comfortable';
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, density = 'comfortable', ...props }, ref) => {
    return (
      <select
        ref={ref}
        className={cn(
          'input-field w-full cursor-pointer pr-8 bg-no-repeat bg-[right_0.5rem_center]',
          density === 'dense' ? 'input-dense' : 'input-comfortable',
          className
        )}
        {...props}
      >
        {children}
      </select>
    );
  }
);

Select.displayName = 'Select';
