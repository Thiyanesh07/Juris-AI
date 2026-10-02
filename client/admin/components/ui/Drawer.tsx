import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from './Button';

export interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  width?: 'md' | 'lg' | 'xl';
}

export const Drawer: React.FC<DrawerProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  footer,
  width = 'md',
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const widthClass = {
    md: 'w-80 md:w-96',
    lg: 'w-96 md:w-[480px]',
    xl: 'w-full md:w-[640px]',
  }[width];

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-[#17253A]/30 backdrop-blur-xs">
      <div className="absolute inset-0" onClick={onClose} />

      <div className="fixed inset-y-0 right-0 flex max-w-full pl-10">
        <div
          className={cn(
            'relative w-screen bg-[#FFFFFF] border-l border-[#C9D4E1] shadow-[-8px_0_40px_rgba(23,37,58,0.10)] flex flex-col',
            widthClass
          )}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-[#D9E1EA]">
            <div>
              {title && <h3 className="text-lg font-semibold text-[#17253A] font-serif">{title}</h3>}
              {description && <p className="text-xs text-[#526176] mt-0.5">{description}</p>}
            </div>
            <Button variant="ghost" size="sm" onClick={onClose} className="h-8 w-8 p-0 rounded-full">
              <X className="h-4 w-4" />
            </Button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-6">{children}</div>

          {/* Footer */}
          {footer && (
            <div className="flex items-center justify-end gap-3 px-6 py-4 bg-[#EFF3F7] border-t border-[#D9E1EA]">
              {footer}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
