'use client';

import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { GraphNode, GraphEdge, ReasoningStep, EntityType } from '@/lib/types';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import {
  GitFork,
  Sparkles,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Table as TableIcon,
  Eye,
  RotateCcw,
  Layers,
  ArrowRight,
  Info,
  CheckCircle2,
} from 'lucide-react';
import {
  layoutGraphNodes,
  calculateGraphBounds,
  calculateFitToView,
  formatNodeDisplayLabel,
  GraphBounds,
} from '@/lib/graphLayout';

interface GraphTabProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  reasoningSteps: ReasoningStep[];
  graphAvailable: boolean;
  selectedNodeId: string | null;
  onSelectNode: (id: string | null) => void;
}

export const KnowledgeGraphTab: React.FC<GraphTabProps> = ({
  nodes: propNodes,
  edges,
  reasoningSteps,
  graphAvailable,
  selectedNodeId,
  onSelectNode,
}) => {
  // Clear stale selection if selected node does not exist in current nodes
  useEffect(() => {
    if (selectedNodeId && !propNodes.some((n) => n.id === selectedNodeId)) {
      onSelectNode(null);
    }
  }, [selectedNodeId, propNodes, onSelectNode]);

  // Apply deterministic, collision-free layout
  const nodes = useMemo(() => {
    return layoutGraphNodes(propNodes, edges);
  }, [propNodes, edges]);

  // Active selected node
  const selectedNode = nodes.find((n) => n.id === selectedNodeId);

  // View mode: Visual Graph vs Accessible Structured Table
  const [viewMode, setViewMode] = useState<'visual' | 'table'>('visual');

  // Interactive Viewport State: Zoom & Pan
  const [zoomLevel, setZoomLevel] = useState<number>(1.0);
  const [panOffset, setPanOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);

  // Compute graph bounding box
  const bounds: GraphBounds = useMemo(() => {
    return calculateGraphBounds(nodes, 80);
  }, [nodes]);

  // Fit to view calculation
  const fitView = useCallback(() => {
    const container = containerRef.current;
    const width = container ? container.clientWidth : 800;
    const height = container ? container.clientHeight : 440;
    const transform = calculateFitToView(bounds, width, height, 0.45, 1.4);
    setZoomLevel(transform.zoom);
    setPanOffset({ x: transform.panX, y: transform.panY });
  }, [bounds]);

  // Auto-fit on initial graph mount or graph size change
  useEffect(() => {
    if (graphAvailable && nodes.length > 0) {
      fitView();
    }
  }, [graphAvailable, nodes.length, fitView]);

  // Zoom handlers
  const handleZoomIn = () => setZoomLevel((prev) => Math.min(2.5, Number((prev + 0.15).toFixed(2))));
  const handleZoomOut = () => setZoomLevel((prev) => Math.max(0.4, Number((prev - 0.15).toFixed(2))));
  const handleReset = () => fitView();

  // Pan handlers
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

  // Color mapping
  const getNodeColor = (type: EntityType | 'QUERY' | 'INTERPRETATION', isSeed?: boolean, isQuery?: boolean) => {
    if (isQuery) return { bg: '#1D4E8A', stroke: '#132F52', text: '#FFFFFF', pill: '#DBEAFE' };
    if (isSeed) return { bg: '#2563A8', stroke: '#1D4E8A', text: '#FFFFFF', pill: '#E0E7FF' };
    switch (type) {
      case 'ARTICLE':
      case 'SECTION':
        return { bg: '#DBEAFE', stroke: '#3B82D0', text: '#1E40AF', pill: '#BFDBFE' };
      case 'JUDGMENT':
        return { bg: '#F3E8FF', stroke: '#A855F7', text: '#6B21A8', pill: '#E9D5FF' };
      case 'AMENDMENT':
        return { bg: '#FEE2E2', stroke: '#EF4444', text: '#991B1B', pill: '#FECACA' };
      case 'COURT':
        return { bg: '#E0E7FF', stroke: '#6366F1', text: '#3730A3', pill: '#C7D2FE' };
      case 'ACT':
        return { bg: '#FEF3C7', stroke: '#F59E0B', text: '#92400E', pill: '#FDE68A' };
      case 'PRINCIPLE':
        return { bg: '#ECFDF5', stroke: '#10B981', text: '#065F46', pill: '#A7F3D0' };
      case 'RULE':
        return { bg: '#F1F5F9', stroke: '#64748B', text: '#334155', pill: '#E2E8F0' };
      default:
        return { bg: '#E2E8F0', stroke: '#94A3B8', text: '#334155', pill: '#CBD5E0' };
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* GRAPH VISUALIZER / WORKSPACE */}
      <div className="lg:col-span-8 space-y-4">
        {/* Header Toolbar */}
        <div className="card p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <GitFork className="h-5 w-5 text-[#1D4E8A] shrink-0" />
            <div>
              <h2 className="text-base font-bold text-[#17253A] font-sans">Multi-Hop Graph Reasoning Path</h2>
              <p className="text-xs text-[#526176] font-mono">
                {graphAvailable
                  ? `Interactive traversal subgraph (${nodes.length} entities, ${edges.length} typed relationships)`
                  : 'Graph data not available for this result'}
              </p>
            </div>
          </div>

          {graphAvailable && (
            <div className="flex items-center gap-2">
              {/* View Mode Toggle: Canvas vs Table */}
              <div className="flex items-center bg-[#F0F4F8] p-1 rounded-lg border border-[#CBD5E0] text-xs font-mono">
                <button
                  type="button"
                  onClick={() => setViewMode('visual')}
                  className={`px-2.5 py-1 rounded flex items-center gap-1.5 transition-colors cursor-pointer ${
                    viewMode === 'visual'
                      ? 'bg-white text-[#1D4E8A] font-bold shadow-xs'
                      : 'text-[#526176] hover:text-[#17253A]'
                  }`}
                  aria-pressed={viewMode === 'visual'}
                >
                  <Eye className="h-3.5 w-3.5" /> Canvas
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('table')}
                  className={`px-2.5 py-1 rounded flex items-center gap-1.5 transition-colors cursor-pointer ${
                    viewMode === 'table'
                      ? 'bg-white text-[#1D4E8A] font-bold shadow-xs'
                      : 'text-[#526176] hover:text-[#17253A]'
                  }`}
                  aria-pressed={viewMode === 'table'}
                  aria-label="View structured table alternative"
                >
                  <TableIcon className="h-3.5 w-3.5" /> Structured List
                </button>
              </div>

              {/* Visual Legend indicator */}
              <div className="hidden xl:flex items-center gap-2 text-xs font-mono border-l border-[#CBD5E0] pl-3">
                <span className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#1D4E8A]" /> Query
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#3B82D0]" /> Seed
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#A855F7]" /> Authority
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Graph Content Area */}
        {graphAvailable ? (
          viewMode === 'visual' ? (
            /* Visual SVG Canvas with Zoom & Pan */
            <div
              ref={containerRef}
              className="card relative overflow-hidden h-[480px] bg-[#F8FAFC] border-[#CBD5E0] select-none"
            >
              {/* Canvas Controls Overlay */}
              <div className="absolute top-3 right-3 z-10 flex items-center gap-1 bg-white/95 backdrop-blur-xs p-1 rounded-lg border border-[#CBD5E0] shadow-xs">
                <button
                  type="button"
                  onClick={handleZoomIn}
                  className="p-1.5 rounded hover:bg-[#EFF3F7] text-[#526176] transition-colors cursor-pointer"
                  title="Zoom In (+)"
                  aria-label="Zoom in graph"
                >
                  <ZoomIn className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  onClick={handleZoomOut}
                  className="p-1.5 rounded hover:bg-[#EFF3F7] text-[#526176] transition-colors cursor-pointer"
                  title="Zoom Out (-)"
                  aria-label="Zoom out graph"
                >
                  <ZoomOut className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  onClick={handleReset}
                  className="p-1.5 rounded hover:bg-[#EFF3F7] text-[#526176] transition-colors cursor-pointer"
                  title="Fit to View"
                  aria-label="Fit graph to view"
                >
                  <Maximize2 className="h-4 w-4" />
                </button>
              </div>

              {/* Status / Zoom level badge */}
              <div className="absolute bottom-3 left-3 z-10 flex items-center gap-2 bg-white/95 backdrop-blur-xs px-2.5 py-1 rounded-md border border-[#CBD5E0] text-[11px] font-mono text-[#526176]">
                <span className="w-2 h-2 rounded-full bg-[#10B981]" />
                <span>Zoom: {Math.round(zoomLevel * 100)}%</span>
                <span>•</span>
                <span>Pan: Click & Drag</span>
                <span>•</span>
                <span>Tab: Keyboard Navigation</span>
              </div>

              {/* SVG Canvas */}
              <div
                className={`w-full h-full overflow-hidden flex items-center justify-center ${
                  isPanning ? 'cursor-grabbing' : 'cursor-grab'
                }`}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
              >
                <svg
                  className="w-full h-full"
                  role="graphics-document"
                  aria-label="Knowledge Graph Visualization Canvas"
                >
                  <defs>
                    <marker
                      id="arrowhead"
                      markerWidth="8"
                      markerHeight="6"
                      refX="22"
                      refY="3"
                      orient="auto-start-reverse"
                    >
                      <polygon points="0 0, 8 3, 0 6" fill="#94A3B8" />
                    </marker>
                    <marker
                      id="arrowhead-active"
                      markerWidth="9"
                      markerHeight="7"
                      refX="22"
                      refY="3.5"
                      orient="auto-start-reverse"
                    >
                      <polygon points="0 0, 9 3.5, 0 7" fill="#1D4E8A" />
                    </marker>
                  </defs>

                  {/* Interactive Background Rect for Pan Dragging */}
                  <rect id="canvas-bg" width="100%" height="100%" fill="transparent" />

                  {/* Transform Viewport Layer */}
                  <g
                    id="graph-viewport"
                    style={{
                      transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${zoomLevel})`,
                      transformOrigin: '0 0',
                      transition: isPanning ? 'none' : 'transform 120ms ease-out',
                    }}
                  >
                    {/* Background Subtle Grid */}
                    <g id="bg-grid" opacity="0.3">
                      <line x1="-1000" y1="300" x2="2000" y2="300" stroke="#CBD5E0" strokeDasharray="4 4" />
                      <line x1="500" y1="-1000" x2="500" y2="2000" stroke="#CBD5E0" strokeDasharray="4 4" />
                    </g>

                    {/* Edges Layer */}
                    <g id="edges-group">
                      {edges.map((edge) => {
                        const source = nodes.find((n) => n.id === edge.sourceId);
                        const target = nodes.find((n) => n.id === edge.targetId);
                        if (!source || !target) return null;

                        const isConnectedToSelected =
                          selectedNodeId === edge.sourceId || selectedNodeId === edge.targetId;

                        const midX = (source.x + target.x) / 2;
                        const midY = (source.y + target.y) / 2;
                        const pillWidth = Math.max(50, edge.label.length * 6 + 14);

                        return (
                          <g key={edge.id} className="transition-all">
                            <line
                              x1={source.x}
                              y1={source.y}
                              x2={target.x}
                              y2={target.y}
                              stroke={isConnectedToSelected ? '#1D4E8A' : '#CBD5E0'}
                              strokeWidth={isConnectedToSelected ? '2.5' : '1.5'}
                              strokeDasharray={edge.label === 'INTERPRETS' ? 'none' : '4 4'}
                              markerEnd={isConnectedToSelected ? 'url(#arrowhead-active)' : 'url(#arrowhead)'}
                            />
                            <rect
                              x={midX - pillWidth / 2}
                              y={midY - 8}
                              width={pillWidth}
                              height={16}
                              rx={4}
                              fill="#FFFFFF"
                              stroke={isConnectedToSelected ? '#1D4E8A' : '#E2E8F0'}
                              strokeWidth={isConnectedToSelected ? 1.5 : 1}
                              opacity={0.95}
                            />
                            <text
                              x={midX}
                              y={midY + 3}
                              textAnchor="middle"
                              className={`text-[8.5px] font-mono font-bold select-none pointer-events-none ${
                                isConnectedToSelected ? 'fill-[#1D4E8A]' : 'fill-[#526176]'
                              }`}
                            >
                              {edge.label}
                            </text>
                          </g>
                        );
                      })}
                    </g>

                    {/* Nodes Layer */}
                    <g id="nodes-group">
                      {nodes.map((node) => {
                        const color = getNodeColor(node.type, node.isSeed, node.isQuery);
                        const isSelected = node.id === selectedNodeId;
                        const isFocused = node.id === focusedNodeId;
                        const labelInfo = formatNodeDisplayLabel(node.label, 18);

                        return (
                          <g
                            key={node.id}
                            transform={`translate(${node.x}, ${node.y})`}
                            onClick={() => onSelectNode(isSelected ? null : node.id)}
                            onFocus={() => setFocusedNodeId(node.id)}
                            onBlur={() => setFocusedNodeId(null)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter' || e.key === ' ') {
                                e.preventDefault();
                                onSelectNode(isSelected ? null : node.id);
                              }
                            }}
                            tabIndex={0}
                            role="button"
                            aria-label={`Entity: ${node.label}, type: ${node.type}${
                              node.isSeed ? ', seed authority' : ''
                            }${isSelected ? ', selected' : ''}`}
                            aria-pressed={isSelected}
                            className="cursor-pointer transition-transform duration-150 focus:outline-hidden group"
                          >
                            <title>{`${node.label} (${node.type})`}</title>

                            {/* Focus / Selection Ring Indicator */}
                            {(isSelected || isFocused) && (
                              <circle
                                r={node.isQuery ? 32 : 28}
                                fill="none"
                                stroke={isSelected ? '#1D4E8A' : '#3B82D0'}
                                strokeWidth={isSelected ? 3 : 2}
                                strokeDasharray="3 3"
                                className="animate-spin"
                                style={{ animationDuration: '8s' }}
                              />
                            )}

                            {/* Node Circle */}
                            <circle
                              r={node.isQuery ? 24 : 20}
                              fill={color.bg}
                              stroke={isSelected ? '#17253A' : color.stroke}
                              strokeWidth={isSelected ? 3 : 2}
                              className="shadow-sm transition-all group-hover:scale-105"
                            />

                            {/* Node Type Abbreviation inside circle */}
                            <text
                              y={3}
                              textAnchor="middle"
                              fontSize="9"
                              fontFamily="monospace"
                              fontWeight="bold"
                              fill={color.text}
                              className="pointer-events-none select-none"
                            >
                              {node.isQuery ? 'QUERY' : node.type.substring(0, 3)}
                            </text>

                            {/* Collision-protected Node Label */}
                            <text
                              y={node.isQuery ? 36 : 32}
                              textAnchor="middle"
                              className={`text-[11px] font-sans select-none pointer-events-none drop-shadow-xs ${
                                isSelected ? 'fill-[#1D4E8A] font-bold underline' : 'fill-[#17253A] font-semibold'
                              }`}
                            >
                              {labelInfo.displayLabel}
                            </text>
                          </g>
                        );
                      })}
                    </g>
                  </g>
                </svg>
              </div>
            </div>
          ) : (
            /* Structured Accessible Table Alternative */
            <div className="card p-5 space-y-4 bg-white border-[#CBD5E0]">
              <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-3">
                <div className="flex items-center gap-2">
                  <TableIcon className="h-4 w-4 text-[#1D4E8A]" />
                  <h3 className="text-sm font-bold text-[#17253A] font-sans">
                    Accessible Graph Entities & Relationships Table
                  </h3>
                </div>
                <span className="text-xs font-mono text-[#526176]">{nodes.length} entities</span>
              </div>

              <div className="overflow-x-auto max-h-[440px]">
                <table className="w-full text-left text-xs font-sans">
                  <thead>
                    <tr className="border-b border-[#CBD5E0] bg-[#F8FAFC] text-[#526176] font-mono text-[10px] uppercase tracking-wider">
                      <th className="py-2.5 px-3">Entity Name</th>
                      <th className="py-2.5 px-3">Type</th>
                      <th className="py-2.5 px-3">Role</th>
                      <th className="py-2.5 px-3">Connected Links</th>
                      <th className="py-2.5 px-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E2E8F0]">
                    {nodes.map((node) => {
                      const isSelected = node.id === selectedNodeId;
                      const connectedEdges = edges.filter(
                        (e) => e.sourceId === node.id || e.targetId === node.id
                      );

                      return (
                        <tr
                          key={node.id}
                          className={`hover:bg-[#F0F4F8] transition-colors ${
                            isSelected ? 'bg-[#F4F8FC] font-semibold' : ''
                          }`}
                        >
                          <td className="py-2.5 px-3 text-[#17253A] font-medium">
                            {node.label}
                          </td>
                          <td className="py-2.5 px-3">
                            <Badge variant="primary">{node.type}</Badge>
                          </td>
                          <td className="py-2.5 px-3 font-mono text-[11px] text-[#526176]">
                            {node.isQuery ? 'Query Seed' : node.isSeed ? 'Seed Entity' : 'Graph Authority'}
                          </td>
                          <td className="py-2.5 px-3 font-mono text-[11px] text-[#526176]">
                            {connectedEdges.length} relationship{connectedEdges.length === 1 ? '' : 's'}
                          </td>
                          <td className="py-2.5 px-3 text-right">
                            <Button
                              variant={isSelected ? 'primary' : 'secondary'}
                              size="sm"
                              onClick={() => onSelectNode(isSelected ? null : node.id)}
                              className="text-xs h-7 px-2.5"
                            >
                              {isSelected ? 'Selected' : 'Inspect'}
                            </Button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )
        ) : (
          /* Graph data unavailable state */
          <div className="card p-8 bg-[#F8FAFC] min-h-[300px] flex flex-col items-center justify-center gap-4 border-[#CBD5E0] border-dashed">
            <GitFork className="h-10 w-10 text-[#CBD5E0]" />
            <div className="text-center space-y-2">
              <p className="text-sm font-bold text-[#526176] font-sans">Knowledge Graph Unavailable</p>
              <p className="text-xs text-[#718096] font-mono max-w-md">
                Graph node and edge data is not included in the current backend QA response.
                The Juris AI Neo4j graph is used internally for hybrid retrieval but graph
                HTTP endpoints are not yet exposed. This tab will become live in a future phase.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* REASONING STEPS & NODE DETAILS */}
      <div className="lg:col-span-4 space-y-4">
        {/* Node Inspector */}
        {selectedNode ? (
          <div className="card p-5 border-[#1D4E8A] bg-[#F4F8FC] shadow-md animate-fade-in-up">
            <div className="flex items-center justify-between mb-3 border-b border-[#CBD5E0] pb-2">
              <span className="text-xs font-mono font-bold text-[#1D4E8A]">Graph Node Inspector</span>
              <button
                type="button"
                onClick={() => onSelectNode(null)}
                className="text-xs text-[#718096] hover:text-[#17253A] underline font-mono cursor-pointer"
                aria-label="Clear selected node"
              >
                Clear Selection
              </button>
            </div>
            <h4 className="text-sm font-bold text-[#17253A] font-sans mb-1">{selectedNode.label}</h4>
            <div className="flex flex-wrap items-center gap-2 mb-3">
              <Badge variant="primary">{selectedNode.type}</Badge>
              {selectedNode.isSeed && <Badge variant="warning">Seed Entity</Badge>}
              {selectedNode.isQuery && <Badge variant="success">Query Seed</Badge>}
            </div>
            <p className="text-xs text-[#526176] leading-relaxed mb-3">
              Entity indexed in the Juris AI Legal Knowledge Graph with multi-hop connections to related articles, precedents, and amendments.
            </p>
            {(() => {
              const connectedEdges = edges.filter(
                (e) => e.sourceId === selectedNode.id || e.targetId === selectedNode.id
              );
              if (connectedEdges.length === 0) return null;
              return (
                <div className="pt-2.5 border-t border-[#CBD5E0] space-y-1.5">
                  <span className="text-[10px] font-mono font-bold text-[#526176] uppercase tracking-wider block">
                    Connected Relationships ({connectedEdges.length})
                  </span>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                    {connectedEdges.map((edge) => {
                      const isSource = edge.sourceId === selectedNode.id;
                      const otherId = isSource ? edge.targetId : edge.sourceId;
                      const other = nodes.find((n) => n.id === otherId);
                      const otherLabel = other?.label || otherId;
                      return (
                        <div
                          key={edge.id}
                          onClick={() => other && onSelectNode(other.id)}
                          onKeyDown={(e) => {
                            if ((e.key === 'Enter' || e.key === ' ') && other) {
                              e.preventDefault();
                              onSelectNode(other.id);
                            }
                          }}
                          tabIndex={0}
                          role="button"
                          aria-label={`Jump to connected entity ${otherLabel} via ${edge.label}`}
                          className="text-[11px] font-mono text-[#17253A] flex items-center justify-between bg-white p-2 rounded border border-[#CBD5E0] hover:border-[#1D4E8A] hover:bg-[#F0F4F8] cursor-pointer transition-colors"
                        >
                          <span className="font-bold text-[#1D4E8A]">{edge.label}</span>
                          <span className="text-[#718096] text-[10px]">
                            {isSource ? '→ outgoing to' : '← incoming from'}
                          </span>
                          <span className="truncate max-w-[120px] font-semibold text-right" title={otherLabel}>
                            {otherLabel}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })()}
          </div>
        ) : (
          <div className="p-4 rounded-xl bg-white border border-[#CBD5E0] text-center text-xs font-mono text-[#718096]">
            Click any graph node or table item to inspect entity properties and relationship links.
          </div>
        )}

        {/* Reasoning Steps List */}
        <div className="card p-5 space-y-3">
          <h3 className="text-sm font-bold text-[#17253A] font-sans flex items-center gap-1.5 border-b border-[#E2E8F0] pb-2">
            <Sparkles className="h-4 w-4 text-[#1D4E8A]" />
            Multi-Hop Reasoning Traversal Log
          </h3>
          <div className="space-y-3 max-h-[440px] overflow-y-auto pr-1">
            {reasoningSteps.length === 0 ? (
              <p className="text-xs font-mono text-[#718096] py-2 text-center">
                No reasoning steps recorded for this graph.
              </p>
            ) : (
              reasoningSteps.map((step) => (
                <div key={step.step} className="p-3 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0] space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[10px] font-bold text-[#1D4E8A]">Step {step.step}</span>
                    {step.relationLabel && <Badge variant="graph">{step.relationLabel}</Badge>}
                  </div>
                  <p className="text-xs text-[#17253A] leading-relaxed">{step.description}</p>
                  {step.targetEntityName && (
                    <p className="text-[11px] font-mono text-[#526176]">
                      → Target: <span className="font-bold text-[#17253A]">{step.targetEntityName}</span>
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
