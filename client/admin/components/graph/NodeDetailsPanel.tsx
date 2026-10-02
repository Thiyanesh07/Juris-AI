'use client';

import React from 'react';
import Link from 'next/link';
import { useGraphStore } from '@/context/GraphStoreContext';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ADMIN_DYNAMIC_ROUTES } from '@/constants/routes';
import {
  GitFork,
  FileText,
  ArrowRight,
  ArrowLeft,
  ExternalLink,
} from 'lucide-react';

export const NodeDetailsPanel: React.FC = () => {
  const {
    getSelectedNode,
    getSelectedEdge,
    getNodeRelationships,
    selectNode,
    startTraversal,
    traversalDepth,
  } = useGraphStore();

  const selectedNode = getSelectedNode();
  const selectedEdge = getSelectedEdge();

  if (!selectedNode && !selectedEdge) {
    return (
      <div className="p-6 rounded-2xl bg-white border border-[#C9D4E1] shadow-xs text-center space-y-3">
        <div className="p-3 rounded-full bg-[#D9E7F5] text-[#2563A8] w-fit mx-auto">
          <GitFork className="h-6 w-6" />
        </div>
        <h3 className="text-sm font-serif font-bold text-[#17253A]">Entity Inspector</h3>
        <p className="text-xs text-[#526176] max-w-xs mx-auto">
          Click any node or relationship edge on the canvas to inspect legal metadata and multi-hop connections.
        </p>
      </div>
    );
  }

  if (selectedNode) {
    const { incoming, outgoing } = getNodeRelationships(selectedNode.id);

    return (
      <div className="p-6 rounded-2xl bg-white border border-[#C9D4E1] shadow-xs space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-[#D9E1EA]">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Badge variant="primary" size="sm" className="font-mono">
                {selectedNode.type}
              </Badge>
              {selectedNode.jurisdiction && (
                <span className="text-[11px] font-mono text-[#718096]">
                  {selectedNode.jurisdiction}
                </span>
              )}
            </div>
            <h3 className="text-lg font-bold font-serif text-[#17253A]">{selectedNode.label}</h3>
            <p className="text-xs font-mono text-[#526176] mt-0.5">{selectedNode.identifier}</p>
          </div>
        </div>

        {/* Description */}
        <div className="space-y-1">
          <span className="text-xs font-mono font-bold text-[#526176] uppercase tracking-wider">
            Description / Scope
          </span>
          <p className="text-xs text-[#17253A] leading-relaxed bg-[#EFF3F7] p-3 rounded-lg border border-[#D9E1EA]">
            {selectedNode.description}
          </p>
        </div>

        {/* Source Document Link (Phase 5 Integration) */}
        {selectedNode.sourceDocId && (
          <div className="p-3 rounded-xl bg-[#D9E7F5]/50 border border-[#B5D3EE] flex items-center justify-between text-xs font-mono">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-[#2563A8]" />
              <span className="font-semibold text-[#17253A]">Source Corpus Document</span>
            </div>
            <Link href={ADMIN_DYNAMIC_ROUTES.DOCUMENT_DETAIL(selectedNode.sourceDocId)}>
              <Button variant="secondary" size="sm" className="text-xs h-7">
                View Document
                <ExternalLink className="h-3 w-3 ml-1" />
              </Button>
            </Link>
          </div>
        )}

        {/* Traversal Action */}
        <div className="pt-2">
          <Button
            variant="primary"
            size="sm"
            onClick={() => startTraversal(selectedNode.id)}
            className="w-full text-xs font-mono"
          >
            <GitFork className="h-3.5 w-3.5 mr-1.5" />
            Explore {traversalDepth}-Hop Neighborhood
          </Button>
        </div>

        {/* Incoming & Outgoing Relationships */}
        <div className="space-y-4 pt-2 border-t border-[#D9E1EA]">
          <h4 className="text-xs font-mono font-bold text-[#17253A] uppercase tracking-wider">
            Connected Legal Relationships ({incoming.length + outgoing.length})
          </h4>

          {/* Outgoing */}
          {outgoing.length > 0 && (
            <div className="space-y-2">
              <span className="text-[11px] font-mono text-[#718096] uppercase">Outgoing Relationships:</span>
              <div className="space-y-1.5">
                {outgoing.map(({ edge, node }) => (
                  <div
                    key={edge.id}
                    onClick={() => selectNode(node.id)}
                    className="p-2.5 rounded-lg bg-[#EFF3F7] hover:bg-[#D9E7F5] border border-[#D9E1EA] flex items-center justify-between text-xs font-mono cursor-pointer transition-colors"
                  >
                    <div className="flex items-center gap-2 truncate">
                      <Badge variant="outline" size="sm">
                        {edge.relationship}
                      </Badge>
                      <span className="font-semibold text-[#17253A] truncate">{node.label}</span>
                    </div>
                    <ArrowRight className="h-3.5 w-3.5 text-[#2563A8] shrink-0" />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Incoming */}
          {incoming.length > 0 && (
            <div className="space-y-2">
              <span className="text-[11px] font-mono text-[#718096] uppercase">Incoming Relationships:</span>
              <div className="space-y-1.5">
                {incoming.map(({ edge, node }) => (
                  <div
                    key={edge.id}
                    onClick={() => selectNode(node.id)}
                    className="p-2.5 rounded-lg bg-[#EFF3F7] hover:bg-[#D9E7F5] border border-[#D9E1EA] flex items-center justify-between text-xs font-mono cursor-pointer transition-colors"
                  >
                    <div className="flex items-center gap-2 truncate">
                      <ArrowLeft className="h-3.5 w-3.5 text-[#2563A8] shrink-0" />
                      <span className="font-semibold text-[#17253A] truncate">{node.label}</span>
                    </div>
                    <Badge variant="outline" size="sm">
                      {edge.relationship}
                    </Badge>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  return null;
};
