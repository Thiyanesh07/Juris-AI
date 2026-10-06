'use client';

import React, { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { useSidebar } from '@/hooks/useSidebar';
import { AdminSidebar } from '@/components/layout/AdminSidebar';
import { AdminTopbar } from '@/components/layout/AdminTopbar';
import { Breadcrumb } from '@/components/layout/Breadcrumb';
import { UserStoreProvider } from '@/context/UserStoreContext';
import { DocumentStoreProvider } from '@/context/DocumentStoreContext';
import { ValidationStoreProvider } from '@/context/ValidationStoreContext';
import { AuditStoreProvider } from '@/context/AuditStoreContext';
import { SettingsStoreProvider } from '@/context/SettingsStoreContext';
import { useAuth, useRequireAdmin } from '@/context/AuthContext';
import { cn } from '@/lib/utils';

export default function AdminAppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isCollapsed, toggleSidebar } = useSidebar();
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const { loading } = useAuth();
  const adminUser = useRequireAdmin();

  if (loading || !adminUser) {
    return (
      <div className="min-h-screen bg-[#E7EDF4] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-[#1B365D]" />
      </div>
    );
  }

  return (
    <UserStoreProvider>
      <DocumentStoreProvider>
        <ValidationStoreProvider>
          <AuditStoreProvider>
            <SettingsStoreProvider>
              <div className="min-h-screen bg-[#E7EDF4] flex flex-col">
                {/* Sidebar Navigation */}
                <AdminSidebar
                  isCollapsed={isCollapsed}
                  onToggle={toggleSidebar}
                  isMobileOpen={isMobileOpen}
                  onMobileClose={() => setIsMobileOpen(false)}
                />

                {/* Top Header */}
                <AdminTopbar
                  isSidebarCollapsed={isCollapsed}
                  onMobileMenuToggle={() => setIsMobileOpen(!isMobileOpen)}
                />

                {/* Main Content Area */}
                <main
                  className={cn(
                    'flex-1 pt-18 pb-10 px-4 sm:px-6 lg:px-8 transition-all duration-200 ease-in-out',
                    isCollapsed ? 'ml-0 md:ml-[56px]' : 'ml-0 md:ml-[232px]'
                  )}
                >
                  <div className="max-w-7xl mx-auto">
                    <Breadcrumb />
                    {children}
                  </div>
                </main>
              </div>
            </SettingsStoreProvider>
          </AuditStoreProvider>
        </ValidationStoreProvider>
      </DocumentStoreProvider>
    </UserStoreProvider>
  );
}
