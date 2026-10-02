'use client';

import React, { createContext, useContext, useState, useMemo } from 'react';
import {
  GraphNodeData,
  GraphEdgeData,
  GraphEntityType,
  GraphRelationType,
  INITIAL_GRAPH_NODES,
  INITIAL_GRAPH_EDGES,
} from '@/data/graph';

interface GraphStoreContextType {
  nodes: GraphNodeData[];
  edges: GraphEdgeData[];
  selectedNodeId: string | null;
  selectedEdgeId: string | null;
  searchQuery: string;
  entityTypeFilter: string;
  relationTypeFilter: string;
  traversalDepth: number;
  traversalPath: string[];
  zoomLevel: number;
  panOffset: { x: number; y: number };
  selectNode: (id: string | null) => void;
  selectEdge: (id: string | null) => void;
  setSearchQuery: (query: string) => void;
  setEntityTypeFilter: (type: string) => void;
  setRelationTypeFilter: (type: string) => void;
  setTraversalDepth: (depth: number) => void;
  startTraversal: (startNodeId: string) => void;
  resetTraversal: () => void;
  resetView: () => void;
  zoomIn: () => void;
  zoomOut: () => void;
  visibleNodes: GraphNodeData[];
  visibleEdges: GraphEdgeData[];
  getSelectedNode: () => GraphNodeData | undefined;
  getSelectedEdge: () => GraphEdgeData | undefined;
  getNodeRelationships: (nodeId: string) => {
    incoming: { edge: GraphEdgeData; node: GraphNodeData }[];
    outgoing: { edge: GraphEdgeData; node: GraphNodeData }[];
  };
}

const GraphStoreContext = createContext<GraphStoreContextType | undefined>(undefined);

export const GraphStoreProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [nodes] = useState<GraphNodeData[]>(INITIAL_GRAPH_NODES);
  const [edges] = useState<GraphEdgeData[]>(INITIAL_GRAPH_EDGES);

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>('n_art21'); // Default select Article 21
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [entityTypeFilter, setEntityTypeFilter] = useState<string>('ALL');
  const [relationTypeFilter, setRelationTypeFilter] = useState<string>('ALL');
  const [traversalDepth, setTraversalDepth] = useState<number>(2);
  const [traversalPath, setTraversalPath] = useState<string[]>(['n_art21', 'n_const', 'n_j_maneka']);

  const [zoomLevel, setZoomLevel] = useState<number>(1.0);
  const [panOffset, setPanOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  const selectNode = (id: string | null) => {
    setSelectedNodeId(id);
    setSelectedEdgeId(null);
    if (id) {
      startTraversal(id);
    }
  };

  const selectEdge = (id: string | null) => {
    setSelectedEdgeId(id);
    if (id) {
      const e = edges.find((item) => item.id === id);
      if (e) {
        setSelectedNodeId(e.source);
      }
    }
  };

  const getSelectedNode = (): GraphNodeData | undefined => {
    return nodes.find((n) => n.id === selectedNodeId);
  };

  const getSelectedEdge = (): GraphEdgeData | undefined => {
    return edges.find((e) => e.id === selectedEdgeId);
  };

  // Traversal path calculation from start node up to selected depth
  const startTraversal = (startNodeId: string) => {
    const visited = new Set<string>([startNodeId]);
    const path: string[] = [startNodeId];
    let currentLevel = [startNodeId];

    for (let d = 0; d < traversalDepth; d++) {
      const nextLevel: string[] = [];
      for (const nid of currentLevel) {
        const connectedEdges = edges.filter((e) => e.source === nid || e.target === nid);
        for (const edge of connectedEdges) {
          const neighbor = edge.source === nid ? edge.target : edge.source;
          if (!visited.has(neighbor)) {
            visited.add(neighbor);
            nextLevel.push(neighbor);
            path.push(neighbor);
          }
        }
      }
      currentLevel = nextLevel;
    }
    setTraversalPath(path);
  };

  const resetTraversal = () => {
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setTraversalPath([]);
  };

  const resetView = () => {
    setZoomLevel(1.0);
    setPanOffset({ x: 0, y: 0 });
    setSearchQuery('');
    setEntityTypeFilter('ALL');
    setRelationTypeFilter('ALL');
    setTraversalDepth(2);
  };

  const zoomIn = () => setZoomLevel((prev) => Math.min(2.0, prev + 0.15));
  const zoomOut = () => setZoomLevel((prev) => Math.max(0.6, prev - 0.15));

  // Compute visible nodes based on search, entity filter, and depth
  const visibleNodes = useMemo(() => {
    let filtered = nodes;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (n) =>
          n.label.toLowerCase().includes(q) ||
          n.identifier.toLowerCase().includes(q) ||
          n.type.toLowerCase().includes(q)
      );
    }

    if (entityTypeFilter !== 'ALL') {
      filtered = filtered.filter((n) => n.type === entityTypeFilter);
    }

    // Depth filtering if selected node exists
    if (selectedNodeId && traversalPath.length > 0) {
      const pathSet = new Set(traversalPath);
      // Keep nodes matching path or filters
      filtered = filtered.filter((n) => pathSet.has(n.id));
    }

    return filtered;
  }, [nodes, searchQuery, entityTypeFilter, selectedNodeId, traversalPath]);

  const visibleNodeIds = useMemo(() => new Set(visibleNodes.map((n) => n.id)), [visibleNodes]);

  // Compute visible edges based on visible nodes & relationship filter
  const visibleEdges = useMemo(() => {
    return edges.filter((e) => {
      const endpointsVisible = visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target);
      const matchesRelFilter = relationTypeFilter === 'ALL' || e.relationship === relationTypeFilter;
      return endpointsVisible && matchesRelFilter;
    });
  }, [edges, visibleNodeIds, relationTypeFilter]);

  const getNodeRelationships = (nodeId: string) => {
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));
    const incoming = edges
      .filter((e) => e.target === nodeId)
      .map((edge) => ({ edge, node: nodeMap.get(edge.source)! }))
      .filter((item) => item.node !== undefined);

    const outgoing = edges
      .filter((e) => e.source === nodeId)
      .map((edge) => ({ edge, node: nodeMap.get(edge.target)! }))
      .filter((item) => item.node !== undefined);

    return { incoming, outgoing };
  };

  return (
    <GraphStoreContext.Provider
      value={{
        nodes,
        edges,
        selectedNodeId,
        selectedEdgeId,
        searchQuery,
        entityTypeFilter,
        relationTypeFilter,
        traversalDepth,
        traversalPath,
        zoomLevel,
        panOffset,
        selectNode,
        selectEdge,
        setSearchQuery,
        setEntityTypeFilter,
        setRelationTypeFilter,
        setTraversalDepth,
        startTraversal,
        resetTraversal,
        resetView,
        zoomIn,
        zoomOut,
        visibleNodes,
        visibleEdges,
        getSelectedNode,
        getSelectedEdge,
        getNodeRelationships,
      }}
    >
      {children}
    </GraphStoreContext.Provider>
  );
};

export const useGraphStore = () => {
  const context = useContext(GraphStoreContext);
  if (!context) {
    throw new Error('useGraphStore must be used within a GraphStoreProvider');
  }
  return context;
};
