'use client';

import React from 'react';
import { ResearchStoreProvider } from '@/context/ResearchStoreContext';
import { UserShell } from '@/components/layout/UserShell';

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  return (
    <ResearchStoreProvider>
      <UserShell>{children}</UserShell>
    </ResearchStoreProvider>
  );
}
