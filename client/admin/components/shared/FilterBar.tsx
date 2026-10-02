import React from 'react';
import { Search, Filter, RotateCcw } from 'lucide-react';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

export interface FilterBarProps {
  searchValue: string;
  onSearchChange: (value: string) => void;
  placeholder?: string;
  filters?: React.ReactNode;
  onReset?: () => void;
  className?: string;
}

export const FilterBar: React.FC<FilterBarProps> = ({
  searchValue,
  onSearchChange,
  placeholder = 'Search records...',
  filters,
  onReset,
  className,
}) => {
  return (
    <div
      className={cn(
        'p-3 rounded-xl bg-[#EFF3F7] border border-[#C9D4E1] flex flex-col md:flex-row items-center gap-3 justify-between',
        className
      )}
    >
      <div className="relative w-full md:w-80">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#718096]" />
        <Input
          value={searchValue}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder={placeholder}
          density="dense"
          className="pl-9 bg-white"
        />
      </div>

      <div className="flex items-center gap-2.5 w-full md:w-auto overflow-x-auto justify-end">
        {filters && <div className="flex items-center gap-2">{filters}</div>}
        {onReset && (
          <Button variant="ghost" size="sm" onClick={onReset} className="text-xs text-[#526176]">
            <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
            Reset
          </Button>
        )}
      </div>
    </div>
  );
};
