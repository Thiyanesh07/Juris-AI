import React from 'react';
import { useGraphStore } from '@/context/GraphStoreContext';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { Search, RotateCcw, GitFork, SlidersHorizontal, Layers } from 'lucide-react';

export const GraphToolbar: React.FC = () => {
  const {
    searchQuery,
    setSearchQuery,
    entityTypeFilter,
    setEntityTypeFilter,
    relationTypeFilter,
    setRelationTypeFilter,
    traversalDepth,
    setTraversalDepth,
    resetView,
  } = useGraphStore();

  return (
    <div className="p-3.5 rounded-xl bg-[#EFF3F7] border border-[#C9D4E1] flex flex-col md:flex-row items-center justify-between gap-3 shadow-xs">
      {/* Search Input */}
      <div className="relative w-full md:w-72">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[#718096]" />
        <Input
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search node e.g. Article 21, IPC..."
          density="dense"
          className="pl-8 bg-white text-xs"
        />
      </div>

      {/* Filters & Depth Selector */}
      <div className="flex flex-wrap items-center gap-2.5 w-full md:w-auto justify-end">
        {/* Entity Type Filter */}
        <div className="flex items-center gap-1 text-xs font-mono text-[#526176]">
          <Select
            density="dense"
            value={entityTypeFilter}
            onChange={(e) => setEntityTypeFilter(e.target.value)}
            className="w-32 bg-white text-xs"
          >
            <option value="ALL">All Entities</option>
            <option value="ARTICLE">Article</option>
            <option value="ACT">Act</option>
            <option value="SECTION">Section</option>
            <option value="AMENDMENT">Amendment</option>
            <option value="JUDGMENT">Judgment</option>
            <option value="COURT">Court</option>
          </Select>
        </div>

        {/* Relation Type Filter */}
        <div className="flex items-center gap-1 text-xs font-mono text-[#526176]">
          <Select
            density="dense"
            value={relationTypeFilter}
            onChange={(e) => setRelationTypeFilter(e.target.value)}
            className="w-36 bg-white text-xs"
          >
            <option value="ALL">All Relations</option>
            <option value="BELONGS_TO">BELONGS_TO</option>
            <option value="CONTAINS">CONTAINS</option>
            <option value="AMENDS">AMENDS</option>
            <option value="MODIFIES">MODIFIES</option>
            <option value="INTERPRETS">INTERPRETS</option>
            <option value="REFERENCES">REFERENCES</option>
            <option value="OVERRULES">OVERRULES</option>
            <option value="CONFLICTS_WITH">CONFLICTS_WITH</option>
          </Select>
        </div>

        {/* Multi-Hop Depth Selector */}
        <div className="flex items-center gap-1 bg-white border border-[#C5D5E8] rounded-md px-2 py-1 text-xs font-mono">
          <Layers className="h-3.5 w-3.5 text-[#2563A8]" />
          <span className="text-[#526176]">Depth:</span>
          {[1, 2, 3].map((d) => (
            <button
              key={d}
              onClick={() => setTraversalDepth(d)}
              className={`px-1.5 py-0.5 rounded text-[11px] font-bold cursor-pointer transition-colors ${
                traversalDepth === d
                  ? 'bg-[#2563A8] text-white'
                  : 'text-[#526176] hover:bg-[#EFF3F7]'
              }`}
            >
              {d}
            </button>
          ))}
        </div>

        {/* Reset View */}
        <Button variant="ghost" size="sm" onClick={resetView} className="text-xs text-[#526176]">
          <RotateCcw className="h-3.5 w-3.5 mr-1" />
          Reset Graph
        </Button>
      </div>
    </div>
  );
};
