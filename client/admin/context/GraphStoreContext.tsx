'use client';

import React, { createContext, useContext, useState, useMemo, useCallback, useEffect } from 'react';
import {
  GraphNodeData,
  GraphEdgeData,
  GraphEntityType,
  GraphRelationType,
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
  setPanOffset: React.Dispatch<React.SetStateAction<{ x: number; y: number }>>;
  isLoading: boolean;
  error: string | null;
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
  refreshGraph: () => Promise<void>;
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

export function mapRawType(rawType?: string): GraphEntityType {
  if (!rawType) return 'ARTICLE';
  const u = rawType.toUpperCase();
  if (['ARTICLE', 'ACT', 'SECTION', 'AMENDMENT', 'RULE', 'REGULATION', 'JUDGMENT', 'COURT'].includes(u)) {
    return u as GraphEntityType;
  }
  if (u === 'DOCTRINE' || u === 'CONCEPT' || u === 'CONSTITUTION') return 'ARTICLE';
  return 'ACT';
}

export function layoutNodes(
  rawNodes: any[],
  rawEdges: any[],
  centerId?: string
): { nodes: GraphNodeData[]; edges: GraphEdgeData[] } {
  if (!rawNodes || rawNodes.length === 0) {
    return { nodes: [], edges: [] };
  }

  const cx = 500;
  const cy = 300;

  const nodeMap = new Map<string, GraphNodeData>();
  const firstHop = new Set<string>();
  const secondHop = new Set<string>();

  if (centerId && rawEdges && rawEdges.length > 0) {
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
      const posIdx = firstHopList.indexOf(id);
      const angle = (2 * Math.PI * posIdx) / Math.max(1, firstHopList.length);
      const radius = 160;
      x = cx + Math.cos(angle) * radius;
      y = cy + Math.sin(angle) * radius;
    } else if (secondHop.has(id)) {
      const posIdx = secondHopList.indexOf(id);
      const angle = (2 * Math.PI * posIdx) / Math.max(1, secondHopList.length);
      const radius = 280;
      x = cx + Math.cos(angle) * radius;
      y = cy + Math.sin(angle) * radius;
    } else {
      const posIdx = remainingList.indexOf(id);
      const angle = (2 * Math.PI * (posIdx >= 0 ? posIdx : idx)) / Math.max(1, remainingList.length);
      const radius = 240;
      x = cx + Math.cos(angle) * radius;
      y = cy + Math.sin(angle) * radius;
    }

    nodeMap.set(id, {
      id,
      label: String(n.label || n.name || id),
      type: mapRawType(n.type || n.label),
      x: Math.round(x),
      y: Math.round(y),
      description: n.description || n.properties?.description || (n.properties ? JSON.stringify(n.properties) : 'Legal entity record'),
      identifier: n.identifier || n.properties?.id || id,
      sourceDocId: n.sourceDocId || n.properties?.document_id,
      jurisdiction: n.jurisdiction || n.properties?.jurisdiction || 'Union of India',
    });
  });

  const parsedEdges: GraphEdgeData[] = (rawEdges || []).map((e: any, idx: number) => ({
    id: String(e.id || `edge_${idx}`),
    source: String(e.sourceId || e.source),
    target: String(e.targetId || e.target),
    relationship: (e.label || e.relationship || 'REFERENCES').toUpperCase() as GraphRelationType,
    description: e.description,
  }));

  return { nodes: Array.from(nodeMap.values()), edges: parsedEdges };
}

export const GraphStoreProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [nodes, setNodes] = useState<GraphNodeData[]>([]);
  const [edges, setEdges] = useState<GraphEdgeData[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [entityTypeFilter, setEntityTypeFilter] = useState<string>('ALL');
  const [relationTypeFilter, setRelationTypeFilter] = useState<string>('ALL');
  const [traversalDepth, setTraversalDepth] = useState<number>(2);
  const [traversalPath, setTraversalPath] = useState<string[]>([]);

  const [zoomLevel, setZoomLevel] = useState<number>(1.0);
  const [panOffset, setPanOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Fetch live neighbors when node is selected
  const fetchNeighborsFromApi = useCallback(async (nodeId: string, depth: number) => {
    setIsLoading(true);
    setError(null);
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
        setTraversalPath(res.nodes.map((n) => String(n.id)));
      } else {
        // Center node exists without neighbors
        if (res?.center_node) {
          const layout = layoutNodes([res.center_node], [], nodeId);
          setNodes(layout.nodes);
          setEdges([]);
          setTraversalPath([nodeId]);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retrieve node neighbors');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Fetch graph nodes matching search query
  const searchGraphFromApi = useCallback(
    async (query: string, typeFilter?: string) => {
      if (!query.trim()) return;
      setIsLoading(true);
      setError(null);
      try {
        const typeParam = typeFilter && typeFilter !== 'ALL' ? `&entity_type=${encodeURIComponent(typeFilter)}` : '';
        const res = await apiClient.get<{ nodes: any[]; total: number }>(
          `/graph/search?query=${encodeURIComponent(query.trim())}${typeParam}`
        );

        if (res && res.nodes && res.nodes.length > 0) {
          const firstId = res.nodes[0]?.id;
          if (firstId) {
            setSelectedNodeId(firstId);
            await fetchNeighborsFromApi(firstId, traversalDepth);
          } else {
            const layout = layoutNodes(res.nodes, []);
            setNodes(layout.nodes);
            setEdges([]);
          }
        } else {
          setNodes([]);
          setEdges([]);
          setSelectedNodeId(null);
          setTraversalPath([]);
        }
      } catch (err) {
        setNodes([]);
        setEdges([]);
        setSelectedNodeId(null);
        setError(err instanceof Error ? err.message : 'Graph search request failed');
      } finally {
        setIsLoading(false);
      }
    },
    [fetchNeighborsFromApi, traversalDepth]
  );

  // Initial load: search for initial seed entities without hardcoded mocks
  const initialLoad = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await apiClient.get<{ nodes: any[]; total: number }>('/graph/search?query=Act&limit=15');
      if (res && res.nodes && res.nodes.length > 0) {
        const firstId = res.nodes[0]?.id;
        if (firstId) {
          setSelectedNodeId(firstId);
          await fetchNeighborsFromApi(firstId, 2);
        } else {
          const layout = layoutNodes(res.nodes, []);
          setNodes(layout.nodes);
          setEdges([]);
        }
      } else {
        // Fallback search with single letter
        const fallbackRes = await apiClient.get<{ nodes: any[]; total: number }>('/graph/search?query=a&limit=15');
        if (fallbackRes && fallbackRes.nodes && fallbackRes.nodes.length > 0) {
          const firstId = fallbackRes.nodes[0]?.id;
          if (firstId) {
            setSelectedNodeId(firstId);
            await fetchNeighborsFromApi(firstId, 2);
          } else {
            const layout = layoutNodes(fallbackRes.nodes, []);
            setNodes(layout.nodes);
            setEdges([]);
          }
        } else {
          setNodes([]);
          setEdges([]);
          setSelectedNodeId(null);
        }
      }
    } catch (err) {
      setNodes([]);
      setEdges([]);
      setSelectedNodeId(null);
      setError(err instanceof Error ? err.message : 'Unable to connect to Neo4j Knowledge Graph');
    } finally {
      setIsLoading(false);
    }
  }, [fetchNeighborsFromApi]);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const res = await apiClient.get<{ nodes: any[]; total: number }>('/graph/search?query=Act&limit=15');
        if (!active) return;
        if (res && res.nodes && res.nodes.length > 0) {
          const firstId = res.nodes[0]?.id;
          if (firstId) {
            setSelectedNodeId(firstId);
            await fetchNeighborsFromApi(firstId, 2);
          } else {
            const layout = layoutNodes(res.nodes, []);
            setNodes(layout.nodes);
            setEdges([]);
          }
        } else {
          const fallbackRes = await apiClient.get<{ nodes: any[]; total: number }>('/graph/search?query=a&limit=15');
          if (!active) return;
          if (fallbackRes && fallbackRes.nodes && fallbackRes.nodes.length > 0) {
            const firstId = fallbackRes.nodes[0]?.id;
            if (firstId) {
              setSelectedNodeId(firstId);
              await fetchNeighborsFromApi(firstId, 2);
            } else {
              const layout = layoutNodes(fallbackRes.nodes, []);
              setNodes(layout.nodes);
              setEdges([]);
            }
          } else {
            setNodes([]);
            setEdges([]);
            setSelectedNodeId(null);
          }
        }
      } catch (err) {
        if (!active) return;
        setNodes([]);
        setEdges([]);
        setSelectedNodeId(null);
        setError(err instanceof Error ? err.message : 'Unable to connect to Neo4j Knowledge Graph');
      } finally {
        if (active) setIsLoading(false);
      }
    })();

    return () => {
      active = false;
    };
  }, [fetchNeighborsFromApi]);

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
        setTraversalPath([e.source, e.target]);
      }
    }
  };

  const startTraversal = (startNodeId: string) => {
    setSelectedNodeId(startNodeId);
    setSelectedEdgeId(null);
    fetchNeighborsFromApi(startNodeId, traversalDepth);
  };

  const resetTraversal = () => {
    if (selectedNodeId) {
      setTraversalPath([selectedNodeId]);
    } else {
      setTraversalPath([]);
    }
  };

  const resetView = () => {
    setZoomLevel(1.0);
    setPanOffset({ x: 0, y: 0 });
    setSearchQuery('');
    setEntityTypeFilter('ALL');
    setRelationTypeFilter('ALL');
    initialLoad();
  };

  const zoomIn = () => setZoomLevel((prev) => Math.min(prev + 0.2, 2.5));
  const zoomOut = () => setZoomLevel((prev) => Math.max(prev - 0.2, 0.4));

  // Trigger search when searchQuery changes (debounced by caller or direct)
  const handleSetSearchQuery = (query: string) => {
    setSearchQuery(query);
    if (query.trim().length >= 2) {
      searchGraphFromApi(query, entityTypeFilter);
    } else if (query.trim().length === 0) {
      initialLoad();
    }
  };

  const handleSetEntityTypeFilter = (type: string) => {
    setEntityTypeFilter(type);
    if (searchQuery.trim()) {
      searchGraphFromApi(searchQuery, type);
    }
  };

  // Filtered views based on user controls
  const visibleNodes = useMemo(() => {
    return nodes.filter((node) => {
      const matchesType = entityTypeFilter === 'ALL' || node.type === entityTypeFilter;
      const matchesSearch =
        !searchQuery ||
        node.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        node.identifier.toLowerCase().includes(searchQuery.toLowerCase()) ||
        node.description.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesType && matchesSearch;
    });
  }, [nodes, entityTypeFilter, searchQuery]);

  const visibleNodeIds = useMemo(() => new Set(visibleNodes.map((n) => n.id)), [visibleNodes]);

  const visibleEdges = useMemo(() => {
    return edges.filter((edge) => {
      const endpointsVisible = visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target);
      const matchesRelation = relationTypeFilter === 'ALL' || edge.relationship === relationTypeFilter;
      return endpointsVisible && matchesRelation;
    });
  }, [edges, visibleNodeIds, relationTypeFilter]);

  const getSelectedNode = () => nodes.find((n) => n.id === selectedNodeId);
  const getSelectedEdge = () => edges.find((e) => e.id === selectedEdgeId);

  const getNodeRelationships = (nodeId: string) => {
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));
    const incoming: { edge: GraphEdgeData; node: GraphNodeData }[] = [];
    const outgoing: { edge: GraphEdgeData; node: GraphNodeData }[] = [];

    edges.forEach((edge) => {
      if (edge.target === nodeId) {
        const srcNode = nodeMap.get(edge.source);
        if (srcNode) incoming.push({ edge, node: srcNode });
      }
      if (edge.source === nodeId) {
        const tgtNode = nodeMap.get(edge.target);
        if (tgtNode) outgoing.push({ edge, node: tgtNode });
      }
    });

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
        setPanOffset,
        isLoading,
        error,
        selectNode,
        selectEdge,
        setSearchQuery: handleSetSearchQuery,
        setEntityTypeFilter: handleSetEntityTypeFilter,
        setRelationTypeFilter,
        setTraversalDepth,
        startTraversal,
        resetTraversal,
        resetView,
        zoomIn,
        zoomOut,
        refreshGraph: initialLoad,
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
