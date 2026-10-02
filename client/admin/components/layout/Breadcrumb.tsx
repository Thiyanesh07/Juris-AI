'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ChevronRight } from 'lucide-react';
import { ADMIN_ROUTES } from '@/constants/routes';

export const Breadcrumb: React.FC = () => {
  const pathname = usePathname();

  if (!pathname || pathname === ADMIN_ROUTES.LOGIN) return null;

  const pathSegments = pathname
    .split('/')
    .filter(Boolean)
    .slice(1); // Drop 'admin' segment

  const formatSegment = (seg: string) => {
    if (seg === 'admins') return 'Administrators';
    if (seg === 'graph') return 'Knowledge Graph';
    if (seg === 'audit') return 'Audit Logs';
    return seg.replace(/-/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
  };

  const currentTitle = pathSegments.length > 0 ? formatSegment(pathSegments[0]) : 'Dashboard';

  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-xs text-[#526176] font-mono mb-4">
      <Link
        href={ADMIN_ROUTES.DASHBOARD}
        className="text-[#526176] hover:text-[#17253A] font-medium transition-colors"
      >
        Juris AI
      </Link>
      <ChevronRight className="h-3 w-3 text-[#718096]" />
      <span className="text-[#526176]">Administration</span>
      <ChevronRight className="h-3 w-3 text-[#718096]" />
      <span className="font-semibold text-[#17253A]">{currentTitle}</span>
    </nav>
  );
};
