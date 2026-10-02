'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useResearchStore } from '@/context/ResearchStoreContext';
import { formatDate } from '@/lib/utils';
import { SavedResearch } from '@/lib/types';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import {
  Bookmark,
  Search,
  Trash2,
  Edit2,
  ExternalLink,
  BookOpen,
  Tag,
  ArrowRight,
} from 'lucide-react';

export default function SavedResearchPage() {
  const router = useRouter();
  const { savedResearch, removeSavedResearch, renameSavedResearch, openHistorySession } = useResearchStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [editingItem, setEditingItem] = useState<SavedResearch | null>(null);
  const [editTitle, setEditTitle] = useState('');

  const filteredSaved = savedResearch.filter(item => {
    if (searchQuery.trim() !== '') {
      const q = searchQuery.toLowerCase();
      return (
        item.title.toLowerCase().includes(q) ||
        item.query.toLowerCase().includes(q) ||
        item.summary.toLowerCase().includes(q) ||
        item.tags.some(t => t.toLowerCase().includes(q))
      );
    }
    return true;
  });

  const handleOpen = (item: SavedResearch) => {
    router.push(`/research?q=${encodeURIComponent(item.query)}`);
  };

  const handleRenameSubmit = () => {
    if (!editingItem || !editTitle.trim()) return;
    renameSavedResearch(editingItem.id, editTitle.trim());
    setEditingItem(null);
  };

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto space-y-6 pb-20">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#E2E8F0] pb-4">
        <div>
          <h1 className="text-2xl text-[#17253A] flex items-center gap-2">
            <Bookmark className="h-6 w-6 text-[#1D4E8A]" />
            Saved Research Workspace
          </h1>
          <p className="text-xs font-mono text-[#526176] mt-0.5">
            Bookmarked legal research briefs, authorities, and summaries
          </p>
        </div>

        <Badge variant="primary" className="h-7 px-3 text-xs">
          {savedResearch.length} Saved Items
        </Badge>
      </div>

      {/* Controls Bar */}
      <div className="card p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="relative flex-1">
          <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#718096]" />
          <input
            type="text"
            placeholder="Search saved research by title, query, tag, or authority..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="input-field pl-9 text-xs h-9"
          />
        </div>
      </div>

      {/* Saved Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filteredSaved.length === 0 ? (
          <div className="col-span-full card p-12 text-center text-xs font-mono text-[#718096]">
            No saved research briefs match your search.
          </div>
        ) : (
          filteredSaved.map(item => (
            <div
              key={item.id}
              className="card p-5 space-y-4 flex flex-col justify-between hover:shadow-md hover:border-[#1D4E8A]/40 transition-all"
            >
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-sm font-bold text-[#17253A] font-sans leading-snug line-clamp-2">
                    {item.title}
                  </h3>
                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      onClick={() => {
                        setEditingItem(item);
                        setEditTitle(item.title);
                      }}
                      className="p-1 rounded text-[#718096] hover:bg-[#F0F4F8] hover:text-[#17253A] transition-colors cursor-pointer"
                      title="Rename"
                    >
                      <Edit2 className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => removeSavedResearch(item.id)}
                      className="p-1 rounded text-[#718096] hover:bg-[#FEE2E2] hover:text-[#7F1D1D] transition-colors cursor-pointer"
                      title="Remove"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>

                <Badge variant="default" className="text-[10px]">
                  {item.mode}
                </Badge>

                <p className="text-xs text-[#526176] leading-relaxed line-clamp-3 font-sans">
                  {item.summary}
                </p>

                {/* Key Authorities */}
                <div className="bg-[#F8FAFC] p-2.5 rounded-lg border border-[#E2E8F0] space-y-1">
                  <p className="text-[10px] font-mono font-bold text-[#718096] uppercase">Key Authorities</p>
                  <ul className="space-y-0.5 text-[11px] font-mono text-[#17253A]">
                    {item.authorities.map((auth, idx) => (
                      <li key={idx} className="truncate">· {auth}</li>
                    ))}
                  </ul>
                </div>

                {/* Tags */}
                <div className="flex flex-wrap gap-1">
                  {item.tags.map(tag => (
                    <span key={tag} className="badge badge-default text-[10px]">
                      <Tag className="h-2.5 w-2.5 mr-0.5" />
                      {tag}
                    </span>
                  ))}
                </div>
              </div>

              {/* Footer */}
              <div className="flex items-center justify-between text-xs font-mono text-[#718096] pt-3 border-t border-[#E2E8F0]">
                <span>{formatDate(item.savedAt)}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleOpen(item)}
                  className="gap-1 font-semibold text-[#1D4E8A]"
                >
                  View Workspace <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* RENAME DIALOG */}
      <Dialog
        isOpen={!!editingItem}
        onClose={() => setEditingItem(null)}
        title="Rename Saved Research Brief"
        description="Update the title of your saved research item for workspace organization."
        footer={
          <>
            <Button variant="secondary" onClick={() => setEditingItem(null)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={handleRenameSubmit}>
              Save Title
            </Button>
          </>
        }
      >
        <div className="space-y-2">
          <label className="text-xs font-mono font-bold text-[#526176]">Brief Title</label>
          <input
            type="text"
            value={editTitle}
            onChange={e => setEditTitle(e.target.value)}
            className="input-field text-xs h-9 px-3"
          />
        </div>
      </Dialog>
    </div>
  );
}
