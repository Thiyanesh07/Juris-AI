import React from 'react';
import { cn } from '@/lib/utils';
import { EmptyState } from './EmptyState';

export interface Column<T> {
  key: string;
  header: string;
  render?: (item: T) => React.ReactNode;
  width?: string;
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (item: T) => string;
  isLoading?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  onRowClick?: (item: T) => void;
  className?: string;
}

export function DataTable<T>({
  columns,
  data,
  keyExtractor,
  isLoading = false,
  emptyTitle,
  emptyDescription,
  onRowClick,
  className,
}: DataTableProps<T>) {
  if (isLoading) {
    return (
      <div className="p-8 text-center text-xs font-mono text-[#526176] bg-[#EFF3F7] rounded-xl border border-[#C9D4E1]">
        Loading data table...
      </div>
    );
  }

  if (!data || data.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }

  return (
    <div className={cn('w-full overflow-hidden rounded-xl border border-[#C9D4E1] bg-white shadow-xs', className)}>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm border-collapse">
          <thead>
            <tr className="bg-[#EFF3F7] border-b border-[#C9D4E1]">
              {columns.map((col) => (
                <th
                  key={col.key}
                  style={{ width: col.width }}
                  className="px-4 py-3 text-xs font-mono font-bold text-[#526176] uppercase tracking-wider"
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#D9E1EA]">
            {data.map((item) => (
              <tr
                key={keyExtractor(item)}
                onClick={() => onRowClick && onRowClick(item)}
                className={cn(
                  'hover:bg-[#EFF3F7]/60 transition-colors',
                  onRowClick && 'cursor-pointer'
                )}
              >
                {columns.map((col) => (
                  <td key={col.key} className="px-4 py-3.5 text-xs text-[#17253A]">
                    {col.render ? col.render(item) : (item as Record<string, unknown>)[col.key] as React.ReactNode}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
