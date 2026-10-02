import { useState, useRef, useCallback, useEffect } from 'react';
import { Search, ZoomIn, ZoomOut, Maximize2, X, ExternalLink } from 'lucide-react';
import { GRAPH_NODES, GRAPH_EDGES, GraphNode } from '../data';

const NODE_COLORS: Record<string, { fill: string; stroke: string; text: string }> = {
  DOCUMENT:       { fill: '#183B5B', stroke: '#0F2840', text: '#fff' },
  ARTICLE:        { fill: '#2563A8', stroke: '#1E5296', text: '#fff' },
  SECTION:        { fill: '#3B82D0', stroke: '#2563A8', text: '#fff' },
  ACT:            { fill: '#1A5E8A', stroke: '#134A6E', text: '#fff' },
  JUDGMENT:       { fill: '#2D6B8A', stroke: '#1E5270', text: '#fff' },
  COURT:          { fill: '#1B4D6B', stroke: '#103850', text: '#fff' },
  'LEGAL PRINCIPLE': { fill: '#1E6B5A', stroke: '#155248', text: '#fff' },
  AMENDMENT:      { fill: '#7A5A14', stroke: '#604510', text: '#fff' },
  RULE:           { fill: '#2D7A4F', stroke: '#1E6040', text: '#fff' },
};

const NODE_RADIUS = 28;

function getNodeColor(type: string) {
  return NODE_COLORS[type] || { fill: '#526176', stroke: '#3D4D5C', text: '#fff' };
}

interface Transform { x: number; y: number; scale: number }

export default function KnowledgeGraph() {
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [search, setSearch] = useState('');
  const [highlight, setHighlight] = useState<string | null>(null);
  const [transform, setTransform] = useState<Transform>({ x: 0, y: 0, scale: 1 });
  const [dragging, setDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0, tx: 0, ty: 0 });
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const filteredNodes = search
    ? GRAPH_NODES.filter(n => n.label.toLowerCase().includes(search.toLowerCase()) || n.type.toLowerCase().includes(search.toLowerCase()))
    : GRAPH_NODES;

  const highlightedIds = new Set(filteredNodes.map(n => n.id));

  function handleNodeClick(node: GraphNode, e: React.MouseEvent) {
    e.stopPropagation();
    setSelected(node);
  }

  function handleWheel(e: React.WheelEvent) {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.85 : 1.15;
    setTransform(t => {
      const ns = Math.min(Math.max(t.scale * delta, 0.3), 3);
      return { ...t, scale: ns };
    });
  }

  function handleMouseDown(e: React.MouseEvent) {
    if (e.button !== 0) return;
    setDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY, tx: transform.x, ty: transform.y });
  }

  function handleMouseMove(e: React.MouseEvent) {
    if (!dragging) return;
    setTransform(t => ({
      ...t,
      x: dragStart.tx + (e.clientX - dragStart.x),
      y: dragStart.ty + (e.clientY - dragStart.y),
    }));
  }

  function handleMouseUp() { setDragging(false); }

  function zoom(factor: number) {
    setTransform(t => ({ ...t, scale: Math.min(Math.max(t.scale * factor, 0.3), 3) }));
  }

  function resetView() {
    setTransform({ x: 0, y: 0, scale: 1 });
  }

  const connectedEdges = selected
    ? GRAPH_EDGES.filter(e => e.from === selected.id || e.to === selected.id)
    : [];

  const connectedNodeIds = new Set(connectedEdges.flatMap(e => [e.from, e.to]));

  // Simple curved edge path
  function edgePath(from: GraphNode, to: GraphNode) {
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const mx = (from.x + to.x) / 2;
    const my = (from.y + to.y) / 2;
    const perp = { x: -dy * 0.2, y: dx * 0.2 };
    return `M ${from.x} ${from.y} Q ${mx + perp.x} ${my + perp.y} ${to.x} ${to.y}`;
  }

  const TYPE_LEGEND = Object.keys(NODE_COLORS);

  return (
    <div className="space-y-4">
      <div>
        <h1 style={{ fontFamily: 'DM Serif Display, serif', fontSize: 24, color: '#183B5B', marginBottom: 4 }}>Knowledge Graph</h1>
        <p style={{ fontSize: 13, color: '#526176' }}>Inspect the legal knowledge structure powering Juris AI.</p>
      </div>

      <div className="flex gap-4" style={{ height: 'calc(100vh - 200px)', minHeight: 520 }}>
        {/* Graph canvas */}
        <div className="flex-1 flex flex-col" style={{ background: '#F5F7FA', border: '1px solid #C5D5E8', borderRadius: 8, overflow: 'hidden', position: 'relative' }}>
          {/* Toolbar */}
          <div className="flex items-center gap-2 px-3 py-2" style={{ borderBottom: '1px solid #C5D5E8', background: '#EFF3F7', flexShrink: 0 }}>
            <div className="relative flex-1 max-w-64">
              <Search size={12} style={{ position: 'absolute', left: 9, top: '50%', transform: 'translateY(-50%)', color: '#526176' }} />
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search nodes…"
                style={{ width: '100%', padding: '5px 10px 5px 28px', fontSize: 12, background: '#F5F7FA', border: '1px solid #C5D5E8', borderRadius: 5, color: '#17253A', outline: 'none' }}
                onFocus={e => (e.target.style.borderColor = '#3B82D0')}
                onBlur={e => (e.target.style.borderColor = '#C5D5E8')}
              />
            </div>
            <div style={{ width: 1, height: 20, background: '#C5D5E8' }} />
            <button onClick={() => zoom(1.2)} title="Zoom in" style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#526176', padding: 4, borderRadius: 4 }}
              onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = '#E7EDF4')}
              onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'none')}>
              <ZoomIn size={14} />
            </button>
            <button onClick={() => zoom(0.85)} title="Zoom out" style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#526176', padding: 4, borderRadius: 4 }}
              onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = '#E7EDF4')}
              onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'none')}>
              <ZoomOut size={14} />
            </button>
            <button onClick={resetView} title="Reset view" style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#526176', padding: 4, borderRadius: 4 }}
              onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = '#E7EDF4')}
              onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'none')}>
              <Maximize2 size={14} />
            </button>
            <div style={{ marginLeft: 'auto', fontSize: 11, color: '#526176', fontFamily: 'JetBrains Mono, monospace' }}>
              {GRAPH_NODES.length} nodes · {GRAPH_EDGES.length} edges
            </div>
          </div>

          {/* SVG */}
          <div
            ref={containerRef}
            className="flex-1 overflow-hidden"
            style={{ cursor: dragging ? 'grabbing' : 'grab', position: 'relative' }}
            onWheel={handleWheel}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onClick={() => setSelected(null)}
          >
            <svg
              ref={svgRef}
              width="100%" height="100%"
              style={{ display: 'block' }}
            >
              <defs>
                <marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
                  <path d="M 0 0 L 6 3 L 0 6 Z" fill="#C5D5E8" />
                </marker>
                <marker id="arrow-active" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
                  <path d="M 0 0 L 6 3 L 0 6 Z" fill="#2563A8" />
                </marker>
              </defs>

              <g transform={`translate(${transform.x}, ${transform.y}) scale(${transform.scale})`}>
                {/* Grid dots */}
                {Array.from({ length: 30 }).map((_, r) =>
                  Array.from({ length: 40 }).map((_, c) => (
                    <circle key={`${r}-${c}`} cx={c * 40} cy={r * 40} r={1} fill="#C5D5E8" opacity={0.4} />
                  ))
                )}

                {/* Edges */}
                {GRAPH_EDGES.map(edge => {
                  const from = GRAPH_NODES.find(n => n.id === edge.from);
                  const to = GRAPH_NODES.find(n => n.id === edge.to);
                  if (!from || !to) return null;
                  const isConnected = selected && (edge.from === selected.id || edge.to === selected.id);
                  const dimmed = selected && !isConnected;
                  const searchDim = search && (!highlightedIds.has(edge.from) || !highlightedIds.has(edge.to));

                  return (
                    <g key={edge.id}>
                      <path
                        d={edgePath(from, to)}
                        fill="none"
                        stroke={isConnected ? '#2563A8' : '#C5D5E8'}
                        strokeWidth={isConnected ? 1.5 : 1}
                        strokeOpacity={dimmed || searchDim ? 0.15 : 0.7}
                        markerEnd={`url(#${isConnected ? 'arrow-active' : 'arrow'})`}
                        style={{ transition: 'all 0.2s' }}
                      />
                      {isConnected && (() => {
                        const mx = (from.x + to.x) / 2;
                        const my = (from.y + to.y) / 2;
                        return (
                          <text x={mx} y={my - 4} textAnchor="middle" style={{ fontSize: 8, fill: '#2563A8', fontFamily: 'JetBrains Mono, monospace', fontWeight: 600 }}>
                            {edge.label}
                          </text>
                        );
                      })()}
                    </g>
                  );
                })}

                {/* Nodes */}
                {GRAPH_NODES.map(node => {
                  const colors = getNodeColor(node.type);
                  const isSelected = selected?.id === node.id;
                  const isConnected = selected && connectedNodeIds.has(node.id) && !isSelected;
                  const dimmed = selected && !isSelected && !isConnected;
                  const searchDim = search && !highlightedIds.has(node.id);

                  return (
                    <g
                      key={node.id}
                      transform={`translate(${node.x}, ${node.y})`}
                      onClick={e => handleNodeClick(node, e)}
                      style={{ cursor: 'pointer' }}
                    >
                      {/* Selection ring */}
                      {isSelected && (
                        <circle r={NODE_RADIUS + 6} fill="none" stroke="#2563A8" strokeWidth={2} strokeDasharray="4 2" opacity={0.7} />
                      )}
                      {/* Node circle */}
                      <circle
                        r={isSelected ? NODE_RADIUS + 2 : NODE_RADIUS}
                        fill={colors.fill}
                        stroke={isSelected ? '#fff' : colors.stroke}
                        strokeWidth={isSelected ? 2 : 1}
                        opacity={dimmed || searchDim ? 0.2 : 1}
                        style={{ transition: 'all 0.2s', filter: isSelected ? 'drop-shadow(0 2px 8px rgba(37,99,168,0.4))' : 'none' }}
                      />
                      {/* Pending indicator */}
                      {node.status === 'Pending' && (
                        <circle r={7} cx={NODE_RADIUS - 4} cy={-(NODE_RADIUS - 4)} fill="#C8A830" stroke="#fff" strokeWidth={1.5} />
                      )}
                      {/* Type label */}
                      <text
                        y={-6}
                        textAnchor="middle"
                        style={{ fontSize: 7, fill: colors.text, fontFamily: 'JetBrains Mono, monospace', fontWeight: 600, letterSpacing: '0.04em', pointerEvents: 'none', opacity: dimmed || searchDim ? 0.3 : 1, transition: 'opacity 0.2s' }}
                      >
                        {node.type.split(' ')[0].substring(0, 8)}
                      </text>
                      {/* Short label below */}
                      <text
                        y={6}
                        textAnchor="middle"
                        style={{ fontSize: 6.5, fill: colors.text, fontFamily: 'Inter, sans-serif', fontWeight: 500, opacity: (dimmed || searchDim) ? 0.3 : 0.9, pointerEvents: 'none', transition: 'opacity 0.2s' }}
                      >
                        {node.label.length > 14 ? node.label.substring(0, 12) + '…' : node.label}
                      </text>
                    </g>
                  );
                })}
              </g>
            </svg>
          </div>

          {/* Legend */}
          <div style={{ borderTop: '1px solid #C5D5E8', padding: '8px 12px', background: '#EFF3F7', flexShrink: 0 }}>
            <div className="flex items-center gap-4 flex-wrap">
              {TYPE_LEGEND.slice(0, 7).map(type => {
                const c = getNodeColor(type);
                return (
                  <div key={type} className="flex items-center gap-1.5">
                    <div style={{ width: 10, height: 10, borderRadius: '50%', background: c.fill, flexShrink: 0 }} />
                    <span style={{ fontSize: 10, color: '#526176', fontFamily: 'JetBrains Mono, monospace' }}>{type}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Inspector panel */}
        <div style={{ width: 280, background: '#F5F7FA', border: '1px solid #C5D5E8', borderRadius: 8, display: 'flex', flexDirection: 'column', overflow: 'hidden', flexShrink: 0 }}>
          <div className="px-4 py-3" style={{ borderBottom: '1px solid #C5D5E8', background: '#EFF3F7', flexShrink: 0 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#526176', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.06em' }}>ENTITY INSPECTOR</div>
          </div>

          <div className="flex-1 overflow-y-auto">
            {!selected ? (
              <div style={{ padding: '40px 20px', textAlign: 'center', color: '#526176', fontSize: 12 }}>
                <div style={{ fontSize: 28, marginBottom: 12, opacity: 0.3 }}>◎</div>
                Click a node to inspect it
              </div>
            ) : (
              <div className="px-4 py-4 space-y-4">
                {/* Header */}
                <div>
                  <div className="flex items-start gap-2">
                    <div
                      className="flex items-center justify-center rounded-full flex-shrink-0 mt-0.5"
                      style={{ width: 32, height: 32, background: getNodeColor(selected.type).fill, color: '#fff', fontSize: 9, fontFamily: 'JetBrains Mono, monospace', fontWeight: 700, textAlign: 'center', lineHeight: 1.2, padding: 4 }}
                    >
                      {selected.type.split(' ').map(w => w[0]).join('')}
                    </div>
                    <div>
                      <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: getNodeColor(selected.type).fill, fontWeight: 600, letterSpacing: '0.06em', marginBottom: 3 }}>
                        {selected.type}
                      </div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: '#17253A', lineHeight: 1.3 }}>{selected.label}</div>
                    </div>
                  </div>
                  <div style={{ marginTop: 8 }}>
                    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, padding: '2px 7px', borderRadius: 3, background: selected.status === 'Validated' ? '#D0EDDB' : '#FBF3D4', color: selected.status === 'Validated' ? '#1E6B45' : '#7A5A0F', fontWeight: 500 }}>
                      {selected.status}
                    </span>
                  </div>
                </div>

                {/* Description */}
                {selected.description && (
                  <div style={{ fontSize: 12, color: '#526176', lineHeight: 1.5, padding: '10px 12px', background: '#EFF3F7', borderRadius: 6, border: '1px solid #C5D5E8' }}>
                    {selected.description}
                  </div>
                )}

                {/* Meta */}
                <div>
                  <div style={{ fontSize: 10, fontWeight: 600, color: '#526176', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.06em', marginBottom: 8 }}>PROPERTIES</div>
                  {[
                    { label: 'Type', value: selected.type },
                    { label: 'Status', value: selected.status },
                    { label: 'Source Document', value: selected.source || '—' },
                  ].map(({ label, value }) => (
                    <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #E7EDF4', fontSize: 12 }}>
                      <span style={{ color: '#526176' }}>{label}</span>
                      <span style={{ color: '#17253A', fontWeight: 500, maxWidth: '55%', textAlign: 'right' }}>{value}</span>
                    </div>
                  ))}
                </div>

                {/* Connected edges */}
                {connectedEdges.length > 0 && (
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 600, color: '#526176', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.06em', marginBottom: 8 }}>
                      RELATIONSHIPS ({connectedEdges.length})
                    </div>
                    <div className="space-y-1.5">
                      {connectedEdges.slice(0, 6).map(edge => {
                        const fromNode = GRAPH_NODES.find(n => n.id === edge.from);
                        const toNode = GRAPH_NODES.find(n => n.id === edge.to);
                        const isOutgoing = edge.from === selected.id;
                        const other = isOutgoing ? toNode : fromNode;
                        return (
                          <div key={edge.id} style={{ padding: '6px 8px', background: '#EFF3F7', borderRadius: 5, border: '1px solid #C5D5E8', fontSize: 11 }}>
                            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#2563A8', fontWeight: 600, marginBottom: 2 }}>
                              {isOutgoing ? '→' : '←'} {edge.label}
                            </div>
                            <div style={{ color: '#17253A', fontWeight: 500 }}>{other?.label}</div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="space-y-1.5 pt-1">
                  {['View Entity', 'View Source Document', 'View All Relationships'].map(label => (
                    <button key={label} style={{ width: '100%', padding: '7px 12px', background: '#EFF3F7', border: '1px solid #C5D5E8', borderRadius: 5, fontSize: 12, color: '#17253A', cursor: 'pointer', textAlign: 'left', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
                      onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = '#D9E7F5')}
                      onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = '#EFF3F7')}>
                      {label}
                      <ExternalLink size={11} style={{ color: '#526176' }} />
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Node count footer */}
          <div style={{ borderTop: '1px solid #C5D5E8', padding: '8px 14px', background: '#EFF3F7', flexShrink: 0 }}>
            <div className="flex justify-between" style={{ fontSize: 11, color: '#526176', fontFamily: 'JetBrains Mono, monospace' }}>
              <span>38,421 entities</span>
              <span>112,804 edges</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
