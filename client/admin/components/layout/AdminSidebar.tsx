'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Users,
  ShieldAlert,
  FileText,
  Cpu,
  GitFork,
  CheckCircle2,
  History,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Scale,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { ADMIN_ROUTES } from '@/constants/routes';
import { Tooltip } from '@/components/ui/Tooltip';

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', href: ADMIN_ROUTES.DASHBOARD, icon: <LayoutDashboard className="h-4 w-4" /> },
  { label: 'Users', href: ADMIN_ROUTES.USERS, icon: <Users className="h-4 w-4" /> },
  { label: 'Administrators', href: ADMIN_ROUTES.ADMINS, icon: <ShieldAlert className="h-4 w-4" /> },
  { label: 'Documents', href: ADMIN_ROUTES.DOCUMENTS, icon: <FileText className="h-4 w-4" /> },
  { label: 'Ingestion', href: ADMIN_ROUTES.INGESTION, icon: <Cpu className="h-4 w-4" /> },
  { label: 'Knowledge Graph', href: ADMIN_ROUTES.GRAPH, icon: <GitFork className="h-4 w-4" /> },
  { label: 'Validation', href: ADMIN_ROUTES.VALIDATION, icon: <CheckCircle2 className="h-4 w-4" /> },
  { label: 'Audit Logs', href: ADMIN_ROUTES.AUDIT, icon: <History className="h-4 w-4" /> },
  { label: 'Settings', href: ADMIN_ROUTES.SETTINGS, icon: <Settings className="h-4 w-4" /> },
];

export interface AdminSidebarProps {
  isCollapsed: boolean;
  onToggle: () => void;
  isMobileOpen?: boolean;
  onMobileClose?: () => void;
}

export const AdminSidebar: React.FC<AdminSidebarProps> = ({
  isCollapsed,
  onToggle,
  isMobileOpen = false,
  onMobileClose,
}) => {
  const pathname = usePathname();

  const renderNavItems = (mobileMode = false) => (
    <nav className="p-2 space-y-1 mt-2">
      {NAV_ITEMS.map((item) => {
        const isActive =
          pathname === item.href ||
          (item.href !== ADMIN_ROUTES.DASHBOARD && pathname?.startsWith(item.href));

        const content = (
          <Link
            key={item.href}
            href={item.href}
            onClick={() => mobileMode && onMobileClose && onMobileClose()}
            className={cn(
              'flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all duration-150 cursor-pointer relative group',
              isActive
                ? 'bg-[#2563A8] text-white shadow-xs font-semibold'
                : 'text-[#526176] hover:bg-[#D9E7F5] hover:text-[#17253A]'
            )}
          >
            {/* Active Left Indicator */}
            {isActive && (
              <span className="absolute left-0 top-1.5 bottom-1.5 w-1 bg-[#183B5B] rounded-r" />
            )}
            <span className={cn('shrink-0', isActive ? 'text-white' : 'text-[#526176]')}>
              {item.icon}
            </span>
            {(!isCollapsed || mobileMode) && <span className="truncate">{item.label}</span>}
          </Link>
        );

        if (isCollapsed && !mobileMode) {
          return (
            <Tooltip key={item.href} content={item.label} position="right">
              {content}
            </Tooltip>
          );
        }

        return content;
      })}
    </nav>
  );

  return (
    <>
      {/* DESKTOP SIDEBAR */}
      <aside
        className={cn(
          'hidden md:flex fixed top-0 left-0 z-40 h-screen bg-[#EFF3F7] border-r border-[#C9D4E1] transition-all duration-200 ease-in-out flex-col justify-between select-none',
          isCollapsed ? 'w-[56px]' : 'w-[232px]'
        )}
      >
        {/* Brand Header */}
        <div>
          <div className="h-14 border-b border-[#C9D4E1] flex items-center justify-between px-3.5">
            <Link href={ADMIN_ROUTES.DASHBOARD} className="flex items-center gap-2.5 overflow-hidden">
              <div className="p-1.5 rounded-lg bg-[#2563A8] text-white shrink-0">
                <Scale className="h-4 w-4" />
              </div>
              {!isCollapsed && (
                <div className="flex flex-col truncate">
                  <span className="font-serif font-bold text-sm text-[#17253A] leading-tight">
                    Juris AI
                  </span>
                  <span className="font-mono text-[10px] text-[#2563A8] font-semibold tracking-wider">
                    ADMIN CONSOLE
                  </span>
                </div>
              )}
            </Link>

            <button
              onClick={onToggle}
              className="p-1.5 rounded-md hover:bg-[#D9E7F5] text-[#526176] hover:text-[#17253A] transition-colors cursor-pointer"
              title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
            </button>
          </div>

          {/* Navigation List */}
          {renderNavItems(false)}
        </div>

        {/* Footer Sign Out */}
        <div className="p-2 border-t border-[#C9D4E1]">
          {isCollapsed ? (
            <Tooltip content="Sign Out" position="right">
              <Link
                href={ADMIN_ROUTES.LOGIN}
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium text-[#8B2E2E] hover:bg-[#F5D9D9] transition-all cursor-pointer"
              >
                <LogOut className="h-4 w-4 shrink-0" />
              </Link>
            </Tooltip>
          ) : (
            <Link
              href={ADMIN_ROUTES.LOGIN}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium text-[#8B2E2E] hover:bg-[#F5D9D9] transition-all cursor-pointer"
            >
              <LogOut className="h-4 w-4 shrink-0" />
              <span>Sign Out</span>
            </Link>
          )}
        </div>
      </aside>

      {/* MOBILE SIDEBAR DRAWER (< 768px) */}
      {isMobileOpen && (
        <div className="md:hidden fixed inset-0 z-50 overflow-hidden">
          {/* Subtle backdrop overlay */}
          <div
            className="fixed inset-0 bg-[#17253A]/40 backdrop-blur-xs transition-opacity animate-in fade-in duration-200"
            onClick={onMobileClose}
          />

          {/* Sliding drawer panel */}
          <aside className="fixed inset-y-0 left-0 w-[240px] bg-[#EFF3F7] border-r border-[#C9D4E1] shadow-xl flex flex-col justify-between z-50 animate-in slide-in-from-left duration-200">
            <div>
              <div className="h-14 border-b border-[#C9D4E1] flex items-center justify-between px-4">
                <Link
                  href={ADMIN_ROUTES.DASHBOARD}
                  onClick={onMobileClose}
                  className="flex items-center gap-2.5"
                >
                  <div className="p-1.5 rounded-lg bg-[#2563A8] text-white shrink-0">
                    <Scale className="h-4 w-4" />
                  </div>
                  <div className="flex flex-col">
                    <span className="font-serif font-bold text-sm text-[#17253A] leading-tight">
                      Juris AI
                    </span>
                    <span className="font-mono text-[10px] text-[#2563A8] font-semibold tracking-wider">
                      ADMIN CONSOLE
                    </span>
                  </div>
                </Link>

                <button
                  onClick={onMobileClose}
                  className="p-1.5 rounded-md hover:bg-[#D9E7F5] text-[#526176] transition-colors"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {renderNavItems(true)}
            </div>

            <div className="p-3 border-t border-[#C9D4E1]">
              <Link
                href={ADMIN_ROUTES.LOGIN}
                onClick={onMobileClose}
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium text-[#8B2E2E] hover:bg-[#F5D9D9] transition-all"
              >
                <LogOut className="h-4 w-4 shrink-0" />
                <span>Sign Out</span>
              </Link>
            </div>
          </aside>
        </div>
      )}
    </>
  );
};
