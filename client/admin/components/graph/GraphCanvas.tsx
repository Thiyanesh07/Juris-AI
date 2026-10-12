'use client';

import React, { useState } from 'react';
import { useGraphStore } from '@/context/GraphStoreContext';
import { GraphNodeData, GraphEdgeData, GraphEntityType } from '@/data/graph';
import { ZoomIn, ZoomOut, Maximize2, Activity, AlertCircle, RefreshCw, GitFork } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/shared/EmptyState';
import { cn } from '@/lib/utils';

export const GraphCanvas: React.FC = () => {
  const {
    visibleNodes,
    visibleEdges,
    selectedNodeId,
    selectedEdgeId,
    selectNode,
    selectEdge,
    traversalPath,
    zoomLevel,
    zoomIn,
    zoomOut,
    panOffset,
    setPanOffset,
    resetView,
    isLoading,
    error,
    refreshGraph,
  } = useGraphStore();

  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [isPanning, setIsPanning] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  const handleMouseDown = (e: React.MouseEvent) => {
    const target = e.target as SVGElement;
    if (target.id === 'canvas-bg' || target.id === 'bg-grid' || target.tagName === 'svg' || target.tagName === 'line') {
      setIsPanning(true);
      setDragStart({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isPanning) {
      setPanOffset({
        x: Math.round(e.clientX - dragStart.x),
        y: Math.round(e.clientY - dragStart.y),
      });
    }
  };

  const handleMouseUp = () => setIsPanning(false);

  const nodeMap = new Map(visibleNodes.map((n) => [n.id, n]));
  const traversalSet = new Set(traversalPath);

  // SVG Marker Defs & Render Helpers
  const getNodeColor = (type: GraphEntityType): string => {
    switch (type) {
      case 'ARTICLE':
        return '#2563A8'; // Primary Slate Blue
      case 'ACT':
        return '#183B5B'; // Deep Navy
      case 'SECTION':
        return '#3B82D0'; // Bright Accent Blue
      case 'AMENDMENT':
        return '#7A5A0F'; // Warm Amber
      case 'JUDGMENT':
        return '#1E6B45'; // Success Green
      case 'COURT':
        return '#8B2E2E'; // Deep Red
      default:
        return '#526176';
    }
  };

  const renderNodeShape = (node: GraphNodeData, isSelected: boolean, isHighlighted: boolean) => {
    const color = getNodeColor(node.type);
    const strokeWidth = isSelected ? 3.5 : isHighlighted ? 2.5 : 1.5;
    const strokeColor = isSelected ? '#3B82D0' : isHighlighted ? '#17253A' : '#FFFFFF';

    switch (node.type) {
      case 'ARTICLE':
        return (
          <circle
            cx={node.x}
            cy={node.y}
            r={18}
            fill={color}
            stroke={strokeColor}
            strokeWidth={strokeWidth}
          />
        );
      case 'ACT':
        return (
          <rect
            x={node.x - 22}
            y={node.y - 15}
            width={44}
            height={30}
            rx={6}
            fill={color}
            stroke={strokeColor}
            strokeWidth={strokeWidth}
          />
        );
      case 'AMENDMENT':
        return (
          <polygon
            points={`${node.x},${node.y - 18} ${node.x + 18},${node.y} ${node.x},${node.y + 18} ${node.x - 18},${node.y}`}
            fill={color}
            stroke={strokeColor}
            strokeWidth={strokeWidth}
          />
        );
      case 'COURT':
        return (
          <polygon
            points={`${node.x - 10},${node.y - 16} ${node.x + 10},${node.y - 16} ${node.x + 18},${node.y} ${node.x + 10},${node.y + 16} ${node.x - 10},${node.y + 16} ${node.x - 18},${node.y}`}
            fill={color}
            stroke={strokeColor}
            strokeWidth={strokeWidth}
          />
        );
      case 'JUDGMENT':
        return (
          <circle
            cx={node.x}
            cy={node.y}
            r={16}
            fill={color}
            stroke={strokeColor}
            strokeWidth={strokeWidth}
          />
        );
      default:
        return (
          <rect
            x={node.x - 18}
            y={node.y - 12}
            width={36}
            height={24}
            rx={4}
            fill={color}
            stroke={strokeColor}
            strokeWidth={strokeWidth}
          />
        );
    }
  };

  // Loading State
  if (isLoading && visibleNodes.length === 0) {
    return (
      <div className="relative w-full h-[520px] bg-[#F5F7FA] rounded-2xl border border-[#C9D4E1] overflow-hidden flex flex-col items-center justify-center space-y-3 shadow-xs">
        <Activity className="h-8 w-8 text-[#2563A8] animate-spin" />
        <p className="font-mono text-xs text-[#526176]">Loading knowledge graph topology from Neo4j…</p>
      </div>
    );
  }

  // Error State
  if (error && visibleNodes.length === 0) {
    return (
      <div className="relative w-full h-[520px] bg-[#F5F7FA] rounded-2xl border border-[#C9D4E1] overflow-hidden flex flex-col items-center justify-center p-6 text-center space-y-3 shadow-xs">
        <div className="p-3 rounded-full bg-[#F5D9D9] text-[#8B2E2E]">
          <AlertCircle className="h-6 w-6" />
        </div>
        <h3 className="text-sm font-serif font-bold text-[#17253A]">Graph Query Failed</h3>
        <p className="text-xs font-mono text-[#8B2E2E] max-w-md">{error}</p>
        <Button variant="secondary" size="sm" onClick={refreshGraph} className="mt-2">
          <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
          Retry Connection
        </Button>
      </div>
    );
  }

  // Empty State
  if (!isLoading && visibleNodes.length === 0) {
    return (
      <div className="relative w-full h-[520px] bg-[#F5F7FA] rounded-2xl border border-[#C9D4E1] overflow-hidden flex flex-col items-center justify-center p-6 text-center shadow-xs">
        <EmptyState
          title="No Knowledge Graph Entities"
          description="No graph nodes or relationships matched the current search query or entity filter, or the Neo4j graph has not yet been populated."
          action={
            <Button variant="secondary" size="sm" onClick={resetView}>
              <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
              Reset Graph View
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="relative w-full h-[520px] bg-[#F5F7FA] rounded-2xl border border-[#C9D4E1] overflow-hidden select-none shadow-xs">
      {/* Canvas Top Bar Overlay */}
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2 bg-white/90 backdrop-blur-xs px-3 py-1.5 rounded-lg border border-[#C9D4E1] text-xs font-mono">
        <span className="h-2 w-2 rounded-full bg-[#1E6B45]" />
        <span className="font-semibold text-[#17253A]">Legal Knowledge Graph Canvas</span>
        <span className="text-[#718096]">({visibleNodes.length} nodes • {Math.round(zoomLevel * 100)}%)</span>
        {isLoading && <Activity className="h-3 w-3 text-[#2563A8] animate-spin ml-1" />}
      </div>

      {/* Canvas Controls Overlay */}
      <div className="absolute top-3 right-3 z-10 flex items-center gap-1.5 bg-white/90 backdrop-blur-xs p-1 rounded-lg border border-[#C9D4E1] shadow-xs">
        <button
          onClick={zoomIn}
          className="p-1.5 rounded hover:bg-[#EFF3F7] text-[#526176] transition-colors cursor-pointer"
          title="Zoom In"
        >
          <ZoomIn className="h-4 w-4" />
        </button>
        <button
          onClick={zoomOut}
          className="p-1.5 rounded hover:bg-[#EFF3F7] text-[#526176] transition-colors cursor-pointer"
          title="Zoom Out"
        >
          <ZoomOut className="h-4 w-4" />
        </button>
        <button
          onClick={resetView}
          className="p-1.5 rounded hover:bg-[#EFF3F7] text-[#526176] transition-colors cursor-pointer"
          title="Fit & Reset View"
        >
          <Maximize2 className="h-4 w-4" />
        </button>
      </div>

      {/* SVG Canvas Area */}
      <div
        className={cn(
          "w-full h-full overflow-hidden flex items-center justify-center select-none",
          isPanning ? "cursor-grabbing" : "cursor-grab"
        )}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <svg
          viewBox="0 0 1000 650"
          className="w-full h-full"
        >
          <defs>
            <marker
              id="arrow-default"
              viewBox="0 0 10 10"
              refX="22"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#718096" />
            </marker>

            <marker
              id="arrow-highlighted"
              viewBox="0 0 10 10"
              refX="22"
              refY="5"
              markerWidth="7"
              markerHeight="7"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#2563A8" />
            </marker>
          </defs>

          {/* Interactive Background Rect for Pan Dragging */}
          <rect id="canvas-bg" width="1000" height="650" fill="transparent" />

          {/* Transform Viewport Layer */}
          <g
            id="canvas-viewport"
            style={{
              transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${zoomLevel})`,
              transformOrigin: '500px 325px',
              transition: isPanning ? 'none' : 'transform 120ms ease-out',
            }}
          >
            {/* Background Grid Pattern */}
            <g id="bg-grid" opacity="0.35">
              <line x1="0" y1="162" x2="1000" y2="162" stroke="#D9E1EA" strokeDasharray="4 4" />
              <line x1="0" y1="325" x2="1000" y2="325" stroke="#D9E1EA" strokeDasharray="4 4" />
              <line x1="0" y1="487" x2="1000" y2="487" stroke="#D9E1EA" strokeDasharray="4 4" />
              <line x1="250" y1="0" x2="250" y2="650" stroke="#D9E1EA" strokeDasharray="4 4" />
              <line x1="500" y1="0" x2="500" y2="650" stroke="#D9E1EA" strokeDasharray="4 4" />
              <line x1="750" y1="0" x2="750" y2="650" stroke="#D9E1EA" strokeDasharray="4 4" />
            </g>

            {/* Edges Layer */}
            <g id="edges-layer">
              {visibleEdges.map((edge) => {
                const src = nodeMap.get(edge.source);
                const tgt = nodeMap.get(edge.target);
                if (!src || !tgt) return null;

                const isEdgeSelected = edge.id === selectedEdgeId;
                const isPathHighlighted =
                  traversalSet.has(edge.source) && traversalSet.has(edge.target);

                const stroke = isEdgeSelected
                  ? '#3B82D0'
                  : isPathHighlighted
                  ? '#2563A8'
                  : '#94A3B8';
                const strokeWidth = isEdgeSelected ? 3 : isPathHighlighted ? 2.5 : 1.5;
                const strokeDasharray = isPathHighlighted ? 'none' : '4 3';

                const midX = (src.x + tgt.x) / 2;
                const midY = (src.y + tgt.y) / 2;
                const pillWidth = Math.max(56, edge.relationship.length * 6.5 + 12);

                return (
                  <g key={edge.id} className="cursor-pointer" onClick={() => selectEdge(edge.id)}>
                    <line
                      x1={src.x}
                      y1={src.y}
                      x2={tgt.x}
                      y2={tgt.y}
                      stroke={stroke}
                      strokeWidth={strokeWidth}
                      strokeDasharray={strokeDasharray}
                      markerEnd={isPathHighlighted ? 'url(#arrow-highlighted)' : 'url(#arrow-default)'}
                    />
                    <rect
                      x={midX - pillWidth / 2}
                      y={midY - 8}
                      width={pillWidth}
                      height={16}
                      rx={4}
                      fill="#FFFFFF"
                      stroke={stroke}
                      strokeWidth={1}
                      opacity={0.92}
                    />
                    <text
                      x={midX}
                      y={midY + 3.5}
                      textAnchor="middle"
                      fontSize="8.5"
                      fontFamily="monospace"
                      fontWeight="bold"
                      fill={isPathHighlighted ? '#2563A8' : '#526176'}
                      className="pointer-events-none"
                    >
                      {edge.relationship}
                    </text>
                  </g>
                );
              })}
            </g>

            {/* Nodes Layer */}
            <g id="nodes-layer">
              {visibleNodes.map((node) => {
                const isSelected = node.id === selectedNodeId;
                const isHovered = node.id === hoveredNodeId;
                const isPathHighlighted = traversalSet.has(node.id);
                const displayLabel = node.label.length > 25 ? `${node.label.slice(0, 23)}…` : node.label;

                return (
                  <g
                    key={node.id}
                    onClick={() => selectNode(node.id)}
                    onMouseEnter={() => setHoveredNodeId(node.id)}
                    onMouseLeave={() => setHoveredNodeId(null)}
                    className="cursor-pointer transition-all duration-150"
                  >
                    <title>{`${node.label} (${node.type})`}</title>
                    {isSelected && (
                      <circle
                        cx={node.x}
                        cy={node.y}
                        r={26}
                        fill="none"
                        stroke="#3B82D0"
                        strokeWidth="2"
                        strokeDasharray="3 3"
                        className="animate-spin"
                        style={{ animationDuration: '6s' }}
                      />
                    )}

                    {renderNodeShape(node, isSelected, isPathHighlighted)}

                    <text
                      x={node.x}
                      y={node.y + 4}
                      textAnchor="middle"
                      fontSize="10"
                      fontFamily="monospace"
                      fontWeight="bold"
                      fill="#FFFFFF"
                      className="pointer-events-none"
                    >
                      {node.type.substring(0, 3)}
                    </text>

                    <text
                      x={node.x}
                      y={node.y + 32}
                      textAnchor="middle"
                      fontSize="11"
                      fontFamily="sans-serif"
                      fontWeight={isSelected ? 'bold' : '500'}
                      fill={isSelected ? '#2563A8' : '#17253A'}
                      className="pointer-events-none drop-shadow-xs"
                    >
                      {displayLabel}
                    </text>
                  </g>
                );
              })}
            </g>
          </g>
        </svg>
      </div>

      {/* Traversal Active Sequence Banner */}
      {traversalPath.length > 0 && selectedNodeId && (
        <div className="absolute bottom-3 left-3 right-3 z-10 p-2.5 rounded-xl bg-white/95 backdrop-blur-xs border border-[#C9D4E1] shadow-xs flex flex-wrap items-center justify-between text-xs font-mono">
          <div className="flex items-center gap-2">
            <span className="font-bold text-[#2563A8]">Active Multi-Hop Chain:</span>
            <div className="flex items-center gap-1 overflow-x-auto max-w-xl">
              {traversalPath.map((nid, index) => {
                const targetNode = nodeMap.get(nid);
                if (!targetNode) return null;
                return (
                  <React.Fragment key={nid}>
                    {index > 0 && <span className="text-[#718096]">&rarr;</span>}
                    <span
                      onClick={() => selectNode(nid)}
                      className={cn(
                        'px-2 py-0.5 rounded cursor-pointer transition-colors',
                        nid === selectedNodeId
                          ? 'bg-[#2563A8] text-white font-bold'
                          : 'bg-[#EFF3F7] text-[#17253A] hover:bg-[#D9E7F5]'
                      )}
                    >
                      {targetNode.label.split(' ')[0]} {targetNode.identifier.split(' ')[0]}
                    </span>
                  </React.Fragment>
                );
              })}
            </div>
          </div>
          <span className="text-[11px] text-[#718096]">Depth: {traversalPath.length - 1} Hops</span>
        </div>
      )}
    </div>
  );
};
