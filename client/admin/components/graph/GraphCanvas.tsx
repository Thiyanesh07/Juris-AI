'use client';

import React, { useState } from 'react';
import { useGraphStore } from '@/context/GraphStoreContext';
import { GraphNodeData, GraphEdgeData, GraphEntityType } from '@/data/graph';
import { ZoomIn, ZoomOut, Maximize2, Move } from 'lucide-react';
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
    resetView,
  } = useGraphStore();

  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

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
        // Circle shape
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
        // Rounded rectangle
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
        // Diamond shape
        return (
          <polygon
            points={`${node.x},${node.y - 18} ${node.x + 18},${node.y} ${node.x},${node.y + 18} ${node.x - 18},${node.y}`}
            fill={color}
            stroke={strokeColor}
            strokeWidth={strokeWidth}
          />
        );
      case 'COURT':
        // Hexagon shape
        return (
          <polygon
            points={`${node.x - 10},${node.y - 16} ${node.x + 10},${node.y - 16} ${node.x + 18},${node.y} ${node.x + 10},${node.y + 16} ${node.x - 10},${node.y + 16} ${node.x - 18},${node.y}`}
            fill={color}
            stroke={strokeColor}
            strokeWidth={strokeWidth}
          />
        );
      case 'JUDGMENT':
      case 'SECTION':
      default:
        // Compact rounded rect
        return (
          <rect
            x={node.x - 20}
            y={node.y - 14}
            width={40}
            height={28}
            rx={4}
            fill={color}
            stroke={strokeColor}
            strokeWidth={strokeWidth}
          />
        );
    }
  };

  return (
    <div className="relative w-full h-[520px] bg-[#F5F7FA] rounded-2xl border border-[#C9D4E1] overflow-hidden select-none shadow-xs">
      {/* Canvas Top Bar Overlay */}
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2 bg-white/90 backdrop-blur-xs px-3 py-1.5 rounded-lg border border-[#C9D4E1] text-xs font-mono">
        <span className="h-2 w-2 rounded-full bg-[#1E6B45]" />
        <span className="font-semibold text-[#17253A]">Legal Knowledge Graph Canvas</span>
        <span className="text-[#718096]">({visibleNodes.length} nodes)</span>
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
      <div className="w-full h-full overflow-hidden flex items-center justify-center">
        <svg
          viewBox="0 0 1000 650"
          className="w-full h-full transition-transform duration-200 ease-out"
          style={{ transform: `scale(${zoomLevel})` }}
        >
          <defs>
            {/* Arrow Marker Definitions */}
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

          {/* BACKGROUND GRID PATTERN */}
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#E7EDF4" strokeWidth="0.8" />
          </pattern>
          <rect width="1000" height="650" fill="url(#grid)" />

          {/* RENDER EDGES */}
          <g className="edges">
            {visibleEdges.map((edge) => {
              const sourceNode = nodeMap.get(edge.source);
              const targetNode = nodeMap.get(edge.target);

              if (!sourceNode || !targetNode) return null;

              const isEdgeSelected = selectedEdgeId === edge.id;
              const isPathHighlighted =
                traversalSet.has(edge.source) && traversalSet.has(edge.target);

              const isHovered =
                hoveredNodeId === edge.source || hoveredNodeId === edge.target;

              const strokeColor = isEdgeSelected
                ? '#3B82D0'
                : isPathHighlighted
                ? '#2563A8'
                : isHovered
                ? '#17253A'
                : '#C9D4E1';

              const strokeWidth = isEdgeSelected ? 3 : isPathHighlighted ? 2.5 : isHovered ? 2 : 1.2;
              const opacity = isPathHighlighted || isHovered || !selectedNodeId ? 1 : 0.35;

              // Midpoint for relationship label
              const midX = (sourceNode.x + targetNode.x) / 2;
              const midY = (sourceNode.y + targetNode.y) / 2;

              return (
                <g
                  key={edge.id}
                  onClick={(e) => {
                    e.stopPropagation();
                    selectEdge(edge.id);
                  }}
                  className="cursor-pointer group"
                  style={{ opacity }}
                >
                  <line
                    x1={sourceNode.x}
                    y1={sourceNode.y}
                    x2={targetNode.x}
                    y2={targetNode.y}
                    stroke={strokeColor}
                    strokeWidth={strokeWidth}
                    strokeDasharray={edge.relationship === 'CONFLICTS_WITH' ? '4 3' : undefined}
                    markerEnd={
                      isPathHighlighted || isEdgeSelected
                        ? 'url(#arrow-highlighted)'
                        : 'url(#arrow-default)'
                    }
                  />

                  {/* Relationship Label Tag */}
                  {(isPathHighlighted || isHovered || isEdgeSelected) && (
                    <g transform={`translate(${midX}, ${midY})`}>
                      <rect
                        x="-36"
                        y="-8"
                        width="72"
                        height="16"
                        rx="4"
                        fill="#FFFFFF"
                        stroke={strokeColor}
                        strokeWidth="1"
                        className="shadow-xs"
                      />
                      <text
                        x="0"
                        y="3"
                        textAnchor="middle"
                        fontSize="9"
                        fontFamily="monospace"
                        fontWeight="bold"
                        fill="#17253A"
                      >
                        {edge.relationship}
                      </text>
                    </g>
                  )}
                </g>
              );
            })}
          </g>

          {/* RENDER NODES */}
          <g className="nodes">
            {visibleNodes.map((node) => {
              const isSelected = selectedNodeId === node.id;
              const isPathHighlighted = traversalSet.has(node.id);
              const isHovered = hoveredNodeId === node.id;
              const opacity = isPathHighlighted || isHovered || !selectedNodeId ? 1 : 0.4;

              return (
                <g
                  key={node.id}
                  onClick={(e) => {
                    e.stopPropagation();
                    selectNode(node.id);
                  }}
                  onMouseEnter={() => setHoveredNodeId(node.id)}
                  onMouseLeave={() => setHoveredNodeId(null)}
                  className="cursor-pointer transition-transform duration-150 group"
                  style={{ opacity }}
                >
                  {/* Outer Glow Ring for Selected Node */}
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

                  {/* Node Shape */}
                  {renderNodeShape(node, isSelected, isPathHighlighted)}

                  {/* Node Type Initial Badge inside Shape */}
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

                  {/* Node Label Below */}
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
                    {node.label}
                  </text>
                </g>
              );
            })}
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
