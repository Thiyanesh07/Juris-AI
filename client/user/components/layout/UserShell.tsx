'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Scale,
  Search,
  Clock,
  Bookmark,
  User,
  Plus,
  Menu,
  X,
  ChevronDown,
  LogOut,
  Settings,
  Sparkles,
  ShieldAlert,
  Loader2,
} from 'lucide-react';
import { cn, getInitials } from '@/lib/utils';
import { useAuth } from '@/context/AuthContext';

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  { href: '/home', label: 'Research Home', icon: <Scale className="h-4 w-4" /> },
  { href: '/research', label: 'Research', icon: <Search className="h-4 w-4" /> },
  { href: '/history', label: 'History', icon: <Clock className="h-4 w-4" /> },
  { href: '/saved', label: 'Saved Research', icon: <Bookmark className="h-4 w-4" /> },
  { href: '/profile', label: 'Profile', icon: <User className="h-4 w-4" /> },
];

interface UserShellProps {
  children: React.ReactNode;
}

export const UserShell: React.FC<UserShellProps> = ({ children }) => {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const { user, isLoading, logout } = useAuth();

  useEffect(() => {
    if (!isLoading && !user) {
      window.location.href = `/login?from=${encodeURIComponent(pathname)}`;
    }
  }, [user, isLoading, pathname]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#F0F4F8] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-[#1D4E8A]" />
      </div>
    );
  }

  if (!user) return null;

  const userName = user?.name || 'Legal Researcher';
  const userRole = user?.role || 'USER';

  return (
    <div className="min-h-screen flex bg-[#F0F4F8]">
      {/* DESKTOP SIDEBAR */}
      <aside className="hidden lg:flex flex-col w-56 shrink-0 fixed left-0 top-0 h-full bg-white border-r border-[#CBD5E0] z-30">
        {/* Brand */}
        <div className="flex items-center gap-2.5 px-5 py-5 border-b border-[#E2E8F0]">
          <div className="h-7 w-7 rounded-lg bg-[#1D4E8A] flex items-center justify-center">
            <Scale className="h-4 w-4 text-white" />
          </div>
          <div>
            <span className="text-sm font-bold text-[#17253A]" style={{ fontFamily: 'var(--font-dm-serif, serif)' }}>
              Juris AI
            </span>
            <p className="text-[10px] text-[#718096] font-mono leading-none mt-0.5">Research Portal</p>
          </div>
        </div>

        {/* New Research CTA */}
        <div className="px-3 pt-4 pb-2">
          <Link
            href="/research"
            className="flex items-center justify-center gap-2 w-full h-9 bg-[#1D4E8A] text-white text-sm font-semibold rounded-lg hover:bg-[#132F52] transition-colors"
          >
            <Plus className="h-4 w-4" />
            New Research
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-2 space-y-0.5">
          {NAV_ITEMS.map(item => {
            const active = pathname === item.href || (item.href !== '/home' && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn('nav-item', active && 'nav-item-active')}
              >
                {item.icon}
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* User Profile Area */}
        <div className="border-t border-[#E2E8F0] p-3 relative">
          <button
            onClick={() => setUserMenuOpen(v => !v)}
            className="w-full flex items-center gap-2.5 p-2 rounded-lg hover:bg-[#F0F4F8] transition-colors cursor-pointer"
          >
            <div className="h-8 w-8 rounded-full bg-[#1D4E8A] flex items-center justify-center text-white text-xs font-bold shrink-0">
              {getInitials(userName)}
            </div>
            <div className="flex-1 text-left min-w-0">
              <p className="text-xs font-semibold text-[#17253A] truncate">{userName}</p>
              <p className="text-[10px] text-[#718096] font-mono truncate">{userRole}</p>
            </div>
            <ChevronDown className="h-3.5 w-3.5 text-[#718096] shrink-0" />
          </button>

          {/* User dropdown */}
          {userMenuOpen && (
            <div className="absolute bottom-16 left-3 right-3 bg-white rounded-xl border border-[#CBD5E0] shadow-lg z-50 overflow-hidden">
              <Link
                href="/profile"
                onClick={() => setUserMenuOpen(false)}
                className="flex items-center gap-2 px-3 py-2.5 text-xs text-[#526176] hover:bg-[#F0F4F8] transition-colors"
              >
                <User className="h-3.5 w-3.5" />
                View Profile
              </Link>
              <div className="border-t border-[#E2E8F0]" />
              <button
                onClick={() => logout()}
                className="w-full flex items-center gap-2 px-3 py-2.5 text-xs text-[#7F1D1D] hover:bg-[#FEE2E2] transition-colors cursor-pointer"
              >
                <LogOut className="h-3.5 w-3.5" />
                Sign Out
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* MOBILE TOPBAR */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-40 h-14 bg-white border-b border-[#CBD5E0] flex items-center justify-between px-4">
        <div className="flex items-center gap-2.5">
          <div className="h-7 w-7 rounded-lg bg-[#1D4E8A] flex items-center justify-center">
            <Scale className="h-4 w-4 text-white" />
          </div>
          <span className="text-sm font-bold text-[#17253A]" style={{ fontFamily: 'var(--font-dm-serif, serif)' }}>
            Juris AI
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/research"
            className="flex items-center gap-1 h-8 px-3 bg-[#1D4E8A] text-white text-xs font-semibold rounded-lg"
          >
            <Plus className="h-3.5 w-3.5" /> Research
          </Link>
          <button
            onClick={() => setMobileOpen(true)}
            className="p-2 rounded-lg text-[#526176] hover:bg-[#F0F4F8] cursor-pointer"
          >
            <Menu className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* MOBILE DRAWER */}
      {mobileOpen && (
        <>
          <div className="fixed inset-0 bg-black/40 z-40 lg:hidden" onClick={() => setMobileOpen(false)} />
          <div className="fixed top-0 right-0 bottom-0 w-64 bg-white z-50 lg:hidden shadow-xl flex flex-col">
            <div className="flex items-center justify-between px-4 py-4 border-b border-[#E2E8F0]">
              <span className="font-bold text-[#17253A]">Menu</span>
              <button onClick={() => setMobileOpen(false)} className="p-1 text-[#718096] cursor-pointer">
                <X className="h-5 w-5" />
              </button>
            </div>
            <nav className="flex-1 p-3 space-y-0.5">
              {NAV_ITEMS.map(item => {
                const active = pathname === item.href || (item.href !== '/home' && pathname.startsWith(item.href));
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileOpen(false)}
                    className={cn('nav-item', active && 'nav-item-active')}
                  >
                    {item.icon}
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>
            <div className="border-t border-[#E2E8F0] p-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-full bg-[#1D4E8A] flex items-center justify-center text-white text-xs font-bold shrink-0">
                  {getInitials(userName)}
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-[#17253A] truncate">{userName}</p>
                  <p className="text-[10px] text-[#718096] font-mono truncate">{userRole}</p>
                </div>
              </div>
              <button
                onClick={() => logout()}
                className="p-1.5 text-red-600 hover:bg-red-50 rounded-lg cursor-pointer"
                title="Sign Out"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        </>
      )}

      {/* MAIN CONTENT */}
      <main className="flex-1 lg:ml-56 pt-14 lg:pt-0 min-h-screen">
        {children}
      </main>
    </div>
  );
};

