import React from 'react';
import { Badge } from '@/components/ui/Badge';
import { Circle, Square, Diamond, Hexagon, FileText } from 'lucide-react';

export const GraphLegend: React.FC = () => {
  const legendItems = [
    { label: 'Article', color: '#2563A8', shape: 'Circle' },
    { label: 'Act / Code', color: '#183B5B', shape: 'Rounded Rect' },
    { label: 'Section', color: '#3B82D0', shape: 'Rect' },
    { label: 'Amendment', color: '#7A5A0F', shape: 'Diamond' },
    { label: 'Judgment', color: '#1E6B45', shape: 'Document Tag' },
    { label: 'Court', color: '#8B2E2E', shape: 'Hexagon' },
  ];

  return (
    <div className="p-4 rounded-xl bg-white border border-[#C9D4E1] shadow-xs space-y-3 font-mono text-xs">
      <h4 className="font-bold text-[#17253A] uppercase tracking-wider text-[11px]">
        Entity Visual Legend
      </h4>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {legendItems.map((item) => (
          <div key={item.label} className="flex items-center gap-2 p-1.5 rounded bg-[#EFF3F7]">
            <span
              className="h-3 w-3 rounded-full shrink-0"
              style={{ backgroundColor: item.color }}
            />
            <div className="flex flex-col">
              <span className="font-semibold text-[#17253A] text-[11px] leading-tight">
                {item.label}
              </span>
              <span className="text-[10px] text-[#718096]">{item.shape}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
