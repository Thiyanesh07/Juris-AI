import React, { useState, useRef, useEffect } from 'react';
import { cn } from '@/lib/utils';

export interface DropdownItem {
  id: string;
  label: string;
  icon?: React.ReactNode;
  danger?: boolean;
  disabled?: boolean;
  onClick: () => void;
}

export interface DropdownProps {
  trigger: React.ReactNode;
  items: DropdownItem[];
  align?: 'left' | 'right';
}

export const Dropdown: React.FC<DropdownProps> = ({ trigger, items, align = 'right' }) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative inline-block text-left" ref={containerRef}>
      <div onClick={() => setIsOpen(!isOpen)}>{trigger}</div>

      {isOpen && (
        <div
          className={cn(
            'absolute z-40 mt-1 min-w-[160px] rounded-lg bg-[#FFFFFF] border border-[#C9D4E1] shadow-[0_2px_8px_rgba(23,37,58,0.08)] py-1 focus:outline-none animate-in fade-in duration-100',
            align === 'right' ? 'right-0' : 'left-0'
          )}
        >
          {items.map((item) => (
            <button
              key={item.id}
              disabled={item.disabled}
              onClick={() => {
                if (!item.disabled) {
                  item.onClick();
                  setIsOpen(false);
                }
              }}
              className={cn(
                'w-full flex items-center gap-2.5 px-3.5 py-2 text-xs font-medium transition-colors text-left disabled:opacity-50 disabled:pointer-events-none cursor-pointer',
                item.danger
                  ? 'text-[#8B2E2E] hover:bg-[#F5D9D9]/50'
                  : 'text-[#17253A] hover:bg-[#EFF3F7]'
              )}
            >
              {item.icon && <span className="h-4 w-4 shrink-0 text-[#526176]">{item.icon}</span>}
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
