'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useResearchStore } from '@/context/ResearchStoreContext';
import { ResearchMode, ResearchHistoryRecord } from '@/lib/types';
import { formatDate, truncate } from '@/lib/utils';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import {
  Clock,
  Search,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  ArrowRight,
  Bookmark,
  Calendar,
  Filter,
} from 'lucide-react';

export default function HistoryPage() {
  const router = useRouter();
  const { history, openHistorySession } = useResearchStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMode, setSelectedMode] = useState<ResearchMode | 'ALL'>('ALL');

  const filteredHistory = history.filter(record => {
    if (selectedMode !== 'ALL' && record.mode !== selectedMode) return false;
    if (searchQuery.trim() !== '') {
      return record.query.toLowerCase().includes(searchQuery.toLowerCase());
    }
    return true;
  });

  const getCitationBadge = (status: ResearchHistoryRecord['citationStatus']) => {
    switch (status) {
      case 'ALL_VERIFIED':
        return <Badge variant="success"><CheckCircle2 className="h-2.5 w-2.5 mr-1" />Verified</Badge>;
      case 'PARTIAL':
        return <Badge variant="warning"><AlertCircle className="h-2.5 w-2.5 mr-1" />Partial</Badge>;
      default:
        return <Badge variant="default"><HelpCircle className="h-2.5 w-2.5 mr-1" />Unverified</Badge>;
    }
  };

  const handleOpen = (recordId: string) => {
    openHistorySession(recordId);
    router.push('/research');
  };

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto space-y-6 pb-20">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#E2E8F0] pb-4">
        <div>
          <h1 className="text-2xl text-[#17253A] flex items-center gap-2">
            <Clock className="h-6 w-6 text-[#1D4E8A]" />
            Research History
          </h1>
          <p className="text-xs font-mono text-[#526176] mt-0.5">
            Audit log of all legal research sessions executed in your workspace
          </p>
        </div>

        <Badge variant="primary" className="h-7 px-3 text-xs">
          {history.length} Saved Sessions
        </Badge>
      </div>

      {/* Controls Bar */}
      <div className="card p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="relative flex-1">
          <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#718096]" />
          <input
            type="text"
            placeholder="Search past research queries..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="input-field pl-9 text-xs h-9"
          />
        </div>

        <div className="flex items-center gap-1 bg-[#F0F4F8] p-1 rounded-lg border border-[#CBD5E0]">
          {(['ALL', 'COMPREHENSIVE', 'CONSTITUTIONAL', 'STATUTORY', 'CASE_LAW'] as const).map(mode => (
            <button
              key={mode}
              onClick={() => setSelectedMode(mode)}
              className={`px-2.5 py-1 text-[11px] font-mono rounded-md font-medium transition-colors cursor-pointer ${
                selectedMode === mode
                  ? 'bg-white text-[#1D4E8A] shadow-xs font-bold'
                  : 'text-[#526176] hover:text-[#17253A]'
              }`}
            >
              {mode === 'ALL' ? 'All Modes' : mode}
            </button>
          ))}
        </div>
      </div>

      {/* History List */}
      <div className="space-y-3">
        {filteredHistory.length === 0 ? (
          <div className="card p-12 text-center text-xs font-mono text-[#718096] space-y-2">
            <p>No research sessions match your criteria.</p>
          </div>
        ) : (
          filteredHistory.map(record => (
            <div
              key={record.id}
              onClick={() => handleOpen(record.id)}
              className="card p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 cursor-pointer hover:border-[#1D4E8A] hover:shadow-md transition-all group"
            >
              <div className="space-y-1.5 flex-1 min-w-0">
                <p className="text-sm font-semibold text-[#17253A] group-hover:text-[#1D4E8A] transition-colors line-clamp-2">
                  {record.query}
                </p>
                <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-[#718096]">
                  <span className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    {formatDate(record.createdAt)}
                  </span>
                  <span>·</span>
                  <Badge variant="default">{record.mode}</Badge>
                  <span>·</span>
                  <span>{record.sourcesCount} Authorities Fused</span>
                </div>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                {getCitationBadge(record.citationStatus)}
                {record.saved && (
                  <Badge variant="primary">
                    <Bookmark className="h-2.5 w-2.5 mr-0.5" /> Saved
                  </Badge>
                )}
                <Button variant="ghost" size="sm" className="gap-1 font-mono text-xs">
                  Re-open <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
