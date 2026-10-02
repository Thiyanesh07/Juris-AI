import React from 'react';
import { cn } from '@/lib/utils';

export interface TabItem {
  id: string;
  label: string;
  count?: number;
}

export interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (id: string) => void;
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({ tabs, activeTab, onChange, className }) => {
  return (
    <div className={cn('flex items-center border-b border-[#C9D4E1] gap-6', className)}>
      {tabs.map((tab) => {
        const isActive = tab.id === activeTab;
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={cn(
              'pb-3 pt-1 text-sm font-medium transition-colors relative cursor-pointer',
              isActive ? 'text-[#2563A8]' : 'text-[#526176] hover:text-[#17253A]'
            )}
          >
            <span className="flex items-center gap-2">
              {tab.label}
              {tab.count !== undefined && (
                <span
                  className={cn(
                    'px-1.5 py-0.5 text-xs rounded-full font-mono',
                    isActive ? 'bg-[#D9E7F5] text-[#2563A8]' : 'bg-[#EFF3F7] text-[#718096]'
                  )}
                >
                  {tab.count}
                </span>
              )}
            </span>
            {isActive && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#2563A8] rounded-t-sm" />
            )}
          </button>
        );
      })}
    </div>
  );
};
