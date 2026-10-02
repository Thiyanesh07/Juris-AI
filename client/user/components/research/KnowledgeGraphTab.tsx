'use client';

import React, { useState } from 'react';
import { GraphNode, GraphEdge, ReasoningStep, EntityType } from '@/lib/types';
import { Badge } from '@/components/ui/Badge';
import { GitFork, Layers, Info, Sparkles } from 'lucide-react';

interface GraphTabProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  reasoningSteps: ReasoningStep[];
  graphAvailable: boolean;
  selectedNodeId: string | null;
  onSelectNode: (id: string | null) => void;
}

export const KnowledgeGraphTab: React.FC<GraphTabProps> = ({
  nodes,
  edges,
  reasoningSteps,
  graphAvailable,
  selectedNodeId,
  onSelectNode,
}) => {
  const selectedNode = nodes.find(n => n.id === selectedNodeId);

  const getNodeColor = (type: EntityType | 'QUERY' | 'INTERPRETATION', isSeed?: boolean, isQuery?: boolean) => {
    if (isQuery) return { bg: '#1D4E8A', stroke: '#132F52', text: '#FFFFFF' };
    if (isSeed) return { bg: '#2563A8', stroke: '#1D4E8A', text: '#FFFFFF' };
    switch (type) {
      case 'ARTICLE':
      case 'SECTION':
        return { bg: '#DBEAFE', stroke: '#3B82D0', text: '#1E40AF' };
      case 'JUDGMENT':
        return { bg: '#F3E8FF', stroke: '#A855F7', text: '#6B21A8' };
      case 'ACT':
        return { bg: '#FEF3C7', stroke: '#F59E0B', text: '#92400E' };
      default:
        return { bg: '#E2E8F0', stroke: '#94A3B8', text: '#334155' };
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* GRAPH VISUALIZER */}
      <div className="lg:col-span-8 space-y-4">
        <div className="card p-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <GitFork className="h-5 w-5 text-[#1D4E8A]" />
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
            <div className="flex items-center gap-2 text-xs font-mono">
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-[#1D4E8A]" /> Query</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-[#3B82D0]" /> Seed Article</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-[#A855F7]" /> Authority</span>
            </div>
          )}
        </div>

        {/* Graph Canvas — only rendered when graph data is available */}
        {graphAvailable ? (<div className="card p-4 bg-[#F8FAFC] relative overflow-hidden min-h-[460px] flex items-center justify-center border-[#CBD5E0]">
          <svg className="w-full h-[440px] pointer-events-auto">
            <defs>
              <marker
                id="arrowhead"
                markerWidth="8"
                markerHeight="6"
                refX="18"
                refY="3"
                orient="auto"
              >
                <polygon points="0 0, 8 3, 0 6" fill="#94A3B8" />
              </marker>
            </defs>

            {/* Edges */}
            {edges.map(edge => {
              const source = nodes.find(n => n.id === edge.sourceId);
              const target = nodes.find(n => n.id === edge.targetId);
              if (!source || !target) return null;

              const midX = (source.x + target.x) / 2;
              const midY = (source.y + target.y) / 2;

              return (
                <g key={edge.id}>
                  <line
                    x1={source.x}
                    y1={source.y}
                    x2={target.x}
                    y2={target.y}
                    stroke="#CBD5E0"
                    strokeWidth="2"
                    strokeDasharray={edge.label === 'INTERPRETS' ? 'none' : '4 4'}
                    markerEnd="url(#arrowhead)"
                  />
                  <rect
                    x={midX - 35}
                    y={midY - 9}
                    width="70"
                    height="18"
                    rx="4"
                    fill="#FFFFFF"
                    stroke="#E2E8F0"
                  />
                  <text
                    x={midX}
                    y={midY + 3}
                    textAnchor="middle"
                    className="text-[9px] font-mono fill-[#526176] font-bold"
                  >
                    {edge.label}
                  </text>
                </g>
              );
            })}

            {/* Nodes */}
            {nodes.map(node => {
              const color = getNodeColor(node.type, node.isSeed, node.isQuery);
              const isSelected = node.id === selectedNodeId;

              return (
                <g
                  key={node.id}
                  transform={`translate(${node.x}, ${node.y})`}
                  onClick={() => onSelectNode(isSelected ? null : node.id)}
                  className="cursor-pointer transition-transform duration-200 hover:scale-110"
                >
                  <circle
                    r={node.isQuery ? 24 : 20}
                    fill={color.bg}
                    stroke={isSelected ? '#17253A' : color.stroke}
                    strokeWidth={isSelected ? 3 : 2}
                    className="shadow-sm"
                  />
                  <text
                    y={node.isQuery ? 35 : 32}
                    textAnchor="middle"
                    className={`text-[11px] font-sans font-bold ${
                      isSelected ? 'fill-[#17253A] underline' : 'fill-[#17253A]'
                    }`}
                  >
                    {node.label}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
        ) : (
          /* Graph data unavailable — backend does not yet expose graph HTTP endpoints */
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
                onClick={() => onSelectNode(null)}
                className="text-xs text-[#718096] hover:text-[#17253A] underline font-mono cursor-pointer"
              >
                Clear
              </button>
            </div>
            <h4 className="text-sm font-bold text-[#17253A] font-sans mb-1">{selectedNode.label}</h4>
            <div className="flex items-center gap-2 mb-3">
              <Badge variant="primary">{selectedNode.type}</Badge>
              {selectedNode.isSeed && <Badge variant="warning">Seed Entity</Badge>}
              {selectedNode.isQuery && <Badge variant="success">Query Seed</Badge>}
            </div>
            <p className="text-xs text-[#526176] leading-relaxed">
              Entity indexed in the Juris AI Legal Knowledge Graph with multi-hop connections to related articles, precedents, and amendments.
            </p>
          </div>
        ) : (
          <div className="p-4 rounded-xl bg-white border border-[#CBD5E0] text-center text-xs font-mono text-[#718096]">
            Click any graph node on the canvas to inspect entity properties and relationship links.
          </div>
        )}

        {/* Reasoning Steps List */}
        <div className="card p-5 space-y-3">
          <h3 className="text-sm font-bold text-[#17253A] font-sans flex items-center gap-1.5 border-b border-[#E2E8F0] pb-2">
            <Sparkles className="h-4 w-4 text-[#1D4E8A]" />
            Multi-Hop Reasoning Traversal Log
          </h3>
          <div className="space-y-3 max-h-[440px] overflow-y-auto pr-1">
            {reasoningSteps.map(step => (
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
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
