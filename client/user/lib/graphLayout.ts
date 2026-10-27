/**
 * JURIS AI — Graph Layout & Geometry Utilities (Phase 5)
 *
 * Provides deterministic, collision-free layout for legal knowledge graph subgraphs:
 * - Concentric / radial layout around query seed and seed entities.
 * - Dynamic radius scaling to prevent label and node collisions.
 * - Single-node, disconnected component, and large-graph handling.
 * - Bounding box and responsive fit-to-view calculation.
 * - Smart legal label shortening with full label retention.
 */

import { GraphNode, GraphEdge, EntityType } from './types';

export interface GraphBounds {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
  width: number;
  height: number;
  centerX: number;
  centerY: number;
}

export interface FitViewTransform {
  zoom: number;
  panX: number;
  panY: number;
}

export interface TruncatedLabel {
  displayLabel: string;
  fullLabel: string;
  isTruncated: boolean;
}

/**
 * Truncate long legal names gracefully for SVG display while preserving
 * recognizable citation markers (e.g. "Art. 21", "Maneka Gandhi v. UOI").
 */
export function formatNodeDisplayLabel(label: string, maxChars = 20): TruncatedLabel {
  const fullLabel = String(label || '').trim();
  if (fullLabel.length <= maxChars) {
    return { displayLabel: fullLabel, fullLabel, isTruncated: false };
  }

  // Preserve constitutional article short forms if present
  const artMatch = fullLabel.match(/Article\s+(\d+[A-Z]?)/i);
  if (artMatch && fullLabel.length > maxChars) {
    const short = `Art. ${artMatch[1]}`;
    if (short.length <= maxChars) {
      return { displayLabel: short, fullLabel, isTruncated: true };
    }
  }

  // Preserve case names with "v." or "Versus"
  const vMatch = fullLabel.match(/^([A-Za-z\s]+?)\s+(?:v\.|v|Versus)\s+/i);
  if (vMatch) {
    const petitioner = vMatch[1].trim();
    if (petitioner.length <= maxChars - 5) {
      return { displayLabel: `${petitioner} v. …`, fullLabel, isTruncated: true };
    }
    const words = petitioner.split(/\s+/);
    if (words[0].length <= maxChars - 6) {
      const lead = words.length > 1 && (words[0].length + words[1].length + 1 <= maxChars - 6)
        ? `${words[0]} ${words[1]}`
        : words[0];
      return { displayLabel: `${lead}… v. …`, fullLabel, isTruncated: true };
    }
  }

  return {
    displayLabel: `${fullLabel.slice(0, maxChars - 1).trim()}…`,
    fullLabel,
    isTruncated: true,
  };
}

/**
 * Calculate bounding box across a set of graph nodes with configurable margin.
 */
export function calculateGraphBounds(nodes: GraphNode[], margin = 60): GraphBounds {
  if (!nodes || nodes.length === 0) {
    return {
      minX: 0,
      minY: 0,
      maxX: 1000,
      maxY: 600,
      width: 1000,
      height: 600,
      centerX: 500,
      centerY: 300,
    };
  }

  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;

  nodes.forEach((node) => {
    const x = typeof node.x === 'number' && !isNaN(node.x) ? node.x : 500;
    const y = typeof node.y === 'number' && !isNaN(node.y) ? node.y : 300;
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
  });

  minX -= margin;
  minY -= margin;
  maxX += margin;
  maxY += margin;

  const width = Math.max(100, maxX - minX);
  const height = Math.max(100, maxY - minY);

  return {
    minX,
    minY,
    maxX,
    maxY,
    width,
    height,
    centerX: minX + width / 2,
    centerY: minY + height / 2,
  };
}

/**
 * Compute optimal zoom and pan offset to frame all nodes in the viewport.
 */
export function calculateFitToView(
  bounds: GraphBounds,
  viewportWidth = 800,
  viewportHeight = 440,
  minZoom = 0.45,
  maxZoom = 1.3
): FitViewTransform {
  if (bounds.width <= 0 || bounds.height <= 0 || viewportWidth <= 0 || viewportHeight <= 0) {
    return { zoom: 1.0, panX: 0, panY: 0 };
  }

  const scaleX = viewportWidth / bounds.width;
  const scaleY = viewportHeight / bounds.height;
  const rawZoom = Math.min(scaleX, scaleY);

  const zoom = Math.max(minZoom, Math.min(maxZoom, rawZoom * 0.9));

  // Compute pan offset to center graph content
  const panX = Math.round(viewportWidth / 2 - bounds.centerX * zoom);
  const panY = Math.round(viewportHeight / 2 - bounds.centerY * zoom);

  return { zoom, panX, panY };
}

/**
 * Layout graph nodes in a deterministic, collision-free radial / concentric topology:
 * - Query node / seed nodes positioned at center.
 * - Hop 1 entities distributed along inner ring.
 * - Hop 2+ entities distributed along outer ring.
 * - Disconnected nodes placed in dedicated perimeter ring.
 * - Dynamic radius scaling based on node count to prevent label collisions.
 */
export function layoutGraphNodes(
  rawNodes: GraphNode[],
  edges: GraphEdge[] = [],
  canvasWidth = 1000,
  canvasHeight = 650
): GraphNode[] {
  if (!rawNodes || rawNodes.length === 0) return [];
  if (rawNodes.length === 1) {
    return [
      {
        ...rawNodes[0],
        x: Math.round(canvasWidth / 2),
        y: Math.round(canvasHeight / 2),
      },
    ];
  }

  const cx = canvasWidth / 2;
  const cy = canvasHeight / 2;

  // Build adjacency lookup
  const adj = new Map<string, Set<string>>();
  rawNodes.forEach((n) => adj.set(n.id, new Set()));
  edges.forEach((e) => {
    if (adj.has(e.sourceId) && adj.has(e.targetId)) {
      adj.get(e.sourceId)!.add(e.targetId);
      adj.get(e.targetId)!.add(e.sourceId);
    }
  });

  // Identify seed / center nodes
  // Priority: 1) isQuery, 2) isSeed, 3) highest degree node
  let centerNode = rawNodes.find((n) => n.isQuery);
  if (!centerNode) {
    centerNode = rawNodes.find((n) => n.isSeed);
  }
  if (!centerNode) {
    let maxDeg = -1;
    rawNodes.forEach((n) => {
      const deg = adj.get(n.id)?.size ?? 0;
      if (deg > maxDeg) {
        maxDeg = deg;
        centerNode = n;
      }
    });
  }

  const centerId = centerNode?.id ?? rawNodes[0].id;

  // Partition into hops
  const hop1 = new Set<string>();
  const hop2 = new Set<string>();
  const disconnected = new Set<string>();

  (adj.get(centerId) || new Set()).forEach((neighborId) => {
    hop1.add(neighborId);
  });

  rawNodes.forEach((n) => {
    if (n.id === centerId || hop1.has(n.id)) return;
    const neighbors = adj.get(n.id) || new Set();
    const hasHop1Connection = Array.from(neighbors).some((id) => hop1.has(id));
    if (hasHop1Connection) {
      hop2.add(n.id);
    } else if (neighbors.size === 0) {
      disconnected.add(n.id);
    } else {
      hop2.add(n.id);
    }
  });

  const hop1List = Array.from(hop1);
  const hop2List = Array.from(hop2);
  const disconnectedList = Array.from(disconnected);

  // Dynamic radius sizing based on node counts to prevent visual crowding
  const hop1Radius = Math.max(160, Math.min(240, hop1List.length * 36));
  const hop2Radius = Math.max(hop1Radius + 110, Math.min(370, hop1Radius + hop2List.length * 24));
  const discRadius = hop2Radius + 80;

  return rawNodes.map((node, idx) => {
    let x = cx;
    let y = cy;

    if (node.id === centerId) {
      x = cx;
      y = cy;
    } else if (hop1.has(node.id)) {
      const pos = hop1List.indexOf(node.id);
      const angle = (2 * Math.PI * pos) / Math.max(1, hop1List.length) - Math.PI / 2;
      x = cx + Math.cos(angle) * hop1Radius;
      y = cy + Math.sin(angle) * hop1Radius;
    } else if (hop2.has(node.id)) {
      const pos = hop2List.indexOf(node.id);
      // Offset by half a step from hop1 to interleave rays and reduce edge crossings
      const offset = Math.PI / Math.max(1, hop2List.length);
      const angle = (2 * Math.PI * pos) / Math.max(1, hop2List.length) - Math.PI / 2 + offset;
      x = cx + Math.cos(angle) * hop2Radius;
      y = cy + Math.sin(angle) * hop2Radius;
    } else if (disconnected.has(node.id)) {
      const pos = disconnectedList.indexOf(node.id);
      const angle = (2 * Math.PI * pos) / Math.max(1, disconnectedList.length);
      x = cx + Math.cos(angle) * discRadius;
      y = cy + Math.sin(angle) * discRadius;
    } else {
      const angle = (2 * Math.PI * idx) / rawNodes.length;
      x = cx + Math.cos(angle) * hop1Radius;
      y = cy + Math.sin(angle) * hop1Radius;
    }

    return {
      ...node,
      x: Math.round(x),
      y: Math.round(y),
    };
  });
}
