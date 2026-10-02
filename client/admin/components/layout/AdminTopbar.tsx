'use client';

import React, { useState } from 'react';
import { Search, Bell, Activity, Shield, Menu, User, Lock, LogOut, Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { AvatarInitials } from '@/components/shared/AvatarInitials';
import { Dropdown } from '@/components/ui/Dropdown';
import { cn } from '@/lib/utils';
import { ADMIN_ROUTES } from '@/constants/routes';
import { useAuth } from '@/context/AuthContext';
import { getRoleLabel } from '@/lib/authClient';

export interface AdminTopbarProps {
  isSidebarCollapsed: boolean;
  onMobileMenuToggle?: () => void;
}

export const AdminTopbar: React.FC<AdminTopbarProps> = ({
  isSidebarCollapsed,
  onMobileMenuToggle,
}) => {
  const [hasUnread, setHasUnread] = useState(true);
  const { user, loading, logout } = useAuth();

  const displayName = user?.name ?? user?.email ?? 'Administrator';
  const displayEmail = user?.email ?? '';
  const displayRole = user ? getRoleLabel(user.role) : '—';

  return (
    <header
      className={cn(
        'fixed top-0 right-0 z-30 h-14 bg-[#EFF3F7] border-b border-[#C9D4E1] transition-all duration-200 ease-in-out flex items-center justify-between px-4 md:px-6',
        isSidebarCollapsed ? 'left-0 md:left-[56px]' : 'left-0 md:left-[232px]'
      )}
    >
      {/* Left: Mobile Menu Trigger & Global Search */}
      <div className="flex items-center gap-3 w-full max-w-xs md:max-w-md">
        <button
          onClick={onMobileMenuToggle}
          className="md:hidden p-2 rounded-lg hover:bg-[#D9E7F5] text-[#526176] transition-colors"
          title="Toggle navigation menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div className="relative w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[#718096]" />
          <Input
            placeholder="Search users, documents, entities..."
            density="dense"
            className="pl-8 bg-white text-xs border-[#C5D5E8]"
          />
        </div>
      </div>

      {/* Right: Cluster Status, Notifications & Profile Menu */}
      <div className="flex items-center gap-3 md:gap-4 shrink-0">
        {/* System Status Indicator */}
        <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-full bg-[#D0EDDB] border border-[#B2E2C3] text-[#1E6B45] text-xs font-mono">
          <span className="h-2 w-2 rounded-full bg-[#1E6B45] animate-pulse" />
          <span className="font-medium">System Operational</span>
        </div>

        {/* Notifications Dropdown */}
        <Dropdown
          trigger={
            <button
              onClick={() => setHasUnread(false)}
              className="relative p-2 rounded-lg hover:bg-[#D9E7F5] text-[#526176] transition-colors cursor-pointer"
              title="System Notifications"
            >
              <Bell className="h-4 w-4" />
              {hasUnread && (
                <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-[#3B82D0] ring-2 ring-white" />
              )}
            </button>
          }
          items={[
            {
              id: 'notif-1',
              label: 'Backend integration pending',
              onClick: () => {},
            },
            {
              id: 'notif-2',
              label: 'Authentication layer active (Phase 10.5)',
              onClick: () => {},
            },
          ]}
        />

        {/* Profile Menu Dropdown */}
        <div className="pl-2 border-l border-[#C9D4E1]">
          {loading ? (
            <div className="flex items-center gap-2 px-3 py-1">
              <Loader2 className="h-4 w-4 animate-spin text-[#526176]" />
            </div>
          ) : (
            <Dropdown
              trigger={
                <button className="flex items-center gap-2.5 p-1 rounded-lg hover:bg-[#D9E7F5]/60 transition-colors cursor-pointer text-left">
                  <AvatarInitials name={displayName} size="sm" />
                  <div className="hidden lg:flex flex-col">
                    <span className="text-xs font-semibold text-[#17253A] leading-tight">
                      {displayName}
                    </span>
                    <span className="text-[10px] font-mono text-[#526176]">{displayEmail}</span>
                  </div>
                  <Badge variant="primary" size="sm" className="hidden xl:inline-flex">
                    <Shield className="h-3 w-3 mr-1 text-[#2563A8]" />
                    {displayRole}
                  </Badge>
                </button>
              }
              items={[
                {
                  id: 'profile',
                  label: 'Profile',
                  icon: <User className="h-3.5 w-3.5" />,
                  onClick: () => alert('Profile management will be available in a future phase.'),
                },
                {
                  id: 'security',
                  label: 'Security',
                  icon: <Lock className="h-3.5 w-3.5" />,
                  onClick: () => alert('Security configuration will be available in a future phase.'),
                },
                {
                  id: 'signout',
                  label: 'Sign Out',
                  icon: <LogOut className="h-3.5 w-3.5" />,
                  danger: true,
                  onClick: () => logout(),
                },
              ]}
            />
          )}
        </div>
      </div>
    </header>
  );
};
