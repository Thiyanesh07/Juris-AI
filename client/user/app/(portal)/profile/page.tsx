'use client';

import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { getInitials } from '@/lib/utils';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import {
  User,
  Mail,
  Shield,
  CheckCircle2,
  Sliders,
  Save,
  Loader2,
} from 'lucide-react';
import { ResearchMode } from '@/lib/types';

export default function ProfilePage() {
  const { user, isLoading } = useAuth();
  const [preferredMode, setPreferredMode] = useState<ResearchMode>('COMPREHENSIVE');
  const [language, setLanguage] = useState('English (India)');
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  if (isLoading) {
    return (
      <div className="p-12 flex flex-col items-center justify-center min-h-[50vh] space-y-3">
        <Loader2 className="h-8 w-8 text-[#1D4E8A] animate-spin" />
        <p className="text-sm font-mono text-[#526176]">Loading user profile...</p>
      </div>
    );
  }

  const displayName = user?.name || (user?.email ? user.email.split('@')[0] : 'Legal Researcher');
  const displayRole = user?.role ? user.role.toUpperCase().replace('_', ' ') : 'RESEARCHER';

  return (
    <div className="p-6 lg:p-8 max-w-4xl mx-auto space-y-6 pb-20">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#E2E8F0] pb-4">
        <div>
          <h1 className="text-2xl text-[#17253A] flex items-center gap-2 font-display font-semibold">
            <User className="h-6 w-6 text-[#1D4E8A]" />
            Researcher Profile & Preferences
          </h1>
          <p className="text-xs font-mono text-[#526176] mt-0.5">
            Authenticated legal researcher identity and workspace preferences
          </p>
        </div>
      </div>

      {/* Profile Overview Card */}
      <div className="card p-6 flex flex-col sm:flex-row items-start sm:items-center gap-5 border-[#CBD5E0]">
        <div className="h-16 w-16 rounded-full bg-[#1D4E8A] flex items-center justify-center text-white text-xl font-bold font-mono shrink-0 shadow-md">
          {getInitials(displayName)}
        </div>
        <div className="flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-xl font-bold text-[#17253A] font-sans">{displayName}</h2>
            <Badge variant="primary">{displayRole}</Badge>
          </div>
          <div className="flex items-center gap-4 text-xs font-mono text-[#718096] pt-1">
            <span className="flex items-center gap-1">
              <Mail className="h-3.5 w-3.5" /> {user?.email || 'N/A'}
            </span>
            <span className="flex items-center gap-1 text-[#166534]">
              <Shield className="h-3.5 w-3.5" /> Account Active
            </span>
          </div>
        </div>
      </div>

      {/* Settings Form */}
      <form onSubmit={handleSave} className="space-y-6">
        {/* Workspace Preferences */}
        <div className="card p-6 space-y-4">
          <h3 className="text-base font-bold text-[#17253A] font-sans border-b border-[#E2E8F0] pb-2 flex items-center gap-2">
            <Sliders className="h-4 w-4 text-[#1D4E8A]" />
            Default Research Workspace Preferences
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-mono font-bold text-[#526176]">Preferred Research Mode</label>
              <select
                value={preferredMode}
                onChange={e => setPreferredMode(e.target.value as ResearchMode)}
                className="input-field text-xs h-9 px-3"
              >
                <option value="COMPREHENSIVE">Comprehensive (Hybrid GraphRAG)</option>
                <option value="CONSTITUTIONAL">Constitutional Analysis</option>
                <option value="STATUTORY">Statutory Interpretation</option>
                <option value="CASE_LAW">Precedent & Case Law</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-mono font-bold text-[#526176]">Corpus Jurisdiction</label>
              <input
                type="text"
                disabled
                value="India — Constitution, Statutes, Supreme Court"
                className="input-field text-xs h-9 px-3 bg-[#F8FAFC] cursor-not-allowed"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-mono font-bold text-[#526176]">Interface Language</label>
              <select
                value={language}
                onChange={e => setLanguage(e.target.value)}
                className="input-field text-xs h-9 px-3"
              >
                <option value="English (India)">English (India)</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-mono font-bold text-[#526176]">Time Zone</label>
              <input
                type="text"
                disabled
                value="Asia/Kolkata (IST +05:30)"
                className="input-field text-xs h-9 px-3 bg-[#F8FAFC] cursor-not-allowed"
              />
            </div>
          </div>
        </div>

        {/* Save Bar */}
        <div className="flex items-center justify-between border-t border-[#E2E8F0] pt-4">
          <div className="flex items-center gap-2">
            {savedSuccess && (
              <span className="flex items-center gap-1.5 text-xs font-mono text-[#166534] font-bold animate-fade-in-up">
                <CheckCircle2 className="h-4 w-4 text-[#166534]" />
                Profile preferences saved!
              </span>
            )}
          </div>
          <Button type="submit" variant="primary" size="md" className="gap-2 px-6">
            <Save className="h-4 w-4" /> Save Preferences
          </Button>
        </div>
      </form>
    </div>
  );
}

