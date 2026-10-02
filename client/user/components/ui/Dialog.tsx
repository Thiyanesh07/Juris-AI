'use client';

import React, { useState, useRef, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { X } from 'lucide-react';
import { Button } from './Button';

interface DialogProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children?: React.ReactNode;
  footer?: React.ReactNode;
  size?: 'sm' | 'md' | 'lg';
}

export const Dialog: React.FC<DialogProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  footer,
  size = 'md',
}) => {
  if (!isOpen) return null;

  const maxWidth = { sm: 'max-w-sm', md: 'max-w-md', lg: 'max-w-lg' }[size];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div
        className={cn(
          'relative w-full bg-white rounded-2xl shadow-2xl border border-[#CBD5E0] z-10 animate-fade-in-up',
          maxWidth
        )}
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-start justify-between p-5 border-b border-[#E2E8F0]">
          <div>
            <h3 className="text-base font-bold text-[#17253A] font-sans">{title}</h3>
            {description && (
              <p className="text-xs text-[#526176] mt-1 font-mono">{description}</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="ml-4 p-1 rounded-md text-[#718096] hover:bg-[#F0F4F8] transition-colors cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        {children && <div className="p-5 space-y-3">{children}</div>}
        {footer && (
          <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-[#E2E8F0]">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};
