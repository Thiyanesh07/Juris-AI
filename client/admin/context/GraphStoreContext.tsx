'use client';

import React, { createContext, useContext, useState, useMemo, useCallback, useEffect } from 'react';
import {
  GraphNodeData,
  GraphEdgeData,
  GraphEntityType,
  GraphRelationType,
  INITIAL_GRAPH_NODES,
  INITIAL_GRAPH_EDGES,
} from '@/data/graph';
import { apiClient } from '@/lib/apiClient';

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
  isLoading: boolean;
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

function mapRawType(rawType?: string): GraphEntityType {
  if (!rawType) return 'ARTICLE';
  const u = rawType.toUpperCase();
  if (['ARTICLE', 'ACT', 'SECTION', 'AMENDMENT', 'RULE', 'REGULATION', 'JUDGMENT', 'COURT'].includes(u)) {
    return u as GraphEntityType;
  }
  if (u === 'DOCTRINE' || u === 'CONCEPT' || u === 'CONSTITUTION') return 'ARTICLE';
  return 'ACT';
}

function layoutNodes(rawNodes: any[], rawEdges: any[], centerId?: string): { nodes: GraphNodeData[]; edges: GraphEdgeData[] } {
  if (!rawNodes || rawNodes.length === 0) {
    return { nodes: INITIAL_GRAPH_NODES, edges: INITIAL_GRAPH_EDGES };
  }

  const cx = 500;
  const cy = 300;

  const nodeMap = new Map<string, GraphNodeData>();
  const firstHop = new Set<string>();
  const secondHop = new Set<string>();

  if (centerId) {
    rawEdges.forEach((e: any) => {
      const src = String(e.sourceId || e.source);
      const tgt = String(e.targetId || e.target);
      if (src === centerId) firstHop.add(tgt);
      if (tgt === centerId) firstHop.add(src);
    });

    rawEdges.forEach((e: any) => {
      const src = String(e.sourceId || e.source);
      const tgt = String(e.targetId || e.target);
      if (firstHop.has(src) && tgt !== centerId && !firstHop.has(tgt)) secondHop.add(tgt);
      if (firstHop.has(tgt) && src !== centerId && !firstHop.has(src)) secondHop.add(src);
    });
  }

  const firstHopList = Array.from(firstHop);
  const secondHopList = Array.from(secondHop);
  const remainingList = rawNodes
    .map((n: any) => String(n.id))
    .filter((id: string) => id !== centerId && !firstHop.has(id) && !secondHop.has(id));

  rawNodes.forEach((n: any, idx: number) => {
    const id = String(n.id);
    let x = cx;
    let y = cy;

    if (id === centerId) {
      x = cx;
      y = cy;
    } else if (firstHop.has(id)) {
      const i = firstHopList.indexOf(id);
      const angle = (2 * Math.PI * i) / Math.max(firstHopList.length, 1);
      x = cx + Math.round(180 * Math.cos(angle));
      y = cy + Math.round(160 * Math.sin(angle));
    } else if (secondHop.has(id)) {
      const i = secondHopList.indexOf(id);
      const angle = (2 * Math.PI * i) / Math.max(secondHopList.length, 1);
      x = cx + Math.round(320 * Math.cos(angle));
      y = cy + Math.round(260 * Math.sin(angle));
    } else {
      const i = remainingList.indexOf(id);
      const row = Math.floor(i / 6);
      const col = i % 6;
      x = 100 + col * 150;
      y = 100 + row * 120;
    }

    const type = mapRawType(n.type || n.label);
    const label = n.label || n.name || id;

    nodeMap.set(id, {
      id,
      label,
      type,
      x,
      y,
      identifier: n.properties?.citation_ref || n.properties?.id || label,
      description: n.properties?.description || `${type} entity in legal knowledge graph`,
      sourceDocId: n.properties?.document_id,
      jurisdiction: n.properties?.jurisdiction || 'India',
    });
  });

  const parsedEdges: GraphEdgeData[] = rawEdges.map((e: any, idx: number) => ({
    id: String(e.id || `e_${idx}`),
    source: String(e.sourceId || e.source),
    target: String(e.targetId || e.target),
    relationship: (e.label || e.relationship || 'REFERENCES').toUpperCase() as GraphRelationType,
    description: e.description,
  }));

  return { nodes: Array.from(nodeMap.values()), edges: parsedEdges };
}

export const GraphStoreProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [nodes, setNodes] = useState<GraphNodeData[]>(INITIAL_GRAPH_NODES);
  const [edges, setEdges] = useState<GraphEdgeData[]>(INITIAL_GRAPH_EDGES);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>('n_art21');
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [entityTypeFilter, setEntityTypeFilter] = useState<string>('ALL');
  const [relationTypeFilter, setRelationTypeFilter] = useState<string>('ALL');
  const [traversalDepth, setTraversalDepth] = useState<number>(2);
  const [traversalPath, setTraversalPath] = useState<string[]>(['n_art21', 'n_const', 'n_j_maneka']);

  const [zoomLevel, setZoomLevel] = useState<number>(1.0);
  const [panOffset, setPanOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Fetch live neighbors when node is selected
  const fetchNeighborsFromApi = useCallback(async (nodeId: string, depth: number) => {
    setIsLoading(true);
    try {
      const res = await apiClient.get<{
        center_node: any;
        nodes: any[];
        edges: any[];
        depth: number;
      }>(`/graph/neighbors/${encodeURIComponent(nodeId)}?depth=${depth}`);

      if (res && res.nodes && res.nodes.length > 0) {
        const layout = layoutNodes(res.nodes, res.edges, nodeId);
        setNodes(layout.nodes);
        setEdges(layout.edges);
        setTraversalPath(res.nodes.map(n => String(n.id)));
      }
    } catch {
      // Keep existing local nodes on error
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Fetch graph nodes matching search query
  const searchGraphFromApi = useCallback(async (query: string) => {
    if (!query.trim()) return;
    setIsLoading(true);
    try {
      const res = await apiClient.get<{ nodes: any[]; total: number }>(
        `/graph/search?query=${encodeURIComponent(query.trim())}`
      );
      if (res && res.nodes && res.nodes.length > 0) {
        const layout = layoutNodes(res.nodes, [], res.nodes[0]?.id);
        setNodes(layout.nodes);
        if (res.nodes[0]?.id) {
          fetchNeighborsFromApi(res.nodes[0].id, traversalDepth);
        }
      }
    } catch {
      // Keep existing nodes
    } finally {
      setIsLoading(false);
    }
  }, [fetchNeighborsFromApi, traversalDepth]);

  const selectNode = (id: string | null) => {
    setSelectedNodeId(id);
    setSelectedEdgeId(null);
    if (id) {
      fetchNeighborsFromApi(id, traversalDepth);
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

  const startTraversal = (startNodeId: string) => {
    fetchNeighborsFromApi(startNodeId, traversalDepth);
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
    setNodes(INITIAL_GRAPH_NODES);
    setEdges(INITIAL_GRAPH_EDGES);
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

    return filtered;
  }, [nodes, searchQuery, entityTypeFilter]);

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
        isLoading,
        selectNode,
        selectEdge,
        setSearchQuery: (q: string) => {
          setSearchQuery(q);
          if (q.length > 2) searchGraphFromApi(q);
        },
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

