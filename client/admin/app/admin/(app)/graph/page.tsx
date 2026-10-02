'use client';

import React from 'react';
import { PageHeader } from '@/components/shared/PageHeader';
import { GraphStoreProvider } from '@/context/GraphStoreContext';
import { GraphToolbar } from '@/components/graph/GraphToolbar';
import { GraphCanvas } from '@/components/graph/GraphCanvas';
import { NodeDetailsPanel } from '@/components/graph/NodeDetailsPanel';
import { GraphLegend } from '@/components/graph/GraphLegend';
import { GraphTelemetry } from '@/components/graph/GraphTelemetry';

function KnowledgeGraphContent() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="Knowledge Graph"
        subtitle="Explore legal entities and their relationships across the Juris AI knowledge graph."
      />

      {/* Toolbar Controls */}
      <GraphToolbar />

      {/* Main Workspace: Graph Canvas + Details Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <div className="lg:col-span-8">
          <GraphCanvas />
        </div>
        <div className="lg:col-span-4">
          <NodeDetailsPanel />
        </div>
      </div>

      {/* Visual Legend */}
      <GraphLegend />

      {/* Telemetry & Health */}
      <GraphTelemetry />
    </div>
  );
}

export default function KnowledgeGraphPage() {
  return (
    <GraphStoreProvider>
      <KnowledgeGraphContent />
    </GraphStoreProvider>
  );
}
