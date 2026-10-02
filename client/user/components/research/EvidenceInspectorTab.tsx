'use client';

import React, { useState } from 'react';
import { EvidenceItem, RetrievalSource, EntityType } from '@/lib/types';
import { Badge } from '@/components/ui/Badge';
import { Filter, Layers, Search, Database, Scale, BookOpen } from 'lucide-react';

interface EvidenceTabProps {
  evidence: EvidenceItem[];
}

export const EvidenceInspectorTab: React.FC<EvidenceTabProps> = ({ evidence }) => {
  const [sourceFilter, setSourceFilter] = useState<RetrievalSource | 'ALL'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredEvidence = evidence.filter(item => {
    if (sourceFilter !== 'ALL' && item.retrievalSource !== sourceFilter) return false;
    if (searchQuery.trim() !== '') {
      const q = searchQuery.toLowerCase();
      return (
        item.entityName.toLowerCase().includes(q) ||
        item.sourceDocumentTitle.toLowerCase().includes(q) ||
        item.excerpt.toLowerCase().includes(q) ||
        item.provision.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const getSourceBadge = (source: RetrievalSource) => {
    switch (source) {
      case 'VECTOR':
        return <Badge variant="vector">Vector Dense</Badge>;
      case 'GRAPH':
        return <Badge variant="graph">Graph Traversal</Badge>;
      case 'HYBRID':
        return <Badge variant="hybrid">Hybrid Fused</Badge>;
    }
  };

  const getEntityIcon = (type: EntityType) => {
    switch (type) {
      case 'ARTICLE':
      case 'SECTION':
        return <Scale className="h-4 w-4 text-[#1D4E8A]" />;
      case 'JUDGMENT':
        return <BookOpen className="h-4 w-4 text-[#7C3AED]" />;
      default:
        return <Database className="h-4 w-4 text-[#0284C7]" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Controls */}
      <div className="card p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Layers className="h-5 w-5 text-[#1D4E8A]" />
          <div>
            <h2 className="text-base font-bold text-[#17253A] font-sans">Retrieved Evidence Fragments</h2>
            <p className="text-xs text-[#526176] font-mono">
              Showing {filteredEvidence.length} of {evidence.length} evidence items fused from hybrid retrieval.
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search className="h-3.5 w-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#718096]" />
            <input
              type="text"
              placeholder="Search evidence..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="input-field pl-8 text-xs h-8 w-44"
            />
          </div>

          <div className="flex items-center gap-1 bg-[#F0F4F8] p-1 rounded-lg border border-[#CBD5E0]">
            {(['ALL', 'HYBRID', 'VECTOR', 'GRAPH'] as const).map(mode => (
              <button
                key={mode}
                onClick={() => setSourceFilter(mode)}
                className={`px-2.5 py-1 text-[11px] font-mono rounded-md font-medium transition-colors cursor-pointer ${
                  sourceFilter === mode
                    ? 'bg-white text-[#1D4E8A] shadow-xs font-bold'
                    : 'text-[#526176] hover:text-[#17253A]'
                }`}
              >
                {mode}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Evidence Grid */}
      {filteredEvidence.length === 0 ? (
        <div className="card p-8 text-center space-y-2">
          <Layers className="h-8 w-8 text-[#CBD5E0] mx-auto" />
          <p className="text-sm font-bold text-[#526176]">No evidence items</p>
          <p className="text-xs text-[#718096] font-mono">
            {evidence.length === 0
              ? 'The backend returned no evidence for this query.'
              : 'No items match the current filter.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredEvidence.map(item => (
            <div key={item.id} className="card p-5 space-y-3 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-md bg-[#F0F4F8] border border-[#CBD5E0]">
                    {getEntityIcon(item.entityType)}
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-[#17253A] font-sans">{item.entityName}</h3>
                    <p className="text-[11px] font-mono text-[#718096]">
                      {item.sourceDocumentTitle} {item.year ? `(${item.year})` : ''}
                    </p>
                  </div>
                </div>
                {getSourceBadge(item.retrievalSource)}
              </div>

              <div className="bg-[#F8FAFC] p-3 rounded-lg border border-[#E2E8F0] font-serif text-xs leading-relaxed text-[#17253A]">
                "{item.excerpt}"
              </div>

              <div className="flex items-center justify-between text-[11px] font-mono text-[#718096] pt-1 border-t border-[#E2E8F0]">
                <span>Source: {item.provision}</span>
                <span className="font-bold text-[#1D4E8A]">
                  {/* Show hybrid score from backend */}
                  Score: {(item.relevanceScore * 100).toFixed(0)}%
                </span>
              </div>

              {/* Rank from backend */}
              {item.rank !== undefined && (
                <div className="text-[10px] font-mono text-[#718096]">
                  Rank #{item.rank} · Chunk {item.chunkId?.substring(0, 8)}…
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
